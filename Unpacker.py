import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.messagebox import showerror, showwarning, showinfo

import yaml
import json
import os
from PIL import Image, ImageFont, ImageDraw
import PIL.Image
import threading


class Unpacker(tk.Tk):
    class ProgressBar(tk.Toplevel):
        def __init__(self, parent, label):
            super().__init__(parent)
            self.title("Parsing")
            self.resizable(False, False)
            self.geometry("300x50")
            self.progressbar = ttk.Progressbar(self, mode="indeterminate", length=200)
            self.progressbar.pack()
            self.progressbar.start(20)
            self.label = ttk.Label(self, text=label)
            self.label.pack()

        def close_bar(self):
            self.progressbar.stop()
            self.destroy()

    def __init__(self, canvas_width, canvas_height):
        super().__init__()
        self.geometry(f"{canvas_width}x{canvas_height}")
        self.resizable(False, False)
        self.title('Resource unpacker VS')

        l_info = tk.Label(self, text="Resource unpacker for ripped assets from Vampire Survivors game.")
        l_info.grid(row=0, column=0)

        b_info = tk.Button(
            self,
            text="Unpacker help",
            command=self.info
        )
        b_info.grid(row=0, column=1)

        b_unpack_by_meta = tk.Button(
            self,
            text="Select image to unpack",
            command=self.select_and_unpack
        )
        b_unpack_by_meta.grid(row=1, column=1)

        self.progress_bar = ttk.Progressbar(
            self,
            orient='horizontal',
            mode='determinate',
            length=280
        )
        self.progress_bar.grid(row=1, column=0)
        self.l_progress_bar_string = tk.StringVar()
        self.l_progress_bar = ttk.Label(self, textvariable=self.l_progress_bar_string)
        self.l_progress_bar.grid(row=2, column=0)

        self.last_loaded_folder = None

        b_last_loaded_folder = tk.Button(
            self,
            text="Open last loaded folder",
            command=self.open_last_loaded
        )
        b_last_loaded_folder.grid(row=2, column=1)

        self.loaded_meta = {}

        self.outer_progress_bar = None

        self.mainloop()

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

    def select_and_unpack(self):
        filetypes = (
            ('Images', '*.png'),
        )

        full_path = fd.askopenfilename(
            title='Open a file',
            initialdir='/',
            filetypes=filetypes
        )

        if not full_path:
            return

        p_dir, p_file = os.path.split(full_path)

        if not os.path.exists(full_path + ".meta"):
            showerror("Error", f"{p_file}.meta is unable to find in this directory.")
            return

        self.outer_progress_bar = self.ProgressBar(self, f"Parsing {p_file}.meta")

        t = threading.Thread(target=self.thread_generate_by_meta, args=[p_dir, p_file])
        t.start()

    def thread_generate_by_meta(self, p_dir: str, p_file: str):
        meta, im = self.get_meta_by_full_path(p_dir, p_file)

        self.outer_progress_bar.close_bar()

        self.generate_by_meta(meta, im, p_file)

    def get_meta_by_full_path(self, p_dir: str, p_file: str) -> (dict, Image.Image):
        file = p_file.replace(".png", "")
        full_path = os.path.join(p_dir, p_file)
        if file not in self.loaded_meta:
            print(f"Parsing {p_file}.meta")

            with open(full_path + ".meta") as f:
                sprites = dict(yaml.safe_load(f.read()))["TextureImporter"]["spriteSheet"]["sprites"]

            self.loaded_meta.update({file: {s["name"]: s["rect"] for s in sprites},
                                     file + "Image": Image.open(full_path)})

            print(f"Parse {p_file}.meta ended")
        return self.loaded_meta[file], self.loaded_meta[file + "Image"]

    def generate_by_meta(self, meta: dict, im: Image, file: str, scale_factor: int = 1):
        file = file.replace(".png", "")
        folder_to_save = f"./Images/Generated/By meta/{file}"

        if not os.path.exists(folder_to_save):
            os.makedirs(folder_to_save)

        total = len(meta)

        if total == 0:
            showwarning("Warning",
                        "Meta file of this picture does not containing needed data.\n"
                        "Some files does not contain it.\n"
                        "But it is also possible that data was ripped with incorrect setting.")
            return

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


if __name__ == '__main__':
    app = Unpacker(500, 100)
