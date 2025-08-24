import re
import sys
import tkinter as tk
import tkinter.ttk as ttk
from enum import Enum
from pathlib import Path
from typing import Any

from PIL.Image import Image

from Source.Config.config import DLCType
from Source.Data.data import DataHandler, DataType, DataFile
from Source.Translations.language import LangHandler, LangType, Lang
from Source.Utility.constants import to_source_path, IMAGES_FOLDER, COMPOUND_DATA_TYPE, GENERATED, \
    PROGRESS_BAR_FUNC_TYPE
from Source.Utility.image_functions import resize_image, get_adjusted_sprites_to_rect, get_rects_by_sprite_list
from Source.Utility.meta_data import MetaDataHandler, MetaData
from Source.Utility.sprite_data import SpriteData
from Source.Utility.utility import normalize_str

UI = "UI"
KEY_ID = "key_id"

FONT_FILE_PATH = to_source_path(IMAGES_FOLDER / "Courier.ttf")


class GenType(Enum):
    IMAGE = 0
    IMAGE_FRAME = 1

    ANIM = 10
    DEATH_ANIM = 11
    ATTACK_ANIM = 12

    ARCANA_PICTURE = 20

    @classmethod
    def get_types(cls) -> set["GenType"]:
        return {*cls}


class ImageGeneratorManager:
    @staticmethod
    def get_gen(data_type: DataType) -> "BaseImageGenerator".__class__ | None:
        match data_type:
            case DataType.ACHIEVEMENT:
                return None
            case DataType.ADVENTURE:
                return None
            case DataType.ADVENTURE_MERCHANTS:
                return None
            case DataType.ADVENTURE_STAGE_SET:
                return None
            case DataType.ALBUM:
                return None
            case DataType.ARCANA:
                return ArcanaImageGenerator
            case DataType.CHARACTER:
                return None
            case DataType.CUSTOM_MERCHANTS:
                return None
            case DataType.ENEMY:
                return None
            case DataType.HIT_VFX:
                return None
            case DataType.ITEM:
                return ItemImageGenerator
            case DataType.LIMIT_BREAK:
                return None
            case DataType.MUSIC:
                return None
            case DataType.POWERUP:
                return None
            case DataType.PROPS:
                return None
            case DataType.SECRET:
                return None
            case DataType.STAGE:
                return None
            case DataType.WEAPON:
                return WeaponImageGenerator

        return None

    @staticmethod
    def get_supported_gen_types() -> set[DataType]:
        return set(filter(ImageGeneratorManager.get_gen, DataType.get_all_types()))

    @staticmethod
    def gen_unified_images(dlc_type: DLCType | COMPOUND_DATA_TYPE, data_type: DataType,
                           func_progress_bar_set_percent: PROGRESS_BAR_FUNC_TYPE = lambda c, t: 0) -> Path | None:
        data_to_process = DataHandler.get_data(dlc_type, data_type)

        gen: BaseImageGenerator = ImageGeneratorManager.get_gen(data_type)()

        if not gen:
            return None

        dialog = GeneratorDialog(gen)
        dialog.wait_window()
        req_gens: dict[GenType, int | bool] | None = dialog.return_data

        if not req_gens:
            return None

        print(f"Selected settings for {gen.__class__.__name__}: {req_gens}")

        gen.load_data(data_to_process, req_gens)

        save_path = gen.main_generator(dlc_type, data_type, func_progress_bar_set_percent)

        return save_path


