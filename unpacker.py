import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.messagebox import showerror, showwarning, showinfo, askyesno
from tkinter.simpledialog import askinteger
from typing import AnyStr

import yaml
import json
import os
import sys
import shutil
from PIL import Image
import PIL.Image
import threading

import Config.config as config
import Translations.language as lang_module
import Data.data as data_module
import Images.image_gen as image_gen
from Config.config import CfgKey, DLCType
from Images.image_unified_gen import gen_unified_images
from Utility.utility import CheckBoxes, run_multiprocess
from Utility.meta_data import MetaDataHandler


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
                if gen.assets_type in [image_gen.Type.STAGE, image_gen.Type.STAGE_SET]:
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

            if gt.ATTACK_ANIM in gen.available_gen:
                attack_anim_bool = tk.BooleanVar()
                ttk.Checkbutton(self, text="Also generate attack animations", variable=attack_anim_bool).pack()

                self.settings.update({gt.ATTACK_ANIM: attack_anim_bool})

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
        self.width = width
        self.height = height
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
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
            text="Select image to unpack",
            command=lambda: self.select_and_unpack(self.get_assets_dir())
        )
        b_unpack_by_meta.grid(row=2, column=1)

        b_assets_folder = ttk.Button(
            self,
            text=".. from spritesheets",
            command=lambda: self.select_and_unpack(f"{self.get_assets_dir()}/Resources/spritesheets")
        )
        b_assets_folder.grid(row=2, column=2)

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

        self.last_loaded_folder = None

        b_last_loaded_folder = ttk.Button(
            self,
            text="Open last loaded folder",
            command=self.open_last_loaded
        )
        b_last_loaded_folder.grid(row=3, column=1)

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

        b_data_to_image = ttk.Button(
            self,
            text="Get images with\nunified names by data (rewrite)",
            command=self.unified_image_gen_handler
        )
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
        ).grid(row=5, column=0)

        self.loaded_meta = dict()
        self.guid_table = dict()

        MetaDataHandler().load_assets_meta_files()

        self.data_from_popup = None

        self.outer_progress_bar = None

    def load_config(self):
        self.config = config.Config()

    def change_config(self):
        self.config.change_config(self)

    def get_assets_dir(self):
        path = os.path.normpath(self.config[CfgKey.VS])
        if not path.endswith("Assets"):
            path = None
        return path or "/"

    @staticmethod
    def info():
        showinfo("App info",
                 f"To use unpacker you need to rip assets from the game.\n"
                 f"Read README.md for more info."
                 )

    def progress_bar_set(self, current, total):
        self.progress_bar['value'] = current * 100 / total
        self.progress_bar.update()
        self.l_progress_bar_string.set(f"{current} / {total}")
        self.l_progress_bar.update()

    def open_last_loaded(self):
        if self.last_loaded_folder and os.path.exists(self.last_loaded_folder):
            os.startfile(self.last_loaded_folder)

    def select_and_unpack(self, start_path):
        def thread_generate_by_meta(p_dir: str, p_file: str, scale: int = 1):
            meta, im = self.get_meta_by_full_path(p_dir, p_file)

            self.outer_progress_bar.close_bar()

            self.generate_by_meta(meta, im, p_file, scale_factor=scale)

        if not os.path.exists(start_path):
            showwarning("Warning", "Assets directory must be selected.")
            return

        filetypes = [
            ('Images', '*.png')
        ]

        full_path = fd.askopenfilename(
            title='Open a file',
            initialdir=start_path,
            filetypes=filetypes
        )

        if not full_path:
            return

        direct, file = os.path.split(full_path)

        print(f"Unpacking {file}")

        if not os.path.exists(full_path + ".meta"):
            showerror("Error", f"{file}.meta is unable to find in this directory.")
            return

        scale_factor = askinteger("Scale", "Type scale multiplier", initialvalue=1)

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {file}.meta")

        t = threading.Thread(target=thread_generate_by_meta, args=[direct, file, scale_factor])
        t.start()

    def get_meta_by_set_of_paths(self, texture_paths_set: set, is_internal_id: bool = False):
        args = [(*os.path.split(path), is_internal_id) for path in texture_paths_set]
        print(args)
        return run_multiprocess(self.get_meta_by_full_path, args)

    def get_meta_by_full_path(self, p_dir: str, p_file: str, is_internal_id: bool = False) -> (dict, Image.Image):
        p_file = p_file.replace(".meta", "")
        file = p_file.replace(".png", "").lower()
        full_path = os.path.join(p_dir, p_file)
        if file not in self.loaded_meta:
            if not p_dir:
                return None, None

            print(f"Parsing {p_file}.meta")

            file_path = full_path + ".meta"

            if not os.path.exists(file_path):
                print(f"! file {file_path} not exists",
                      file=sys.stderr)
                return None

            with open(file_path) as f:
                spriteSheet = dict(yaml.safe_load(f.read()))["TextureImporter"]["spriteSheet"]
                sprites = spriteSheet["sprites"]

            image = Image.open(full_path)
            if len(sprites) == 0:
                sprites = [{
                    "name": p_file.replace(".png", ""),
                    "internalID": spriteSheet.get("internalID"),
                    "rect": {
                        "x": 0, "y": 0, "width": image.width, "height": image.height
                    },
                    "pivot": {"x": 0.5, "y": 0.5}
                }]
                if not spriteSheet.get("spriteID"):
                    print(
                        f"! Not found sprites and spriteID for {os.path.basename(full_path)}. It could be caused by ripping with wrong sprite setting.",
                        file=sys.stderr)

            self.loaded_meta.update(
                {
                    file: {
                        (s.get("name") if not is_internal_id else s.get("internalID")): {
                            "name": s.get("name"),
                            "internalID": s.get("internalID"),
                            "rect": s.get("rect"),
                            "pivot": s.get("pivot"),
                        } for s in sprites
                    },
                    file + "Image": image
                }
            )

            print(f"Parse {p_file}.meta ended. {len(sprites)=}")
        return self.loaded_meta[file], self.loaded_meta[file + "Image"]

    def generate_by_meta(self, meta: dict, im: Image, file: str, scale_factor: int = 1):
        file = file.replace(".png", "")
        print(f"Generating by meta")

        total = len(meta)
        if total > 1:
            folder_to_save = f"./Images/Generated/_By meta/{file}"
        else:
            folder_to_save = f"./Images/Generated/_By meta/_SingeSprites"

        if total == 0:
            showwarning("Warning",
                        "Meta file of this picture does not containing needed data.\n"
                        "Some files does not contain it.\n"
                        "But it is also possible that data was ripped with incorrect setting.")
            return

        if not os.path.exists(folder_to_save):
            os.makedirs(folder_to_save)

        print(f"Files out of {total}:")

        self.progress_bar_set(0, total)
        for i, (_, meta_data) in enumerate(meta.items()):
            rect = meta_data["rect"]
            print(f"\r{i + 1}", end="")
            self.progress_bar_set(i + 1, total)

            sx, sy = im.size

            im_crop = im.crop(
                (rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

            im_crop = im_crop.resize((im_crop.size[0] * scale_factor, im_crop.size[1] * scale_factor),
                                     PIL.Image.NEAREST)
            im_crop.save(f"{folder_to_save}/{meta_data["name"]}.png")

        print()
        self.last_loaded_folder = os.path.abspath(folder_to_save)

    @staticmethod
    def get_meta_guid(path) -> str | None:
        if not path or not os.path.exists(path):
            return None

        with open(path, 'r', encoding="UTF-8") as f:
            for line in f.readlines()[:10]:
                key, val = line.split(":")

                if key == "guid":
                    return val.strip()

                if not val:
                    return None

    def get_path_by_guid(self, guid: id):
        all_assets = self.get_assets_meta_files()

        if guid not in self.guid_table:
            print("Collecting guids of all spritesheets")
            for path in all_assets:
                asset_guid = self.get_meta_guid(path)
                self.guid_table.update({
                    asset_guid: path
                })
            print("Collected guids of all spritesheets")

        return self.guid_table.get(guid)

    def languages_get(self):
        def thread_languages_get(file_path_):
            self.progress_bar_set(0, 1)
            with open(file_path_, 'r', encoding="UTF-8") as f:
                for _ in range(3):
                    f.readline()
                text = f.read()

            if len(text) < 1000:
                showerror("Error",
                          f"I2Languages does not contain necessary data. (length: {len(text)}) You must manually copy data. (See README.md on how to)")
                self.outer_progress_bar.close_bar()
                return

            folder_to_save = "./Translations"
            if not os.path.exists(folder_to_save):
                os.makedirs(folder_to_save)

            with open(folder_to_save + "/I2Languages.yaml", 'w', encoding="UTF-8") as yml:
                yml.write(text)

            self.outer_progress_bar.close_bar()
            self.progress_bar_set(1, 1)
            self.last_loaded_folder = os.path.abspath(folder_to_save)

        if not self.get_assets_dir().endswith("Assets"):
            showerror("Error", "Assets directory must be selected.")
            return

        file_path = f"{self.get_assets_dir()}/Resources/I2Languages.asset"
        if not os.path.exists(file_path):
            showerror("Error", "Assets directory does not contain language file (I2Languages.asset).")
            return

        print("Copying I2Languages")

        direct, file = os.path.split(file_path)

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {file}.meta")

        t = threading.Thread(target=thread_languages_get, args=[file_path])
        t.start()

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
            if not os.path.exists(folder_to_save):
                os.makedirs(folder_to_save)

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
                self.progress_bar_set(i + 1, total)

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
        if not self.get_assets_dir().endswith("Assets"):
            showwarning("Warning", "Assets directory must be selected.")
            return

        print("Copying data files")

        p_assets = list(filter(lambda x: "ASSETS" in x.value, self.config.data))
        paths = [
            (
                f"{self.config[dlc_id]}\\TextAsset",
                DLCType.get_dlc_name(dlc_id)
            ) for dlc_id in p_assets
        ]
        paths = list(filter(lambda x: x[1], paths))

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
                    self.progress_bar_set(i := i + 1, total)

    def data_concatenate(self):
        add_content_group = askyesno("Add content group",
                                     "Do you want to add 'contentGroup' (DLC) field to objects in merged file"
                                     "if it is not present in original data file?\n"
                                     "Helps to separate image generation by DLC (ex. for characters)\n"
                                     "Default: True")

        print(f"Concatenating data files. {add_content_group=}")
        gen = data_module.concatenate(is_gen=True, add_content_group=add_content_group)

        for i, total in gen:
            self.progress_bar_set(i + 1, total)

    @staticmethod
    def data_selector() -> AnyStr | None:
        path = "./Data"
        if not os.path.exists(path):
            return

        filetypes = [
            ('JSON', '*.json')
        ]

        full_path = fd.askopenfilename(
            title='Open a data file',
            initialdir=path,
            filetypes=filetypes
        )

        if not full_path:
            return None

        return full_path

    def get_assets_meta_files(self):
        paths = [f"{self.get_assets_dir()}/Resources/spritesheets"]
        for f in filter(lambda x: "ASSETS" in x.value, self.config.data):
            p = os.path.join(self.config[f], "Texture2D")
            if os.path.exists(p):
                paths.append(p)

        dirs = list(map(os.path.normpath, paths))
        files = []
        missing_paths = []
        while len(dirs) > 0:
            this_dir = dirs.pop(0)
            if not os.path.exists(this_dir):
                missing_paths.append(this_dir)
                continue

            files.extend(f for f in os.scandir(this_dir) if f.name.endswith(".meta") and not f.is_dir())
            dirs.extend(f for f in os.scandir(this_dir) if f.is_dir())

        if missing_paths:
            print(f"! Missing paths {missing_paths} while trying to access meta files for images.",
                  file=sys.stderr)
            # showerror("Error", f"Missing paths: {missing_paths}")

        return files

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

            texture_set = gen.textures_set(data)
            if generator_settings.get(str(gt.FRAME)):
                texture_set.add("UI")

                if gen.assets_type == image_gen.Type.ARCANA:
                    texture_set.add("items")

            if gen.assets_type == image_gen.Type.CHARACTER:
                weapon_gen = image_gen.IGFactory.get("weapon")
                w_data = data_module.get_data_file(data_module.get_data_path("weaponData_Full.json"))
                add_data.update({
                    "weapon": w_data,
                    "character": data
                })

                if generator_settings.get(str(gt.FRAME)):
                    texture_set.update(weapon_gen.textures_set(w_data))

            for texture in texture_set:
                if texture is None:
                    continue

                def filter_assets(x):
                    name_low = x.name.lower()
                    texture_low = texture.lower()
                    return name_low.startswith(f"{texture_low}") and name_low.endswith(f"{texture_low}.png.meta")

                meta = list(filter(filter_assets, all_assets))
                print(texture, meta)

                if meta:
                    meta = meta[0]
                    m_dir, m_file = os.path.split(meta)
                    self.outer_progress_bar.change_label(f"Parsing {m_file}")
                    self.get_meta_by_full_path(m_dir, m_file)

            total = gen.len_data(data)
            ug = gen.unit_generator(data)

            self.outer_progress_bar.close_bar()

            for i, (k_id, obj) in enumerate(ug):
                self.progress_bar_set(i + 1, total)
                gen.make_image(self.get_meta_by_full_path, k_id, obj,
                               lang_data=(lang or {}).get(k_id),
                               add_data=add_data,
                               **generator_settings)

            self.last_loaded_folder = os.path.abspath("./Images/Generated")

        if not self.get_assets_dir().endswith("Assets"):
            showerror("Error", "Assets directory must be selected.")
            return

        all_assets = self.get_assets_meta_files()

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

        gt = image_gen.GenType

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {p_file}")

        t = threading.Thread(target=thread_load_data)
        t.start()

    def unified_image_gen_handler(self):
        start_path = f".\\Data"
        if not os.path.exists(start_path):
            showerror("Error",
                      "Data folder not exists.")
            return

        filetypes = [
            ('JSON', '*.json')
        ]

        full_path = fd.askopenfilename(
            title='Select data file',
            initialdir=start_path,
            filetypes=filetypes
        )

        if not full_path:
            return

        all_assets = self.get_assets_meta_files()

        gen_unified_images(full_path, all_assets)

    def tilemap_gen_handler(self):
        from Images.tilemap_gen import gen_tilemap
        start_path = f"{self.get_assets_dir()}\\PrefabInstance"
        if not os.path.exists(start_path):
            showwarning("Error",
                        "PrefabInstance folder in assets not exists.")
            start_path = './'

        filetypes = [
            ('Prefab', '*.prefab')
        ]

        full_path = fd.askopenfilename(
            title='Select prefab file',
            initialdir=start_path,
            filetypes=filetypes
        )

        if not full_path:
            return

        print(f"Started generating tilemap {os.path.split(full_path)[-1]}")

        MetaDataHandler().load_guid_paths()

        save_folder = gen_tilemap(full_path)
        self.last_loaded_folder = save_folder

    def audio_gen_handler(self):
        from Utility.req_test import check_pydub
        if not check_pydub():
            print("FFmpeg not found")
            showerror("Error", "FFmpeg not found")
            return

        import Audio.audio_unified_gen as audio_gen

        data_path = self.data_selector()
        if not data_path:
            return

        if "music" not in os.path.basename(data_path).lower():
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

        print(f"Started audio generating {os.path.basename(data_path)}, {save_types_set}")

        self.last_loaded_folder, error = audio_gen.gen_audio(data_path, save_types_set)
        if error:
            showerror("Error", error)

    def data_ripper(self):
        if not self.config[CfgKey.STEAM_VS] or not self.config[CfgKey.RIPPER]:
            showerror("Error", "Not found path to VS steam folder or AssetRipper")
            return

        dlc_types_list = []
        for d in DLCType.get_all():
            if self.config[d.value.config_key]:
                dlc_types_list.append(d)

        cbs = CheckBoxes(dlc_types_list, parent=self, label="Select languages to include in split files",
                         title="Select languages")
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
    app = Unpacker()
    app.mainloop()
