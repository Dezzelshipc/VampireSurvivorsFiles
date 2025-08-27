import itertools
import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog as fd
from tkinter import ttk
from tkinter.messagebox import showerror, showwarning, showinfo, askyesno
from tkinter.simpledialog import askinteger

from PIL.Image import open as image_open

import Source.Data.data as data_module
import Source.Images.image_gen as image_gen
import Source.Images.transparent_save as tr_save
from Source.Images.image_gen_new import ImageGeneratorManager
import Source.Translations.language as lang_module
from Source.Config.config import CfgKey, DLCType, Config
from Source.Data.data import DataHandler
from Source.Translations.language import LangHandler, I2_LANGUAGES, LangType
from Source.Utility.constants import ROOT_FOLDER, IS_DEBUG, DeferConstants, DEFAULT_ANIMATION_FRAME_RATE, IMAGES_FOLDER, \
    GENERATED, TILEMAPS, DATA_FOLDER, TRANSLATIONS_FOLDER, SPLIT, COMPOUND_DATA, COMPOUND_DATA_TYPE, PREFAB_INSTANCE, \
    GAME_OBJECT
from Source.Utility.image_functions import resize_image, get_anim_sprites_ready, apply_tint, resize_list_images
from Source.Utility.logger import Logger
from Source.Utility.meta_data import MetaDataHandler
from Source.Utility.timer import Timeit
from Source.Utility.utility import CheckBoxes, ButtonsBox


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
                if gen.assets_type in [image_gen.OldDataType.STAGE, image_gen.OldDataType.STAGE_SET]:
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

    def __init__(self, width=650, height=370):
        super().__init__()
        self.minsize(width, height)

        self.title('Resource unpacker VS')
        self.iconphoto(False, tk.PhotoImage(file='Source/Images/Show/_Sprite-Atlas Gate.png'))

        ico_image = tk.PhotoImage(file='Source/Images/Show/_Sprite-Garlic.png')
        label_ico = ttk.Label(self, image=ico_image)
        label_ico.image = ico_image
        label_ico.grid(row=0, column=0)

        b_info = ttk.Button(
            self,
            text="Unpacker help",
            command=self.info
        )
        b_info.grid(row=0, column=1)

        b_info = ttk.Button(
            self,
            text="Change config",
            command=lambda: Config.invoke_config_changer(self),
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
            text="Get unified images (old)",
            command=self.data_to_image
        )
        b_data_to_image.grid(row=10, column=1)

        b_data_to_image = ttk.Button(
            self,
            text="Get unified images (new)",
            command=self.unified_image_generator
        )
        b_data_to_image.grid(row=9, column=1)

        ttk.Button(
            self,
            text="Get unified audio",
            command=self.audio_gen_handler
        ).grid(row=9, column=2)

        ttk.Button(
            self,
            text="Magic button to rip data automatically",
            command=self.data_ripper
        ).grid(row=9, column=0)

        # ttk.Label(self, text="").grid(row=10, column=1)

        ttk.Button(
            self,
            text="Get stage tilemap",
            command=self.tilemap_gen_handler
        ).grid(row=11, column=1)

        ttk.Button(
            self,
            text="Create inv tilemap",
            command=self.create_inverse_tilemap
        ).grid(row=11, column=2)

        MetaDataHandler.load()

        self.data_from_popup = None

        self.outer_progress_bar = None

    @staticmethod
    def get_assets_dir(key: DLCType = DLCType.VS) -> Path:
        path = Config.get_assets_dir(key)
        return path.exists() and path or Path()

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
        selected_dlc = self.dlc_selector()
        if not selected_dlc:
            return

        _start_path = self.get_assets_dir(selected_dlc)
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

    def generate_images_by_meta(self, full_path: Path):
        file = full_path.name

        print(f"Generating {file} by meta")

        scale_factor = askinteger("Scale", "Input scale multiplier", initialvalue=1)
        if not scale_factor: return

        full_path_meta = full_path.with_name(file + ".meta")
        if not MetaDataHandler.has_meta_by_path(full_path_meta):
            if not full_path_meta.exists():
                showerror("Error", f"MetaData not found for {file}")
                return
            MetaDataHandler.add_meta_data_by_path(full_path_meta)

        data = MetaDataHandler.get_meta_by_name(file)

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

        frame_rate_initial = DEFAULT_ANIMATION_FRAME_RATE
        frame_rate = askinteger("Frame rate", "Input frame rate (frames per second)", initialvalue=frame_rate_initial)
        if not frame_rate: return
        frame_rate = (frame_rate > 0) and frame_rate or frame_rate_initial

        anim_types = tr_save.ANIM_SAVE_TYPES
        cbs = CheckBoxes(anim_types, parent=self,
                         label="Select animation extension to use.\n(GIF does not support partial transparency)",
                         title="Select anim types")
        cbs.wait_window()
        selected_anim_types = cbs.return_data

        if not selected_anim_types or not any(selected_anim_types):
            print("Not selected any animation extension")
            return

        data = MetaDataHandler.get_meta_by_name(file)

        if not data:
            showerror("Error", f"MetaData not found for {file}")
            return

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

        print(f"Animations out of {total_len}:")
        self.progress_bar_set_percent(0, total_len)

        for i, anim in enumerate(animations):
            sprites_list = get_anim_sprites_ready(anim)
            sprites_list = resize_list_images(sprites_list, scale_factor)

            for ext, folder, func in itertools.compress(tr_save.SAVE_DATA, selected_anim_types):
                path = folder_to_save.joinpath(folder)
                path.mkdir(exist_ok=True)
                func(sprites_list, duration, path.joinpath(str(anim.name)).with_suffix(ext))

            print(f"\r{i + 1}", end="")
            self.progress_bar_set_percent(i + 1, total_len)

        print()
        self.last_loaded_folder = folder_to_save.absolute()

    def languages_get(self):
        timeit = Timeit()
        self.progress_bar_set_percent(0, 1)
        print("Copying I2Languages.assets")

        i2l = LangHandler.get_i2language().raw_text()
        with open((TRANSLATIONS_FOLDER / I2_LANGUAGES).with_suffix(".yaml"), "w", encoding="utf-8") as f:
            f.write(i2l)

        print(f"Copying I2Languages finished {timeit!r}")
        self.progress_bar_set_percent(1, 1)
        self.last_loaded_folder = TRANSLATIONS_FOLDER

    def languages_get_json(self):
        timeit = Timeit()
        self.progress_bar_set_percent(0, 1)
        save_folder = TRANSLATIONS_FOLDER / GENERATED
        print("Converting I2Languages to json")

        i2l = LangHandler.get_i2language().json_text()
        with open((save_folder / I2_LANGUAGES).with_suffix(".json"), "w", encoding="utf-8") as f:
            f.write(i2l)

        print(f"Converting I2Languages finished {timeit!r}")
        self.progress_bar_set_percent(1, 1)
        self.last_loaded_folder = save_folder

    def languages_split(self):
        split_types = ["Split as is", "Change lang list to dict", "Inverse hierarchy so lang is top key"]

        bb = ButtonsBox(split_types, "Select split type", "Select type of splitting langs", self)
        bb.wait_window()

        if bb.return_data is None:
            return

        split_index = bb.return_data
        selected_langs = None

        if split_index == len(split_types) - 1:
            langs_list = LangHandler.get_lang_list()
            cbs = CheckBoxes(LangHandler.get_lang_list(True), parent=self,
                             label="Select languages to include in split files",
                             title="Select languages")
            cbs.wait_window()
            if not cbs.return_data:
                return

            selected_langs = {langs_list[i] for i, tf in enumerate(cbs.return_data) if tf}
            print(f"Selected languages: {selected_langs}")

        split_funcs = [
            lambda l_t: LangHandler.get_lang_file(l_t).json_text(),
            lambda l_t: json.dumps(lang_module.gen_changed_list_to_dict(l_t), ensure_ascii=False, indent=2),
            lambda l_t: json.dumps(
                {lang.value: LangHandler.get_lang_file(l_t).get_lang(lang) for lang in selected_langs},
                ensure_ascii=False, indent=2),
        ]

        _time = Timeit()
        print(f"Splitting I2Languages to separate categories. ({split_types[split_index]})")
        lang_types = LangType.get_all_types()
        i = 0

        for lang_type in lang_types:
            save_path = TRANSLATIONS_FOLDER / GENERATED / SPLIT
            save_path.mkdir(parents=True, exist_ok=True)

            lang_file = split_funcs[split_index](lang_type)
            if lang_file:
                with open((save_path / lang_type.value).with_suffix(".json"), mode="w", encoding="UTF-8") as f:
                    f.write(lang_file)

            self.progress_bar_set_percent(i := i + 1, len(lang_types))

        print(f"Finished splitting I2Languages to separate categories. {_time!r}")

    def get_data(self):
        if not self.get_assets_dir().exists():
            showwarning("Warning", "VS assets folder must be entered.")
            return

        _time = Timeit()
        print("Copying data files.")

        total_amount = DataHandler.get_total_amount()
        i = 0

        dlc_types = DLCType.get_all_types()
        for dlc_type in dlc_types:
            save_path = DATA_FOLDER / dlc_type.value.full_name
            save_path.mkdir(parents=True, exist_ok=True)

            data_files = DataHandler.get_dict_by_dlc_type(dlc_type)
            for data_type, data_file in data_files.items():
                with open((save_path / data_type.value).with_suffix(".json"), mode="w", encoding="UTF-8") as f:
                    f.write(data_file.raw_text())

                self.progress_bar_set_percent(i := i + 1, total_amount)

        print(f"Finished copying data files. {_time!r}")

    def data_concatenate(self):
        _time = Timeit()
        print(f"Concatenating data files.")
        data_types = data_module.DataType.get_all_types()
        i = 0

        for data_type in data_types:
            save_path = DATA_FOLDER / GENERATED
            save_path.mkdir(parents=True, exist_ok=True)

            data_file = DataHandler.get_data(COMPOUND_DATA, data_type)
            with open((save_path / data_type.value).with_suffix(".json"), mode="w", encoding="UTF-8") as f:
                f.write(data_file.raw_text())

            self.progress_bar_set_percent(i := i + 1, len(data_types))

        print(f"Finished concatenating data files. {_time!r}")

    def data_to_image(self):
        def thread_load_data():
            if not path_data or not os.path.exists(path_data):
                return

            with open(path_data, 'r', encoding="UTF-8") as f:
                data = json.loads(f.read())

            self.outer_progress_bar.change_label(f"Getting language file")

            lang = lang_module.LangHandler.get_lang_file(gen.langFileName).get_lang(lang_module.Lang.EN) \
                if gen.langFileName != LangType.NONE else None

            if gen.assets_type == image_gen.OldDataType.CHARACTER:
                w_data = DataHandler.get_data(COMPOUND_DATA, data_module.DataType.WEAPON).data()
                lang_skins = lang_module.LangHandler.get_lang_file(LangType.SKIN).get_lang(lang_module.Lang.EN)
                lang_weapon = lang_module.LangHandler.get_lang_file(LangType.WEAPON).get_lang(lang_module.Lang.EN)
                add_data.update({
                    "weapon": w_data,
                    "character": data,
                    "lang_skins": lang_skins,
                    "lang_weapon": lang_weapon
                })

            total = gen.len_data(data)
            ug = gen.unit_generator(data)

            self.outer_progress_bar.close_bar()

            metas = MetaDataHandler.get_meta_by_name_set(gen.textures_set(data))
            for meta in metas:
                meta.init_sprites()

            for i, (k_id, obj) in enumerate(ug):
                self.progress_bar_set_percent(i + 1, total)
                gen.make_image(k_id, obj, lang_data=(lang or {}).get(k_id), add_data=add_data, **generator_settings)

            self.last_loaded_folder = Path(f"./Images/Generated/{add_data["p_file"]}").absolute()

        if "assets" not in self.get_assets_dir().stem.lower():
            showerror("Error", "Assets directory must be selected.")
            return

        path_data = self.data_selector()

        if not path_data:
            return

        p_file = path_data.stem

        add_data = {
            "p_file": path_data.stem + "_" + path_data.parent.stem,
        }

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

        if gen.is_anim(generator_settings):
            anim_types = tr_save.ANIM_SAVE_TYPES
            cbs = CheckBoxes(anim_types, parent=self,
                             label="Select animation extension to use.\n(GIF does not support partial transparency)",
                             title="Select anim types")
            cbs.wait_window()
            add_data.update({
                "selected_anim_types": cbs.return_data or {}
            })

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {p_file}")

        t = threading.Thread(target=thread_load_data)
        t.start()

    def unified_image_generator(self):
        selected_dlc = self.dlc_selector(allow_compound=True, parent=self)

        if not selected_dlc:
            return

        data_dict = DataHandler.get_dict_by_dlc_type(selected_dlc)
        data_types = list(sorted(ImageGeneratorManager.get_supported_gen_types().intersection(data_dict.keys()),
                                 key=lambda x: x.value))

        show_text = selected_dlc.__repr__() if selected_dlc == COMPOUND_DATA else selected_dlc
        bb = ButtonsBox(map(lambda x: x.value, data_types), "Select data type",
                        ["Select data type which will be used to generate images", f"({show_text})"], self)
        bb.wait_window()

        if bb.return_data is None:
            return

        data_type = data_types[bb.return_data]
        print(f"Started generating images for '{DLCType.string(selected_dlc)}' - '{data_type}'")

        timeit = Timeit()
        self.last_loaded_folder = ImageGeneratorManager.gen_unified_images(selected_dlc, data_type,
                                                                           self.progress_bar_set_percent, parent=self)
        print(f"Finished generating unified images {timeit!r}")

    @staticmethod
    def dlc_selector(allow_compound: bool = False, parent=None) -> DLCType | COMPOUND_DATA_TYPE | None:
        all_dlcs = DLCType.get_all_types()
        compound = COMPOUND_DATA.__repr__()
        if allow_compound:
            all_dlcs.append(compound)

        bb = ButtonsBox(all_dlcs, "Select DLC", "Select DLC from which data file will be selected", parent)
        bb.wait_window()

        if bb.return_data is None:
            return None
        ret = all_dlcs[bb.return_data]

        return COMPOUND_DATA if ret == compound else ret

    @staticmethod
    def data_selector_data(dlc_type: DLCType | COMPOUND_DATA_TYPE,
                           parent=None) -> data_module.DataType | None:
        data_types = list(DataHandler.get_dict_by_dlc_type(dlc_type).keys())

        bb = ButtonsBox(data_types, "Select Data Type", "Select data file", parent)
        bb.wait_window()

        if bb.return_data is None:
            return None

        return data_types[bb.return_data or 0]

    @staticmethod
    def data_selector(add_title="") -> Path | None:
        path = Path("./Data")
        if not path.exists():
            return None

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

    def tilemap_gen_handler(self):
        selected_dlc = self.dlc_selector()
        if not selected_dlc:
            return

        is_found = False
        folders = [GAME_OBJECT, PREFAB_INSTANCE]

        start_path = ROOT_FOLDER
        for folder in folders:
            start_path = self.get_assets_dir(selected_dlc).joinpath(folder)
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

        full_paths_ask = fd.askopenfilenames(
            title='Select prefab files of tilemap',
            initialdir=start_path,
            filetypes=filetypes
        )

        if not full_paths_ask:
            return

        full_paths = list(map(Path, full_paths_ask))

        print(f"Selected for generating tilemap: {full_paths!r}")

        from Source.Images.tilemap_gen import gen_tilemap
        save_folder = None
        for full_path in full_paths:
            save_folder = gen_tilemap(full_path, func_progress_bar_set_percent=self.progress_bar_set_percent)
        print(f"Finished generating all tilemaps: {[fp.name for fp in full_paths]}")
        self.last_loaded_folder = save_folder

    def audio_gen_handler(self):
        if not DeferConstants.is_pydub():
            print("FFmpeg not found")
            showerror("Error", "FFmpeg not found")
            return

        import Source.Audio.audio_unified_gen as audio_gen

        # dlc_type = self.dlc_selector(allow_compound=True, parent=self)
        # if not dlc_type:
        #     return
        dlc_type = COMPOUND_DATA

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

        print(f"Started audio generating {dlc_type!r}, {save_types_set}")

        self.last_loaded_folder, error = audio_gen.gen_music_tracks(dlc_type, save_types_set,
                                                                    self.progress_bar_set_percent)
        if error:
            print(error, file=sys.stderr)
            showerror("Error", error)

    def data_ripper(self):
        if not Config[CfgKey.STEAM_VS] or not Config[CfgKey.RIPPER]:
            showerror("Error", "Not found path to VS steam folder or AssetRipper")
            return

        dlc_types_list = []
        for d in DLCType.get_all_types():
            if Config[d.value.config_key]:
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
        from Source.Ripper.ripper import rip_files
        rip_files(dlc_types_set)

        print("Finished ripping files")

        MetaDataHandler.unload()
        MetaDataHandler.load()

    def create_inverse_tilemap(self):
        selecting_path = IMAGES_FOLDER / GENERATED / TILEMAPS
        while not selecting_path.exists():
            selecting_path = selecting_path.parent

        filetypes = [
            ('Images', '*.png')
        ]

        full_path = fd.askopenfilename(
            title='Open an image file of tilemap',
            initialdir=selecting_path,
            filetypes=filetypes
        )

        if not full_path:
            return

        tint_dec_int = askinteger("Enter tint", "Enter tint in form of integer base 10")
        tint = (
            (tint_dec_int >> 16) & 0xff,
            (tint_dec_int >> 8) & 0xff,
            tint_dec_int & 0xff
        )

        is_create = askyesno("Create inverse?",
                             f"Create inverse with {tint=} [ {tint_dec_int} / {hex(tint_dec_int).upper()[2:]} ]")
        if not is_create:
            return

        full_path = Path(full_path)
        save_path = full_path.parent / "Inverse"

        image = image_open(full_path)

        save_path.mkdir(exist_ok=True, parents=True)
        img = apply_tint(image, tint)
        img.save(save_path / full_path.name)
        img.rotate(180).save(save_path / full_path.with_stem(full_path.stem + "_inv").name)

        self.last_loaded_folder = save_path


if __name__ == '__main__':
    sys.stdout = Logger(sys.stdout)
    sys.stderr = Logger(sys.stderr)
    IS_DEBUG and print(f"{IS_DEBUG = }\n")

    app = Unpacker()
    app.mainloop()
    DeferConstants.is_pydub()