class BaseImageGenerator:
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.IMAGE_FRAME]

    assets_type: DataType = DataType.NONE
    lang_type: LangType = LangType.NONE

    default_scale_factor = 1

    save_image_prefix = None
    save_icon_prefix = "Icon"

    key_main_texture_name = None
    key_sprite_name = None
    key_frame_name = None

    default_frame_name = None

    def __init__(self):
        self.requested_gens: dict[GenType, int | bool] = None
        self.entries: list[dict] = None
        self.meta_data: dict[str, MetaData] = None

    def load_data(self, data: DataFile, requested_gen_types: dict[GenType, int | bool]) -> None:
        self.entries = [
            self.get_unit(key_id, entry.copy()) for key_id, entry in data.data().items()
        ]
        self.requested_gens = requested_gen_types
        self.meta_data = MetaDataHandler.get_meta_dict_by_name_set(self.get_textures_set())

        for texture_name, meta_data in self.meta_data.items():
            meta_data.init_sprites()

    def main_generator(self, dlc_type: DLCType | COMPOUND_DATA_TYPE, data_type: DataType,
                       func_progress_bar_set_percent: PROGRESS_BAR_FUNC_TYPE = lambda c, t: 0) -> Path | None:
        scale = self.requested_gens[GenType.IMAGE]

        save_path = IMAGES_FOLDER / GENERATED / data_type.value / DLCType.string(dlc_type)
        save_path.mkdir(parents=True, exist_ok=True)

        total_len = len(self.entries)

        if self.requested_gens[GenType.IMAGE]:
            for i, entry in enumerate(self.entries):
                out_image: tuple[SpriteData, str] | None = self.gen_image(entry)
                if out_image is None:
                    continue

                image_data, eng_name = out_image
                image = image_data.sprite

                entry_save_path = save_path / entry.get("contentGroup", "BASE_GAME")
                entry_save_path.mkdir(parents=True, exist_ok=True)

                image = resize_image(image, scale)
                image.save(entry_save_path / f"{self.save_image_prefix}-{self.get_save_name(eng_name)}.png")

                func_progress_bar_set_percent(i + 1, total_len)

        if self.requested_gens[GenType.IMAGE_FRAME]:
            for i, entry in enumerate(self.entries):
                out_image: tuple[Image, str] | None = self.gen_image_with_frame(entry)
                if out_image is None:
                    continue

                image, eng_name = out_image

                entry_save_path = save_path / entry.get("contentGroup", "BASE_GAME") / "Icon"
                entry_save_path.mkdir(parents=True, exist_ok=True)

                image = resize_image(image, scale)
                image.save(entry_save_path / f"{self.save_icon_prefix}-{self.get_save_name(eng_name)}.png")

                func_progress_bar_set_percent(i + 1, total_len)

        return save_path

    @classmethod
    def get_available_gens(cls) -> list[GenType]:
        return cls._available_gens

    @staticmethod
    def get_gens_tips() -> dict[GenType, str]:
        return {
            GenType.IMAGE: "Scale factor",
            GenType.IMAGE_FRAME: "Generate frame variants",

            GenType.ANIM: "Generate animations",
            GenType.DEATH_ANIM: "Generate death animations",
            GenType.ATTACK_ANIM: "Generate attack animations",

            GenType.ARCANA_PICTURE: "Generate arcana pictures",
        }

    def get_save_name(self, name) -> str:
        return re.sub(r'[<>:/|\\?*]', '', name.strip())

    def get_unit(self, key_id: str, entry: dict) -> dict:
        entry.update({
            KEY_ID: key_id
        })
        return entry

    def get_frame_name(self, entry: dict):
        return entry.get(self.key_frame_name, self.default_frame_name).replace(".png", "")

    def get_textures_set(self) -> set:
        textures_set = {entry.get(self.key_main_texture_name) for entry in self.entries}
        textures_set.add(UI)
        return textures_set

    def gen_image(self, entry: dict[str, Any]) -> tuple[SpriteData, str] | None:
        main_texture = normalize_str(entry.get(self.key_main_texture_name))
        sprite_texture = normalize_str(entry.get(self.key_sprite_name))

        texture_meta_data = self.meta_data.get(main_texture)
        if not texture_meta_data:
            print(f"!!! Skipped '{sprite_texture}': texture '{main_texture}' not found", file=sys.stderr)
            return None

        sprite_data = texture_meta_data.data_name.get(sprite_texture)
        if not sprite_data:
            print(f"!!! Skipped '{sprite_texture}': not found for texture '{main_texture}'", file=sys.stderr)
            return None

        lang_data = LangHandler.get_lang_file(self.lang_type).get_lang(Lang.EN)
        key_id = entry.get(KEY_ID)
        lang_entry = lang_data.get(key_id) or {}

        eng_name = lang_entry.get("name") or key_id

        # print(main_texture, sprite_texture, sprite_data.name, eng_name)

        return sprite_data, eng_name

    def gen_image_with_frame(self, entry: dict[str, Any]) -> tuple[Image, str] | None:
        out_image: tuple[SpriteData, str] | None = self.gen_image(entry)
        if out_image is None:
            return None

        image_data, eng_name = out_image
        frame_name = self.get_frame_name(entry)

        texture_meta_data = self.meta_data.get(UI)
        if not texture_meta_data:
            print(f"!!! Skipped '{frame_name}': texture '{UI}' not found", file=sys.stderr)
            return None

        frame_data = texture_meta_data.data_name.get(frame_name)
        if not frame_data:
            print(f"!!! Skipped '{frame_name}': not found for texture '{UI}'", file=sys.stderr)
            return None

        rects = get_rects_by_sprite_list([image_data, frame_data])
        image, frame = get_adjusted_sprites_to_rect(zip([image_data.sprite, frame_data.sprite], rects))

        frame.alpha_composite(image)

        return frame, eng_name

    def gen_anim(self, entry: dict[str, Any]):
        pass

    # def gen_anim_death(self, entry: dict[str, Any]):
    #     pass
    #
    # def gen_anim_attack(self, entry: dict[str, Any]):
    #     pass


class ItemImageGenerator(BaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.IMAGE_FRAME]

    assets_type: DataType = DataType.ITEM
    lang_type: LangType = LangType.ITEM

    default_scale_factor = 1

    save_image_prefix = "Sprite"
    save_icon_prefix = "Icon"

    key_main_texture_name = "texture"
    key_sprite_name = "frameName"
    key_frame_name = "collectionFrame"

    default_frame_name = "frameC.png"

    def get_frame_name(self, entry: dict[str, Any]):
        return "frameF" if entry.get("isRelic") else super().get_frame_name(entry)


