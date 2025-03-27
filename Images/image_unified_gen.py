import tkinter as tk
from tkinter import ttk
import re

from enum import Enum
from tkinter.messagebox import showerror

from PIL import Image
from PIL.Image import Resampling

from Utility.singleton import Singleton
from Utility.utility import run_multiprocess
from Data.data import get_data_file
from Utility.meta_data import get_meta_by_name_set, MetaData, get_meta_dict_by_name_set
from Utility.image_functions import crop_image_rect_left_bot, resize_image

class UnifiedImageHandler(metaclass=Singleton):
    def __init__(self):
        self.textures = dict()



def gen_unified_images(path: str, assets_paths: list):
    # raise NotImplementedError("Rewrite is in progress.")
    handler = UnifiedImageHandler()

    data = get_data_file(path)
    gen = get_generator(path)

    if not gen:
        showerror("Error",
                  "Generator for data file not found.")
        return

    dialog = GeneratorDialog(gen)
    dialog.wait_window()
    req_gens = dialog.return_data

    gen.load_data(data, req_gens)

    texture_set = gen.get_textures_set()

    handler.textures = get_meta_dict_by_name_set(texture_set)

    if GenType.IMAGE in req_gens:
        run_multiprocess(gen.gen_image, gen.entries)

    pass


class GenType(Enum):
    IMAGE = 0
    IMAGE_FRAME = 1

    ANIM = 10
    DEATH_ANIM = 11
    ATTACK_ANIM = 12

    @classmethod
    def get_order(cls):
        return [*cls]


class SimpleGenerator:
    def __init__(self):
        # Generic
        self.lang_file_name = ""

        # Entry keys
        self.key_main_texture_name = ""
        self.key_sprite_name = ""
        self.key_frame_name = ""

        # Default
        self.default_scale_factor = 1
        self.default_frame_name = None

        # Data
        self.entries = None
        self.requested_gen_types = None

    def load_data(self, data: dict, requested_gen_types: list[GenType]) -> None:
        self.entries = [
            self.get_unit(key_id, entry) for key_id, entry in data.items()
        ]
        self.requested_gen_types = requested_gen_types

    @staticmethod
    def get_available_gens() -> list[GenType]:
        return [GenType.IMAGE]

    @staticmethod
    def get_gens_tips() -> dict[GenType: str]:
        return {
            GenType.IMAGE: "Scale factor",
            GenType.IMAGE_FRAME: "Generate frame variants",
            GenType.ANIM: "Generate animations",
            GenType.DEATH_ANIM: "Generate death animations",
            GenType.ATTACK_ANIM: "Generate attack animations",
        }

    @staticmethod
    def get_save_name(name) -> str:
        return re.sub(r'[<>:/|\\?*]', '', name.strip())

    @staticmethod
    def get_unit(key_id: str, entry: dict) -> dict:
        entry.update({
            "key_id": key_id
        })
        return entry

    def get_frame_name(self, entry: dict):
        return entry.get(self.key_frame_name, self.default_frame_name).replace(".png", "")

    def get_textures_set(self) -> set:
        textures_set = {entry.get(self.key_main_texture_name) for entry in self.entries}

        if GenType.IMAGE_FRAME in self.requested_gen_types:
            textures_set.add("UI")

        return textures_set

    def gen_image(self, entry):
        handler = UnifiedImageHandler()
        pass

    def gen_image_with_frame(self, entry):
        pass

    def gen_anim(self, entry):
        pass

    def gen_anim_death(self, entry):
        pass

    def gen_attack_anim(self, entry):
        pass


class ItemGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        # Generic
        self.lang_file_name = "itemLang"

        # Entry keys
        self.key_main_texture_name = "texture"
        self.key_sprite_name = "frameName"
        self.key_frame_name = "collection"

        # Default
        self.default_scale_factor = 4
        self.default_frame_name = None


    def load_data(self, data: dict, requested_gen_types: list[GenType]):
        super().load_data(data, requested_gen_types)


    @staticmethod
    def get_available_gens() -> list[GenType]:
        gens_list = SimpleGenerator.get_available_gens()
        gens_list.extend([GenType.IMAGE_FRAME])
        return gens_list

    def get_frame_name(self, entry: dict):
        frames_dict = {
            "BaseGame": "frameF",
            "Extra": "frameB_bold",
            "Moonspell": "frameB_blue",
            "Foscari": "frameB_green",
            "Chalcedony": "frameB_purple",
            "FirstBlood": "frameB_gray",
            "IS": "frameB_red",
        }
        if not entry.get("isRelic"):
            return "frameC"

        return frames_dict.get(entry.get(self.key_frame_name), self.default_frame_name)


def get_generator(file) -> SimpleGenerator | None:
    if "weapon" in file:
        return None
    if "item" in file:
        return ItemGenerator()

    return None

class GeneratorDialog(tk.Toplevel):
    def __init__(self, gen: SimpleGenerator, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("Select settings")
        ttk.Label(self, text="Select settings for exporting files").pack()

        self.settings = dict()

        gen_types_order = GenType.get_order()
        available_gens = gen.get_available_gens()
        gens_tips = gen.get_gens_tips()

        for gen_type in gen_types_order:
            if gen_type not in available_gens:
                continue

            if gen_type == GenType.IMAGE:
                ttk.Label(self, text=gens_tips[gen_type]).pack()
                scale_input = ttk.Entry(self)
                scale_input.insert(0, str(gen.default_scale_factor))
                scale_input.pack()

                self.settings.update({gen_type: lambda: int(scale_input.get())})
            else:
                bool_var = tk.BooleanVar()
                ttk.Checkbutton(self, text=gens_tips[gen_type], variable=bool_var).pack()

                self.settings.update({gen_type: lambda: bool_var.get()})

        b_ok = ttk.Button(self, text="Start", command=self.__close)
        b_ok.pack()

        self.protocol("WM_DELETE_WINDOW", self.__close_exit)

    def __close_exit(self):
        self.return_data = None
        self.destroy()

    def __close(self):
        self.return_data = {k.value: v() for k, v in self.settings.items()}
        self.destroy()