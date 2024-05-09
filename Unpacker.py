import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.messagebox import showerror, showwarning, showinfo, askyesno
from tkinter.simpledialog import askinteger

import yaml
import json
import os
import shutil
from PIL import Image
import PIL.Image
import threading
import dotenv

import Translations.language as lang_module
import Data.data as concat_data
import Images.image_gen as image_gen

DLCS = {
    "VS": "Vampire Survivors",
    "MS": "Moonspell",
    "FS": "Foscari",
    "EM": "Meeting",
    "OG": "Guns",
}


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

    class CheckBoxes(tk.Toplevel):
        def __init__(self, parent, list_to_boxes):
            super().__init__(parent)
            self.parent = parent
            self.title("Select languages")
            label = ttk.Label(self, text="Select languages to include in split files")
            label.pack()

            self.global_state = tk.BooleanVar()

            cb = ttk.Checkbutton(self, text="Select/Deselect all",
                                 variable=self.global_state,
                                 command=self.set_all)
            cb.pack()

            self.states = []

            for i, val in enumerate(list_to_boxes):
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(self, text=val['Name'], variable=var)
                cb.pack()
                self.states.append(var)

            b_ok = ttk.Button(self, text="Select", command=self.__close)
            b_ok.pack()

        def get_states(self):
            return [v.get() for v in self.states]

        def set_all(self):
            state = self.global_state.get()

            for x in self.states:
                x.set(state)

        def __close(self):
            self.parent.data_from_popup = [v.get() for v in self.states]
            self.destroy()

    def __init__(self, width=700, height=300):
        super().__init__()
        self.width = width
        self.height = height
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.title('Resource unpacker VS')

        b_info = ttk.Button(
            self,
            text="Unpacker help",
            command=self.info
        )
        b_info.grid(row=0, column=1)

        l_info = ttk.Label(self, text="Resource unpacker for ripped assets from Vampire Survivors game.")
        l_info.grid(row=1, column=0)

        b_unpack_by_meta = ttk.Button(
            self,
            text="Select image to unpack",
            command=lambda: self.select_and_unpack(self.assets_dir)
        )
        b_unpack_by_meta.grid(row=2, column=1)

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
            text="Convert language strings to json",
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
            text="Concatenate dlc data\ninto one same files",
            command=self.data_concatenate
        )
        b_data_concat.grid(row=8, column=2)

        b_data_to_image = ttk.Button(
            self,
            text="Get images with\nunified names by data",
            command=self.data_to_image
        )
        b_data_to_image.grid(row=9, column=1)

        self.loaded_meta = {}
        self.data_from_popup = None

        self.outer_progress_bar = None

        self.assets_dir = '/'

        self.set_assets_dir()

    @staticmethod
    def info():
        showinfo("App info",
                 f"To use unpacker you need to rip assets from the game with {"Sprite Export Format"} "
                 f"set as {"Texture"}. (using AssetRipper)\n\n"
                 "In folder ./ExportedProject/Assets/Resources and its subfolders you can select .png file and it will "
                 "unpack selected image."
                 )

    def progress_bar_set(self, index, total):
        self.progress_bar['value'] = index * 100 / total
        self.progress_bar.update()
        self.l_progress_bar_string.set(f"{index} / {total}")
        self.l_progress_bar.update()

    def open_last_loaded(self):
        if self.last_loaded_folder and os.path.exists(self.last_loaded_folder):
            os.startfile(self.last_loaded_folder)

    def select_assets_dir(self):
        full_path = fd.askdirectory(
            title='Select assets directory',
            initialdir=self.assets_dir
        )

        if not full_path:
            return

        self.set_assets_dir(full_path)

    def set_assets_dir(self):
        full_path = os.environ.get("VS_ASSETS")
        if not full_path.endswith("Assets"):
            showwarning("Warning", "Folder must be named 'Assets'")
            return

        self.assets_dir = os.path.normpath(full_path)

        path = self.assets_dir + "/Resources/spritesheets"

        if not os.path.exists(path):
            return

        # self.geometry(f"{self.width + 100}x{self.height}")
        b_assets_folder = ttk.Button(
            self,
            text=".. from spritesheets",
            command=lambda: self.select_and_unpack(path)
        )
        b_assets_folder.grid(row=2, column=2)

    def select_and_unpack(self, start_path):
        def thread_generate_by_meta(p_dir: str, p_file: str, scale: int = 1):
            meta, im = self.get_meta_by_full_path(p_dir, p_file)

            self.outer_progress_bar.close_bar()

            self.generate_by_meta(meta, im, p_file, scale_factor=scale)

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

        if not os.path.exists(full_path + ".meta"):
            showerror("Error", f"{file}.meta is unable to find in this directory.")
            return

        scale_factor = askinteger("Scale", "Type scale multiplier", initialvalue=1)

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {file}.meta")

        t = threading.Thread(target=thread_generate_by_meta, args=[direct, file, scale_factor])
        t.start()

    def get_meta_by_full_path(self, p_dir: str, p_file: str) -> (dict, Image.Image):
        p_file = p_file.replace(".meta", "")
        file = p_file.replace(".png", "").lower()
        full_path = os.path.join(p_dir, p_file)
        if file not in self.loaded_meta:
            print(f"Parsing {p_file}.meta")

            file_path = full_path + ".meta"

            if not os.path.exists(file_path):
                print(f"file {file_path} not exists")
                return None

            with open(file_path) as f:
                sprites = dict(yaml.safe_load(f.read()))["TextureImporter"]["spriteSheet"]["sprites"]

            self.loaded_meta.update({file: {s["name"]: s["rect"] for s in sprites},
                                     file + "Image": Image.open(full_path)})

            print(f"Parse {p_file}.meta ended")
        return self.loaded_meta[file], self.loaded_meta[file + "Image"]

    def generate_by_meta(self, meta: dict, im: Image, file: str, scale_factor: int = 1):
        file = file.replace(".png", "")
        folder_to_save = f"./Images/Generated/By meta/{file}"

        total = len(meta)

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

        for i, (pic_name, rect) in enumerate(meta.items()):
            print(f"\r{i + 1}", end="")
            self.progress_bar_set(i + 1, total)

            sx, sy = im.size

            im_crop = im.crop(
                (rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

            im_crop = im_crop.resize((im_crop.size[0] * scale_factor, im_crop.size[1] * scale_factor),
                                     PIL.Image.NEAREST)
            im_crop.save(f"{folder_to_save}/{pic_name}.png")

        print()
        self.last_loaded_folder = os.path.abspath(folder_to_save)

    def languages_get(self):
        def thread_languages_get(file_path_):
            self.progress_bar_set(0, 1)
            with open(file_path_, 'r', encoding="UTF-8") as f:
                for _ in range(3):
                    f.readline()
                text = f.read()

            folder_to_save = "./Translations"
            if not os.path.exists(folder_to_save):
                os.makedirs(folder_to_save)

            with open(folder_to_save + "/I2Languages.yaml", 'w', encoding="UTF-8") as yml:
                yml.write(text)

            self.outer_progress_bar.close_bar()
            self.progress_bar_set(1, 1)
            self.last_loaded_folder = os.path.abspath(folder_to_save)

        if not self.assets_dir.endswith("Assets"):
            showwarning("Warning", "Assets directory must be selected.")
            return

        file_path = self.assets_dir + "/Resources/I2Languages.asset"
        if not os.path.exists(file_path):
            showwarning("Warning", "Assets directory does not contain language file (I2Languages.asset).")
            return

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

        direct, file = os.path.split(lang_yaml)

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {file}")

        t = threading.Thread(target=thread_languages_get_json)
        t.start()

    def languages_split(self):
        folder_to_save = "./Translations/Generated/Split"

        def thread_languages_split():
            yaml_file = self.get_lang_meta()

            langs_list = yaml_file["MonoBehaviour"]["mSource"]["mLanguages"]

            self.outer_progress_bar.close_bar()
            self.last_loaded_folder = os.path.abspath(folder_to_save)

            self.data_from_popup = None
            cbs = self.CheckBoxes(self, langs_list)
            cbs.wait_window()

            if not self.data_from_popup:
                return

            total_lang_count = len(self.data_from_popup)

            using_list = [(i, x[0]['Name']) for i, x in enumerate(zip(langs_list, self.data_from_popup)) if x[1]]

            if len(using_list) == 0:
                showerror("Error", "No language has been selected.")
                return

            gen = lang_module.split_to_files(yaml_file, using_list, is_gen=True)

            for i, total in gen:
                self.progress_bar_set(i + 1, total)

        lang_yaml = './Translations/I2Languages.yaml'

        if not os.path.exists(lang_yaml):
            showerror("Error", "Language file must be gotten from assets first.")
            return

        direct, file = os.path.split(lang_yaml)

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {file}")

        t = threading.Thread(target=thread_languages_split)
        t.start()

    def get_data(self):
        p_assets = list(filter(lambda x: "ASSETS" in x, os.environ))
        paths = [(f"{os.environ.get(path)}\\TextAsset", DLCS[path.replace("_ASSETS", "")]) for path in p_assets]
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
        gen = concat_data.concatenate(True)

        for i, total in gen:
            self.progress_bar_set(i + 1, total)

    @staticmethod
    def data_selector():
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

    @staticmethod
    def assets_gen(paths: list):
        dirs = paths
        files = []
        while len(dirs) > 0:
            this_dir = dirs.pop(0)
            files.extend(f for f in os.scandir(this_dir) if f.name.endswith(".meta") and not f.is_dir())
            dirs.extend(f for f in os.scandir(this_dir) if f.is_dir())

        return files

    def data_to_image(self):
        def thread_load_data():
            with open(path_data, 'r', encoding="UTF-8") as f:
                data = json.loads(f.read())

            self.outer_progress_bar.change_label(f"Getting language file")
            lang = lang_module.get_lang_file(lang_module.get_lang_path(gen.langFileName))
            if lang:
                lang = lang.get('en')
            else:
                print(f"lang file not found: {gen.langFileName}")

            texture_set = gen.textures_set(data)

            for texture in texture_set:
                if texture is None:
                    continue

                def filt(x):
                    name_low = x.name.lower()
                    texture_low = texture.lower()
                    return name_low.startswith(f"{texture_low}") and name_low.endswith(f"{texture_low}.png.meta")

                meta = list(filter(filt, all_assets))
                print(texture, meta)
                meta = meta[0]
                m_dir, m_file = os.path.split(meta)
                self.outer_progress_bar.change_label(f"Parsing {m_file}")
                self.get_meta_by_full_path(m_dir, m_file)

            total = gen.len_data(data)
            ug = gen.unit_generator(data)

            self.outer_progress_bar.close_bar()

            for i, obj in enumerate(ug):
                self.progress_bar_set(i + 1, total)
                gen.make_image(self.get_meta_by_full_path, obj[0], obj[1], is_with_frame=is_with_frame,
                               scale_factor=scale_factor,
                               lang_file=lang)

            self.last_loaded_folder = os.path.abspath("./Images/Generated")

        if not self.assets_dir.endswith("Assets"):
            showerror("Error", "Assets directory must be selected.")
            return

        paths = [self.assets_dir + "/Resources/spritesheets"]
        for f in filter(lambda x: "VS" not in x and "ASSETS" in x, os.environ):
            p = os.path.join(os.environ.get(f), "Texture2D")
            if os.path.exists(p):
                paths.append(p)

        all_assets = self.assets_gen(paths)

        path_data = self.data_selector()

        if not path_data:
            return

        p_dir, p_file = os.path.split(path_data)

        gen = image_gen.IGFactory.get(p_file)

        if gen is None:
            showerror("Generator error", "Cannot get images from this file.\nGenerator does not exist.")
            return

        scale_factor = askinteger("Input scale", "Input scale factor for images", initialvalue=gen.scaleFactor)
        is_with_frame = askyesno("Frame", "Generate images also with frames?")

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {p_file}")

        t = threading.Thread(target=thread_load_data)
        t.start()


if __name__ == '__main__':
    dotenv.load_dotenv()
    app = Unpacker()
    app.mainloop()