class ArcanaImageGenerator(BaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.IMAGE_FRAME, GenType.ARCANA_PICTURE]

    assets_type: DataType = DataType.ARCANA
    lang_type: LangType = LangType.ARCANA

    default_scale_factor = 1

    save_image_prefix = "Sprite"
    save_icon_prefix = "Icon"

    key_main_texture_name = "texture"
    key_sprite_name = "frameName"
    key_frame_name = "collectionFrame"

    default_frame_name = "frameG.png"

    key_secondary_texture_name = "texture2"

    def get_frame_name(self, entry: dict):
        return "frameH" if entry.get("arcanaType") >= 22 else super().get_frame_name(entry)

    def get_save_name(self, name) -> str:
        name = super().get_save_name(name)
        return name[name.find("-") + 1:].strip()

    def get_unit(self, key_id: str, entry: dict) -> dict:
        entry = super().get_unit(key_id, entry)
        entry.update({
            self.key_main_texture_name: "items",
            self.key_secondary_texture_name: entry.get(self.key_main_texture_name),
        })
        return entry

    def get_textures_set(self) -> set:
        textures_set = super().get_textures_set()
        textures_set.update({entry.get(self.key_secondary_texture_name) for entry in self.entries})
        return textures_set

    def main_generator(self, dlc_type: DLCType | COMPOUND_DATA_TYPE, data_type: DataType,
                       func_progress_bar_set_percent: PROGRESS_BAR_FUNC_TYPE = lambda c, t: 0) -> Path | None:
        save_path = super().main_generator(dlc_type, data_type)
        scale = self.requested_gens[GenType.IMAGE]

        total_len = len(self.entries)

        if self.requested_gens[GenType.ARCANA_PICTURE]:
            for i, entry in enumerate(self.entries):
                out_image: tuple[Image, str] | None = self.gen_arcana_picture(entry)
                if out_image is None:
                    continue

                image, eng_name = out_image

                entry_save_path = save_path / entry.get("contentGroup", "BASE_GAME") / "Picture"
                entry_save_path.mkdir(parents=True, exist_ok=True)

                image = resize_image(image, scale)
                image.save(entry_save_path / f"{self.save_image_prefix}-{self.get_save_name(eng_name)}.png")

                func_progress_bar_set_percent(i + 1, total_len)

        return save_path

    def gen_arcana_picture(self, entry: dict[str, Any]) -> tuple[Image, str] | None:
        main_texture = normalize_str(entry.get(self.key_secondary_texture_name))
        sprite_texture = normalize_str(entry.get(self.key_sprite_name))

        texture_meta_data = self.meta_data.get(main_texture)
        if not texture_meta_data:
            print(f"!!! Skipped '{sprite_texture}': texture '{main_texture}' not found", file=sys.stderr)
            return None

        sprite_data = texture_meta_data.data_name.get(sprite_texture)
        if not sprite_data:
            print(f"!!! Skipped '{sprite_texture}': not found for texture '{main_texture}'", file=sys.stderr)
            return None

        lang_data = LangHandler.get_lang_file(self.lang_type).get_lang(Lang.EN)
        key_id = entry.get(KEY_ID)
        lang_entry = lang_data.get(key_id) or {}

        eng_name = lang_entry.get("name") or key_id

        # print(main_texture, sprite_texture, sprite_data.name, eng_name)

        return sprite_data.sprite, eng_name


class ListBaseImageGenerator(BaseImageGenerator):
    def get_unit(self, key_id: str, entry: list[dict]) -> dict:
        entry = entry[0]
        entry.update({
            KEY_ID: key_id
        })
        return entry


class WeaponImageGenerator(ListBaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.IMAGE_FRAME]

    def __init__(self):
        super().__init__()

        self.assets_type: DataType = DataType.WEAPON
        self.lang_type: LangType = LangType.WEAPON

        self.default_scale_factor = 1

        self.save_image_prefix = "Sprite"
        self.save_icon_prefix = "Icon"

        self.key_main_texture_name = "texture"
        self.key_sprite_name = "frameName"
        self.key_frame_name = "collectionFrame"

        self.default_frame_name = "frameB.png"


class GeneratorDialog(tk.Toplevel):
    def __init__(self, gen: BaseImageGenerator, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("Select settings")
        ttk.Label(self, text="Select settings for image generator").pack()

        self.settings = dict()

        gen_types_order = list(sorted(GenType.get_types(), key=lambda x: x.value))
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

                self.settings.update({gen_type: scale_input})
            else:
                bool_var = tk.BooleanVar()
                ttk.Checkbutton(self, text=gens_tips[gen_type], variable=bool_var, takefocus=False).pack()

                self.settings.update({gen_type: bool_var})

        ttk.Button(self, text="Start", command=self.__close).pack()

        self.protocol("WM_DELETE_WINDOW", self.__close_exit)

    def __close_exit(self):
        self.return_data = None
        self.destroy()

    def __close(self):
        self.return_data = {k: v.get() if k != GenType.IMAGE else int(v.get()) for k, v in self.settings.items()}
        self.destroy()
