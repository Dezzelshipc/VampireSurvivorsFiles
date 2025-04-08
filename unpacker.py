import itertools
import json
import os
import shutil
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog as fd
from tkinter import ttk
from tkinter.messagebox import showerror, showwarning, showinfo, askyesno
from tkinter.simpledialog import askinteger

import yaml

import Config.config as config
import Data.data as data_module
import Images.image_gen as image_gen
import Images.transparent_save as tr_save
import Translations.language as lang_module
from Config.config import CfgKey, DLCType
from Utility.logger import Logger
from Utility.constants import ROOT_FOLDER
from Utility.image_functions import resize_image, crop_image_rect_left_top
from Utility.meta_data import MetaDataHandler, get_meta_by_name
from Utility.utility import CheckBoxes, ButtonsBox


class Unpacker(tk.Tk):
    class ProgressBar(tk.Toplevel):
        def __init__(self, parent, label):
            super().__init__(parent)
            self.title("Parsing")
            self.resizable(False, False)
            self.geometry("200x50")
            self.progressbar = ttk.Progressbar(self, mode="indeterminate", length=150)
            self.progressbar.pack()
            self.progressbar.start(20)
            self.label = ttk.Label(self, text=label)
            self.label.pack()

        def change_label(self, label):
            self.label["text"] = label
            self.label.update()

        def close_bar(self):
            self.progressbar.stop()
            self.destroy()

    class GeneratorDialog(tk.Toplevel):
        def __init__(self, parent, gen: image_gen.ImageGenerator):
            super().__init__(parent)
            self.parent = parent
            self.title("Select settings")
            ttk.Label(self, text="Select settings for exporting files").pack()

            self.settings = dict()
            gt = image_gen.GenType

            ttk.Label(self, text="Scale factor").pack()
            scale_input = ttk.Entry(self)
            scale_input.insert(0, gen.scaleFactor)
            scale_input.pack(pady=[0, 5])
            self.settings.update({gt.SCALE: scale_input})

            ttk.Label(self, text="Add postfix to all images").pack()
            postfix_input = ttk.Entry(self)
            postfix_input.insert(0, "")
            postfix_input.pack(pady=[0, 5])
            self.settings.update({"add_postfix": postfix_input})

            if gt.FRAME in gen.available_gen:
                text = "Also generate with frame variants"
                if gen.assets_type in [image_gen.DataType.STAGE, image_gen.DataType.STAGE_SET]:
                    text = "Also generate with name of stage"

                frame_bool = tk.BooleanVar()
                ttk.Checkbutton(self, text=text, variable=frame_bool).pack()

                self.settings.update({gt.FRAME: frame_bool})

            if gt.ANIM in gen.available_gen:
                anim_bool = tk.BooleanVar()
                ttk.Checkbutton(self, text="Also generate animations", variable=anim_bool).pack()

                self.settings.update({gt.ANIM: anim_bool})

            if gt.DEATH_ANIM in gen.available_gen:
                death_anim_bool = tk.BooleanVar()
                ttk.Checkbutton(self, text="Also generate death animations (slow)", variable=death_anim_bool).pack()

                self.settings.update({gt.DEATH_ANIM: death_anim_bool})

            if gt.SPECIAL_ANIM in gen.available_gen:
                attack_anim_bool = tk.BooleanVar()
                ttk.Checkbutton(self, text="Also generate attack animations", variable=attack_anim_bool).pack()

                self.settings.update({gt.SPECIAL_ANIM: attack_anim_bool})

            b_ok = ttk.Button(self, text="Start", command=self.__close)
            b_ok.pack()

            self.protocol("WM_DELETE_WINDOW", self.__close_exit)
            self.exit = False

        def __close_exit(self):
            self.exit = True
            self.__close()

        def __close(self):
            def get(k, v):
                return int(v.get()) if k == image_gen.GenType.SCALE else v.get()

            self.parent.data_from_popup = {str(k): get(k, v) for k, v in self.settings.items()}
            self.parent.data_from_popup.update({"exit": self.exit})
            self.destroy()

    def __init__(self, width=650, height=350):
        super().__init__()
        self.minsize(width, height)

        self.title('Resource unpacker VS')

        self.load_config()

        b_info = ttk.Button(
            self,
            text="Unpacker help",
            command=self.info
        )
        b_info.grid(row=0, column=1)

        b_info = ttk.Button(
            self,
            text="Change config",
            command=self.change_config
        )
        b_info.grid(row=0, column=2)

        l_info = ttk.Label(self, text="Resource unpacker for ripped assets from Vampire Survivors game.")
        l_info.grid(row=1, column=0)

        b_unpack_by_meta = ttk.Button(
            self,
            text="Select image to unpack images",
            command=lambda: self.unpack_by_meta(self.generate_images_by_meta)
        )
        b_unpack_by_meta.grid(row=2, column=1)

        b_unpack_img_spritesheets = ttk.Button(
            self,
            text=".. from spritesheets",
            command=lambda: self.unpack_by_meta_from_spritesheets(self.generate_images_by_meta)
        )
        b_unpack_img_spritesheets.grid(row=2, column=2)

        b_unpack_anim_by_meta = ttk.Button(
            self,
            text="Select image to\nunpack animations",
            command=lambda: self.unpack_by_meta(self.generate_animation_by_meta)
        )
        b_unpack_anim_by_meta.grid(row=3, column=1)

        b_unpack_anim_spritesheets = ttk.Button(
            self,
            text=".. from spritesheets",
            command=lambda: self.unpack_by_meta_from_spritesheets(self.generate_animation_by_meta)
        )
        b_unpack_anim_spritesheets.grid(row=3, column=2)

        self.progress_bar = ttk.Progressbar(
            self,
            orient='horizontal',
            mode='determinate',
            length=280
        )
        self.progress_bar.grid(row=3, column=0)
        self.l_progress_bar_string = tk.StringVar()
        self.l_progress_bar = ttk.Label(self, textvariable=self.l_progress_bar_string)
        self.l_progress_bar.grid(row=2, column=0)

        self.last_loaded_folder: Path | None = None

        b_last_loaded_folder = ttk.Button(
            self,
            text="Open last loaded folder",
            command=self.open_last_loaded
        )
        b_last_loaded_folder.grid(row=5, column=0)

        self.rowconfigure(4, minsize=30)

        b_language_file = ttk.Button(
            self,
            text="Get language strings file",
            command=self.languages_get
        )
        b_language_file.grid(row=5, column=1)

        b_language_to_json = ttk.Button(
            self,
            text="Convert language\nstrings to json",
            command=self.languages_get_json
        )
        b_language_to_json.grid(row=5, column=2)

        b_language_split = ttk.Button(
            self,
            text="Split language strings",
            command=self.languages_split
        )
        b_language_split.grid(row=6, column=1)

        self.rowconfigure(7, minsize=30)

        b_data_get = ttk.Button(
            self,
            text="Get data from assets",
            command=self.get_data
        )
        b_data_get.grid(row=8, column=1)

        b_data_concat = ttk.Button(
            self,
            text="Merge dlc data\ninto same files",
            command=self.data_concatenate
        )
        b_data_concat.grid(row=8, column=2)

        b_data_to_image = ttk.Button(
            self,
            text="Get images with\nunified names by data",
            command=self.data_to_image
        )
        b_data_to_image.grid(row=9, column=1)

        # b_data_to_image = ttk.Button(
        #     self,
        #     text="Get images with\nunified names by data (rewrite)",
        #     command=self.unified_image_gen_handler
        # )
        # b_data_to_image.grid(row=10, column=1)

        ttk.Button(
            self,
            text="Get stage tilemap",
            command=self.tilemap_gen_handler
        ).grid(row=9, column=2)

        ttk.Button(
            self,
            text="Get unified audio",
            command=self.audio_gen_handler
        ).grid(row=10, column=2)

        ttk.Button(
            self,
            text="Magic button to\nrip data automatically",
            command=self.data_ripper
        ).grid(row=9, column=0)

        self.loaded_meta = dict()

        MetaDataHandler()

        self.data_from_popup = None

        self.outer_progress_bar = None

    def load_config(self):
        self.config = config.Config()

    def change_config(self):
        self.config.change_config(self)

    def get_assets_dir(self, key: CfgKey = CfgKey.VS) -> Path:
        path = self.config[key]
        if not "assets" in path.stem.lower():
            path = None
        return path or Path("./")

    @staticmethod
    def info():
        showinfo("App info",
                 f"To use unpacker you need to rip assets from the game.\n"
                 f"Read README.md for more info."
                 )

    def progress_bar_set_percent(self, current, total):
        self.progress_bar['value'] = current * 100 / total if total else 100
        self.progress_bar.update()
        self.l_progress_bar_string.set(f"{current} / {total}")
        self.l_progress_bar.update()

    def progress_bar_set_sec(self, seconds: float):
        self.progress_bar['value'] = (seconds * 10) % 100
        self.progress_bar.update()
        self.l_progress_bar_string.set(f"{seconds:.2f}")
        self.l_progress_bar.update()

    def open_last_loaded(self):
        if self.last_loaded_folder and self.last_loaded_folder.exists():
            os.startfile(self.last_loaded_folder)

    def unpack_by_meta_from_spritesheets(self, generate_function):
        folder = self.get_assets_dir().joinpath("Resources", "spritesheets")

        if not folder.exists():
            showwarning("Warning", "Spritesheets folder does not found.")
            return

        self.generate_by_meta_selector(folder, generate_function)

    def unpack_by_meta(self, generate_function):
        selected_dlc = self.select_dlc()
        if not selected_dlc:
            return
        selected_dlc = selected_dlc.value

        _start_path = self.get_assets_dir(selected_dlc.config_key)
        start_paths = [_start_path.joinpath("Texture2D"), _start_path]

        while (start_path := start_paths.pop(0)) and not start_path.exists():
            pass

        if not start_paths:
            showwarning("Warning", "Assets folder not found.")
            return

        self.generate_by_meta_selector(start_path, generate_function)

    @staticmethod
    def generate_by_meta_selector(selecting_path: Path, generate_function):
        filetypes = [
            ('Images', '*.png')
        ]

        full_path = fd.askopenfilename(
            title='Open a file',
            initialdir=selecting_path,
            filetypes=filetypes
        )

        if not full_path:
            return

        full_path = Path(full_path)

        generate_function(full_path)

    def generate_images_by_meta(self, full_path):
        file = full_path.name

        print(f"Generating {file} by meta")

        scale_factor = askinteger("Scale", "Input scale multiplier", initialvalue=1)
        if not scale_factor: return

        data = get_meta_by_name(file)

        if not data:
            showerror("Error", f"MetaData not found for {file}")
            return

        data.init_sprites()

        total_len = len(data.data_name)

        folder_to_save = ROOT_FOLDER.joinpath("Images", "Generated", "_By meta Image")
        if total_len > 1:
            folder_to_save = folder_to_save.joinpath(full_path.stem)
        else:
            folder_to_save = folder_to_save.joinpath("_SingeSprites")

        folder_to_save.mkdir(parents=True, exist_ok=True)

        print(f"Files out of {total_len}:")
        self.progress_bar_set_percent(0, total_len)

        for i, (_, sprite_data) in enumerate(data.data_name.items()):
            sprite = resize_image(sprite_data.sprite, scale_factor)
            sprite.save(folder_to_save.joinpath(str(sprite_data.real_name)).with_suffix(".png"))

            print(f"\r{i + 1}", end="")
            self.progress_bar_set_percent(i + 1, total_len)

        print()
        self.last_loaded_folder = folder_to_save.absolute()

    def generate_animation_by_meta(self, full_path):
        file = full_path.name

        print(f"Generating {file} by meta")

        scale_factor_initial = 1
        scale_factor = askinteger("Scale", "Input scale multiplier", initialvalue=scale_factor_initial)
        if not scale_factor: return
        scale_factor = (scale_factor > 0) and scale_factor or scale_factor_initial

        frame_rate_initial = 6
        frame_rate = askinteger("Frame rate", "Input frame rate (frames per second)", initialvalue=frame_rate_initial)
        if not frame_rate: return
        frame_rate = (frame_rate > 0) and frame_rate or frame_rate_initial

        anim_types = ["gif", "gif|alpha>=50", "webp", "apng"]
        cbs = CheckBoxes(anim_types, parent=self,
                         label="Select animation extension to use.\n(GIF does not support partial transparency)",
                         title="Select anim types")
        cbs.wait_window()
        selected_anim_types = cbs.return_data

        if not selected_anim_types or not any(selected_anim_types):
            print("Not selected any animation extension")
            return

        data = get_meta_by_name(file)

        if not data:
            showerror("Error", f"MetaData not found for {file}")
            return

        data.init_animations()

        animations = data.get_animations()

        total_len = len(animations)

        if not total_len:
            print(f"Not found animations for {file}")
            return

        selected_types = list(itertools.compress(anim_types, selected_anim_types))
        print(f"Selected {scale_factor=}, {frame_rate=}, selected extensions={selected_types}")

        folder_to_save = ROOT_FOLDER.joinpath("Images", "Generated", "_By meta Anim")
        if total_len > 1:
            folder_to_save = folder_to_save.joinpath(full_path.stem)
        else:
            folder_to_save = folder_to_save.joinpath("_SingeAnimations")

        folder_to_save.mkdir(parents=True, exist_ok=True)

        duration = 1000 // frame_rate

        relative_data = [
            (".gif", "gif", tr_save.save_transparent_gif2),
            (".gif", "gif_a50", lambda *x: tr_save.save_transparent_gif2(*x, alpha_threshold=50)),
            (".webp", "webp", tr_save.save_transparent_webp),
            (".png", "apng", tr_save.save_transparent_apng),
        ]

        print(f"Animations out of {total_len}:")
        self.progress_bar_set_percent(0, total_len)

        for i, anim in enumerate(animations):
            sprites_list = []
            for img, rect, sprite_name in anim.get_sprites_iter():
                sprite = crop_image_rect_left_top(img, rect)
                sprite = resize_image(sprite, scale_factor)
                sprites_list.append(sprite)

            for ext, folder, func in itertools.compress(relative_data, selected_anim_types):
                path = folder_to_save.joinpath(folder)
                path.mkdir(exist_ok=True)
                func(sprites_list, duration, path.joinpath(str(anim.name)).with_suffix(ext))

            print(f"\r{i + 1}", end="")
            self.progress_bar_set_percent(i + 1, total_len)

        print()
        self.last_loaded_folder = folder_to_save.absolute()

    def languages_get(self):
        print("Copying I2Languages.assets")
        self.progress_bar_set_percent(0, 1)
        folder_to_save, error = lang_module.copy_lang_file()
        if error:
            showerror("Error", error)
            print(error, file=sys.stderr)
        else:
            self.last_loaded_folder = folder_to_save
        self.progress_bar_set_percent(1, 1)
        print("Copying finished")

    ##
    def get_lang_meta(self) -> dict | None:
        lang_path = './Translations/I2Languages.yaml'

        if "I2Languages" not in self.loaded_meta:
            with open(lang_path, 'r', encoding="UTF-8") as f:
                self.loaded_meta.update({"I2Languages": yaml.safe_load(f.read())})

        return self.loaded_meta["I2Languages"]

    def languages_get_json(self):
        def thread_languages_get_json():
            yaml_file = self.get_lang_meta()

            folder_to_save = "./Translations/Generated"

            os.makedirs(folder_to_save, exist_ok=True)

            with open(folder_to_save + "/I2Languages.json", 'w', encoding="UTF-8") as json_file:
                json_file.write(json.dumps(yaml_file, ensure_ascii=False, indent=None))

            self.outer_progress_bar.close_bar()
            self.last_loaded_folder = os.path.abspath(folder_to_save)

        lang_yaml = './Translations/I2Languages.yaml'

        if not os.path.exists(lang_yaml):
            showerror("Error", "Language file must be gotten from assets first.")
            return

        print("Converting I2Languages to json")

        direct, file = os.path.split(lang_yaml)

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {file}")

        t = threading.Thread(target=thread_languages_get_json)
        t.start()

    def languages_split(self):
        folder_to_save = "./Translations/Generated/Split"

        def thread_languages_split():
            yaml_file = self.get_lang_meta()

            langs_list = yaml_file["MonoBehaviour"]["mSource"]["mLanguages"]
            langs_list = [lang['Name'] for lang in langs_list]
            self.outer_progress_bar.close_bar()
            self.last_loaded_folder = os.path.abspath(folder_to_save)

            cbs = CheckBoxes(langs_list, parent=self, label="Select languages to include in split files",
                             title="Select languages")
            cbs.wait_window()
            data_from_popup = cbs.return_data

            if not data_from_popup:
                return

            using_list = [(i, x[0]) for i, x in enumerate(zip(langs_list, data_from_popup)) if x[1]]

            if not using_list:
                showerror("Error", "No language has been selected.")
                return

            gen = lang_module.split_to_files(yaml_file, using_list, is_gen=True)

            for i, total in gen:
                self.progress_bar_set_percent(i + 1, total)

        lang_yaml = './Translations/I2Languages.yaml'

        if not os.path.exists(lang_yaml):
            showerror("Error", "Language file must be copied from assets first.")
            return

        print("Splitting I2Languages to separate categories")

        direct, file = os.path.split(lang_yaml)

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {file}")

        t = threading.Thread(target=thread_languages_split)
        t.start()

    def get_data(self):
        if not self.get_assets_dir().exists():
            showwarning("Warning", "VS assets folder must be entered.")
            return

        print("Copying data files")

        paths = [
            (
                self.config[dlc_type.value.config_key].joinpath("TextAsset"),
                dlc_type.value.full_name
            ) for dlc_type in DLCType.get_all_types()
        ]

        total = 0
        i = 0
        for path, dlc in paths:
            data_path = f"./Data/{dlc}"
            if os.path.exists(path):
                entries = list(filter(lambda x: not x.name.endswith(".meta"), os.scandir(path)))
                total += len(entries)
                if os.path.exists(data_path):
                    shutil.rmtree(data_path)
                os.mkdir(data_path)

                for entry in entries:
                    shutil.copy2(entry, data_path)
                    self.progress_bar_set_percent(i := i + 1, total)

    def data_concatenate(self):
        add_content_group = askyesno("Add content group",
                                     "Do you want to add 'contentGroup' (DLC) field to objects in merged file"
                                     "if it is not present in original data file?\n"
                                     "Helps to separate image generation by DLC (ex. for characters)\n"
                                     "Default: True")

        print(f"Concatenating data files. {add_content_group=}")
        gen = data_module.concatenate(is_gen=True, add_content_group=add_content_group)

        for i, total in gen:
            self.progress_bar_set_percent(i + 1, total)

    @staticmethod
    def data_selector(add_title="") -> Path | None:
        path = Path("./Data")
        if not path.exists():
            return

        filetypes = [
            ('JSON', '*.json')
        ]

        full_path = fd.askopenfilename(
            title=f'Open a data file{add_title}',
            initialdir=path,
            filetypes=filetypes
        )

        if not full_path:
            return None

        return Path(full_path)

    def data_to_image(self):
        def thread_load_data():

            data = data_module.get_data_file(path_data)
            add_data = {}

            self.outer_progress_bar.change_label(f"Getting language file")
            lang = lang_module.get_lang_file(lang_module.get_lang_path(gen.langFileName))
            if lang and lang.get('en'):
                lang = lang.get('en')
            else:
                lang = None
                print(f"! Not found english for lang file: {gen.langFileName}",
                      file=sys.stderr)

            if gen.assets_type == image_gen.DataType.CHARACTER:
                w_data = data_module.get_data_file(data_module.get_data_path("weaponData_Full.json"))
                add_data.update({
                    "weapon": w_data,
                    "character": data
                })

            total = gen.len_data(data)
            ug = gen.unit_generator(data)

            self.outer_progress_bar.close_bar()

            def meta_func(path, name):
                d = get_meta_by_name(name)
                if d:
                    return d.data_name, d.image
                else:
                    return (None,) * 2

            for i, (k_id, obj) in enumerate(ug):
                self.progress_bar_set_percent(i + 1, total)
                gen.make_image(meta_func,
                               k_id, obj,
                               lang_data=(lang or {}).get(k_id),
                               add_data=add_data,
                               **generator_settings)

            self.last_loaded_folder = Path("./Images/Generated").absolute()

        if "assets" not in self.get_assets_dir().stem.lower():
            showerror("Error", "Assets directory must be selected.")
            return

        path_data = self.data_selector()

        if not path_data:
            return

        p_dir, p_file = os.path.split(path_data)

        gen = image_gen.IGFactory.get(p_file)

        if gen is None:
            showerror("Generator error", "Cannot get images from this file.\nGenerator does not exist.")
            return

        dial = self.GeneratorDialog(self, gen)
        dial.wait_window()
        if self.data_from_popup["exit"]:
            return

        print(f"Started generating images for {gen.assets_type} ({os.path.basename(path_data)})")

        generator_settings = self.data_from_popup

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {p_file}")

        t = threading.Thread(target=thread_load_data)
        t.start()

    def select_dlc(self) -> DLCType | None:
        all_dlcs = config.DLCType.get_all_types()
        bb = ButtonsBox(all_dlcs, "Select DLC", "Select DLC to open respective folder", self)
        bb.wait_window()

        if bb.return_data is None:
            return None

        return all_dlcs[bb.return_data or 0]

    def tilemap_gen_handler(self):
        selected_dlc = self.select_dlc()
        if not selected_dlc:
            return
        selected_dlc = selected_dlc.value

        is_found = False
        folders = ["GameObject", "PrefabInstance"]

        start_path = ROOT_FOLDER
        for folder in folders:
            start_path = self.get_assets_dir(selected_dlc.config_key).joinpath(folder)
            if start_path.exists():
                is_found = True
                break

        if not is_found:
            showwarning("Error",
                        "Prefab folder not found.")
            start_path = ROOT_FOLDER

        filetypes = [
            ('Prefab', '*.prefab')
        ]

        full_path = fd.askopenfilename(
            title='Select prefab file of tilemap',
            initialdir=start_path,
            filetypes=filetypes
        )

        if not full_path:
            return

        full_path = Path(full_path)

        print(f"Selected for generating tilemap: {full_path!r}")

        from Images.tilemap_gen import gen_tilemap
        save_folder = gen_tilemap(full_path)
        self.last_loaded_folder = save_folder

    def audio_gen_handler(self):
        from Utility.req_test import check_pydub
        if not check_pydub():
            print("FFmpeg not found")
            showerror("Error", "FFmpeg not found")
            return

        import Audio.audio_unified_gen as audio_gen

        data_path = self.data_selector(": any music.json")
        if not data_path:
            return

        if "music" not in data_path.stem.lower():
            showerror("Error", "'Music' data file must be selected.")
            return

        save_types_list = audio_gen.AudioSaveType.get()

        cbs = CheckBoxes(save_types_list, parent=self, label="Select languages to include in split files",
                         title="Select languages")
        cbs.wait_window()
        data_from_popup = cbs.return_data

        if not data_from_popup:
            return

        save_types_set = {t for i, t in enumerate(save_types_list) if data_from_popup[i]}

        if not save_types_set:
            return

        print(f"Started audio generating {data_path!r}, {save_types_set}")

        self.last_loaded_folder, error = audio_gen.gen_music_tracks(data_path, save_types_set,
                                                                    self.progress_bar_set_percent)
        if error:
            showerror("Error", error)

    def data_ripper(self):
        if not self.config[CfgKey.STEAM_VS] or not self.config[CfgKey.RIPPER]:
            showerror("Error", "Not found path to VS steam folder or AssetRipper")
            return

        dlc_types_list = []
        for d in DLCType.get_all_types():
            if self.config[d.value.config_key]:
                dlc_types_list.append(d)

        cbs = CheckBoxes(dlc_types_list, parent=self, label="Select DLCs to rip",
                         title="Select DLCs")
        cbs.wait_window()
        data_from_popup = cbs.return_data

        if not data_from_popup:
            return

        dlc_types_set = {t for i, t in enumerate(dlc_types_list) if data_from_popup[i]}

        if not dlc_types_set:
            return

        print(f"Started ripping files: {dlc_types_set}")
        from Ripper.ripper import rip_files
        rip_files(dlc_types_set)

        print("Finished ripping files")


if __name__ == '__main__':
    sys.stdout = Logger(sys.stdout)
    sys.stderr = Logger(sys.stderr)
    app = Unpacker()
    app.mainloop()
