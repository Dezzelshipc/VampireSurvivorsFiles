import os
import re
import sys
import tkinter as tk
import tkinter.ttk as ttk
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

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
ADD_TO_PATH_ENTRY = "add_to_path_entry"
UNIQUE_SHORT_CHARACTER_NAME = "unique_short_character_name"
FULL_CHARACTER_NAME = "full_character_name"

FONT_FILE_PATH = to_source_path(IMAGES_FOLDER / "Courier.ttf")


class GenType(Enum):
    IMAGE = 0
    IMAGE_FRAME = 1

    ANIM = 10
    DEATH_ANIM = 11
    ATTACK_ANIM = 12

    ARCANA_PICTURE = 20

    STAGE_WITH_NAME = 30

    @classmethod
    def get_types(cls) -> set["GenType"]:
        return {*cls}

    def get_tip(self):
        match self:
            case GenType.IMAGE:
                return "Scale factor"
            case GenType.IMAGE_FRAME:
                return "Generate frame variants"

            case GenType.ANIM:
                return "Generate animations"
            case GenType.DEATH_ANIM:
                return "Generate death animations"
            case GenType.ATTACK_ANIM:
                return "Generate attack animations"

            case GenType.ARCANA_PICTURE:
                return "Generate arcana pictures"

            case GenType.STAGE_WITH_NAME:
                return "Generate with stage name"


@dataclass
class EntryToSave:
    image: Image
    name: str
    name_wrapper: Callable[[str], str]
    key_id: str

    def save_entry(self, save_path: Path, entry: dict[str, Any], scale: int,
                   add_to_path: os.PathLike[str] | str = None) -> None:
        entry_save_path = save_path / entry.get("contentGroup", "BASE_GAME")
        if self.name == self.key_id:
            entry_save_path /= "No lang"
        if add_to_path:
            entry_save_path /= add_to_path
        if add_to_path_entry := entry.get(ADD_TO_PATH_ENTRY):
            entry_save_path /= add_to_path_entry

        entry_save_path.mkdir(parents=True, exist_ok=True)

        image = resize_image(self.image, scale)
        image.save(entry_save_path / self.name_wrapper(self.name))


@dataclass
class SpriteEntryToSave(EntryToSave):
    sprite_data: SpriteData

    def __init__(self, sprite_data: SpriteData, name: str, name_wrapper: Callable[[str], str], key_id) -> None:
        self.sprite_data = sprite_data
        self.image = sprite_data.sprite
        self.name = name
        self.name_wrapper = name_wrapper
        self.key_id = key_id


class ImageGeneratorManager:
    @staticmethod
    def get_gen(data_type: DataType) -> "BaseImageGenerator".__class__ | None:
        match data_type:
            case DataType.ACHIEVEMENT:
                return None
            case DataType.ADVENTURE:
                return None
            case DataType.ADVENTURE_MERCHANTS:
                return AdvMerchantsGenerator
            case DataType.ADVENTURE_STAGE_SET:
                return None
            case DataType.ALBUM:
                return AlbumCoversGenerator
            case DataType.ARCANA:
                return ArcanaImageGenerator
            case DataType.CHARACTER:
                return CharacterImageGenerator
            case DataType.CUSTOM_MERCHANTS:
                return None
            case DataType.ENEMY:
                return None # EnemyImageGenerator
            case DataType.HIT_VFX:
                return None
            case DataType.ITEM:
                return ItemImageGenerator
            case DataType.LIMIT_BREAK:
                return None
            case DataType.MUSIC:
                return MusicIconsGenerator
            case DataType.POWER_UP:
                return PowerUpImageGenerator
            case DataType.PROPS:
                return PropsImageGenerator
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
                           func_progress_bar_set_percent: PROGRESS_BAR_FUNC_TYPE = lambda c, t: 0,
                           parent=None) -> Path | None:
        data_to_process = DataHandler.get_data(dlc_type, data_type)

        gen: BaseImageGenerator = ImageGeneratorManager.get_gen(data_type)()

        if not gen:
            return None

        dialog = GeneratorDialog(gen, parent=parent)
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

    save_image_prefix = "Sprite"
    save_icon_prefix = "Icon"

    key_main_texture_name = None
    key_sprite_name = None
    key_frame_name = None
    key_entry_name = "name"

    default_main_texture_name = None

    is_use_data_name = False

    default_frame_name = None

    def __init__(self):
        self.requested_gens: dict[GenType, int | bool] = None
        self.entries: list[dict] = None
        self.meta_data: dict[str, MetaData] = None
        self.lang_data: dict[str, Any] | None = None

    def load_data(self, data: DataFile, requested_gen_types: dict[GenType, int | bool]) -> None:
        self.requested_gens = requested_gen_types
        lang_data_full = LangHandler.get_lang_file(self.lang_type) or {}
        self.lang_data = lang_data_full and lang_data_full.get_lang(Lang.EN) or {}
        self.entries = [
            self.get_unit(key_id, entry.copy()) for key_id, entry in data.data().items()
        ]
        self.meta_data = MetaDataHandler.get_meta_dict_by_name_set(self.get_textures_set())

        for texture_name, meta_data in self.meta_data.items():
            meta_data.init_sprites()

    def main_generator(self, dlc_type: DLCType | COMPOUND_DATA_TYPE, data_type: DataType,
                       func_progress_bar_set_percent: PROGRESS_BAR_FUNC_TYPE = lambda c, t: 0) -> Path | None:
        scale = self.requested_gens[GenType.IMAGE]

        save_path = IMAGES_FOLDER / GENERATED / data_type.value / DLCType.string(dlc_type)
        save_path.mkdir(parents=True, exist_ok=True)

        total_len = len(self.entries)

        if self.requested_gens.get(GenType.IMAGE):
            for i, entry in enumerate(self.entries):
                out_entry = self.gen_image(entry)
                if out_entry:
                    out_entry.save_entry(save_path, entry, scale)

                func_progress_bar_set_percent(i + 1, total_len)

        if self.requested_gens.get(GenType.IMAGE_FRAME):
            for i, entry in enumerate(self.entries):
                out_entry = self.gen_image_with_frame(entry)
                if out_entry:
                    out_entry.save_entry(save_path, entry, scale, add_to_path="Icon")

                func_progress_bar_set_percent(i + 1, total_len)

        return save_path

    @classmethod
    def get_available_gens(cls) -> list[GenType]:
        return cls._available_gens

    def get_save_name(self, name: str) -> str:
        return re.sub(r'[<>:/|\\?*]', '', name.strip())

    def get_unit(self, key_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        entry.update({
            KEY_ID: key_id
        })
        return entry

    def get_frame_name(self, entry: dict[str, Any]) -> str:
        return entry.get(self.key_frame_name, self.default_frame_name).replace(".png", "")

    def get_textures_set(self) -> set[str]:
        textures_set = {entry.get(self.key_main_texture_name) for entry in self.entries}
        if None in textures_set:
            textures_set.discard(None)
        textures_set.add(UI)
        return textures_set

    def gen_image(self, entry: dict[str, Any]) -> SpriteEntryToSave | None:
        main_texture = normalize_str(entry.get(self.key_main_texture_name, self.default_main_texture_name))
        sprite_texture = normalize_str(entry.get(self.key_sprite_name))

        texture_meta_data = self.meta_data.get(main_texture)
        if not texture_meta_data:
            print(f"!!! Skipped '{sprite_texture}': texture '{main_texture}' not found", file=sys.stderr)
            return None

        sprite_data = texture_meta_data.data_name.get(sprite_texture)
        if not sprite_data:
            print(f"!!! Skipped '{sprite_texture}': not found for texture '{main_texture}'", file=sys.stderr)
            return None

        key_id = entry.get(KEY_ID)
        if self.is_use_data_name:
            lang_entry = entry
        else:
            lang_entry = self.lang_data and self.lang_data.get(key_id) or {}

        eng_name = lang_entry.get(self.key_entry_name) or key_id

        return SpriteEntryToSave(
            sprite_data,
            eng_name,
            lambda x: f"{self.save_image_prefix}-{self.get_save_name(x)}.png",
            entry.get(KEY_ID)
        )

    def gen_image_with_frame(self, entry: dict[str, Any]) -> EntryToSave | None:
        out_image_data: SpriteEntryToSave | None = self.gen_image(entry)
        if out_image_data is None:
            return None

        image_data = out_image_data.sprite_data
        eng_name = out_image_data.name
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

        return EntryToSave(
            frame,
            eng_name,
            lambda x: f"{self.save_icon_prefix}-{self.get_save_name(x)}.png",
            entry.get(KEY_ID)
        )

    # def gen_anim(self, entry: dict[str, Any]):
    #     pass
    #
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

    default_frame_name = "frameC"

    def get_frame_name(self, entry: dict[str, Any]) -> str:
        frame = super().get_frame_name(entry)
        return "frameF" if entry.get("isRelic") and frame == self.default_frame_name else frame


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

    default_frame_name = "frameG"

    key_secondary_texture_name = "texture2"

    def get_frame_name(self, entry: dict[str, Any]) -> str:
        return "frameH" if entry.get("arcanaType") >= 22 else super().get_frame_name(entry)

    def get_save_name(self, name: str) -> str:
        name = super().get_save_name(name)
        return name[name.find("-") + 1:].strip()

    def get_unit(self, key_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        entry = super().get_unit(key_id, entry)
        entry.update({
            self.key_main_texture_name: "items",
            self.key_secondary_texture_name: entry.get(self.key_main_texture_name),
        })
        return entry

    def get_textures_set(self) -> set[str]:
        textures_set = super().get_textures_set()
        textures_set.update({entry.get(self.key_secondary_texture_name) for entry in self.entries})
        return textures_set

    def main_generator(self, dlc_type: DLCType | COMPOUND_DATA_TYPE, data_type: DataType,
                       func_progress_bar_set_percent: PROGRESS_BAR_FUNC_TYPE = lambda c, t: 0) -> Path | None:
        save_path = super().main_generator(dlc_type, data_type)
        scale = self.requested_gens.get(GenType.IMAGE)

        total_len = len(self.entries)

        if self.requested_gens.get(GenType.ARCANA_PICTURE):
            for i, entry in enumerate(self.entries):
                out_entry: EntryToSave | None = self.gen_arcana_picture(entry)
                if out_entry:
                    out_entry.save_entry(save_path, entry, scale, add_to_path="Picture")

                func_progress_bar_set_percent(i + 1, total_len)

        return save_path

    def gen_arcana_picture(self, entry: dict[str, Any]) -> EntryToSave | None:
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

        key_id = entry.get(KEY_ID)
        lang_entry = self.lang_data and self.lang_data.get(key_id) or {}

        eng_name = lang_entry.get(self.key_entry_name) or key_id

        return EntryToSave(
            sprite_data.sprite,
            eng_name,
            lambda x: f"{self.save_image_prefix}-{self.get_save_name(x)}.png",
            entry.get(KEY_ID)
        )


class PropsImageGenerator(BaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.ANIM]

    assets_type: DataType = DataType.PROPS
    lang_type: LangType = LangType.NONE

    default_scale_factor = 1

    save_image_prefix = "Sprite"
    save_icon_prefix = "Icon"

    key_main_texture_name = "textureName"
    key_sprite_name = "frameName"
    key_frame_name = None

    default_frame_name = None

    def get_unit(self, key_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        entry = super().get_unit(key_id, entry)
        entry.update({
            self.key_sprite_name: f"{entry.get(self.key_sprite_name)}1",
        })
        return entry


class AdvMerchantsGenerator(BaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.ANIM]

    assets_type: DataType = DataType.ADVENTURE_MERCHANTS
    lang_type: LangType = LangType.CHARACTER

    default_scale_factor = 1

    save_image_prefix = "Sprite"
    save_icon_prefix = "Icon"

    key_main_texture_name = "staticSpriteTexture"
    key_sprite_name = "staticSprite"
    key_frame_name = None
    key_entry_name = "charName"

    default_frame_name = None


class AlbumCoversGenerator(BaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE]

    assets_type: DataType = DataType.ALBUM
    lang_type: LangType = LangType.NONE

    default_scale_factor = 1

    save_image_prefix = "Album"

    key_main_texture_name = "icon"
    key_sprite_name = "icon"
    key_entry_name = "title"

    is_use_data_name = True


class MusicIconsGenerator(BaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE]

    assets_type: DataType = DataType.MUSIC
    lang_type: LangType = LangType.NONE

    default_scale_factor = 1

    save_image_prefix = "Music"

    key_main_texture_name = None
    key_sprite_name = "icon"
    key_frame_name = None
    key_entry_name = "title"

    default_main_texture_name = UI

    is_use_data_name = True

    def get_unit(self, key_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        entry = super().get_unit(key_id, entry)

        add_to_path = ""
        check = entry.get("source").lower() or entry.get("title").lower()
        if "castlevania" in check:
            add_to_path = entry.get("source")
        if "vampire survivors" in check:
            add_to_path = entry.get("author")

        entry.update({
            ADD_TO_PATH_ENTRY: add_to_path
        })
        return entry


class ListBaseImageGenerator(BaseImageGenerator):
    def get_unit(self, key_id: str, entry: list[dict[str, Any]]) -> dict[str, Any]:
        return super().get_unit(key_id, entry[0])


class WeaponImageGenerator(ListBaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.IMAGE_FRAME]

    assets_type: DataType = DataType.WEAPON
    lang_type: LangType = LangType.WEAPON

    key_main_texture_name = "texture"
    key_sprite_name = "frameName"
    key_frame_name = "collectionFrame"

    default_frame_name = "frameB"


class PowerUpImageGenerator(ListBaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.IMAGE_FRAME]

    assets_type: DataType = DataType.POWER_UP
    lang_type: LangType = LangType.POWER_UP

    default_scale_factor = 1

    save_image_prefix = "Sprite"
    save_icon_prefix = "Icon"

    key_main_texture_name = "texture"
    key_sprite_name = "frameName"

    default_frame_name = "frameD"

    def get_frame_name(self, entry: dict[str, Any]) -> str:
        frame = super().get_frame_name(entry)
        return "frameE" if entry.get("specialBG") and frame == self.default_frame_name else frame


class CharacterImageGenerator(ListBaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE]

    assets_type: DataType = DataType.CHARACTER
    lang_type: LangType = LangType.CHARACTER

    save_image_prefix = "Sprite"
    save_icon_prefix = "Select"

    key_main_texture_name = "textureName"
    key_sprite_name = "spriteName"
    key_frame_name = None
    key_entry_name = FULL_CHARACTER_NAME

    default_frame_name = "CharacterSelectFrame.png"

    is_use_data_name = True

    def __init__(self):
        super(ListBaseImageGenerator).__init__()

        self.lang_skin_data: dict[str, Any] | None = None

    def get_unit(self, key_id: str, entry: list[dict[str, Any]]) -> dict[str, Any]:
        entry = super().get_unit(key_id, entry)
        lang_entry = self.lang_data and self.lang_data.get(key_id) or {}
        prefix = lang_entry.get("prefix") or ""
        char_name = lang_entry.get("charName") or ""
        surname = lang_entry.get("surname") or ""
        entry.update({
            FULL_CHARACTER_NAME: f"{prefix} {char_name} {surname}".strip()
        })
        return entry

    def load_data(self, data: DataFile, requested_gen_types: dict[GenType, int | bool]) -> None:
        super().load_data(data, requested_gen_types)

        lang_data_full = LangHandler.get_lang_file(LangType.SKIN) or {}
        self.lang_skin_data = lang_data_full and lang_data_full.get_lang(Lang.EN) or {}


class EnemyImageGenerator(ListBaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE]

    assets_type: DataType = DataType.ENEMY
    lang_type: LangType = LangType.ENEMIES

    save_image_prefix = "Sprite"

    key_main_texture_name = "textureName"
    key_sprite_name = "frameNames"
    key_frame_name = None
    key_entry_name = "bName"

    def __init__(self):
        super().__init__()
        raise NotImplementedError(f"{self.__class__.__name__} not implemented")


class GeneratorDialog(tk.Toplevel):
    def __init__(self, gen: BaseImageGenerator, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("Select settings")
        ttk.Label(self, text="Select settings for image generator").pack()
        ttk.Label(self, text=f"({gen.assets_type})").pack()

        self.settings = dict()

        gen_types_order = list(sorted(GenType.get_types(), key=lambda x: x.value))
        available_gens = gen.get_available_gens()

        for gen_type in gen_types_order:
            if gen_type not in available_gens:
                continue

            if gen_type == GenType.IMAGE:
                ttk.Label(self, text=gen_type.get_tip()).pack()
                scale_input = ttk.Entry(self)
                scale_input.insert(0, str(gen.default_scale_factor))
                scale_input.pack()

                self.settings.update({gen_type: scale_input})
            else:
                bool_var = tk.BooleanVar()
                ttk.Checkbutton(self, text=gen_type.get_tip(), variable=bool_var, takefocus=False).pack()

                self.settings.update({gen_type: bool_var})

        ttk.Button(self, text="Start", command=self.__close).pack()

        self.protocol("WM_DELETE_WINDOW", self.__close_exit)

    def __close_exit(self):
        self.return_data = None
        self.destroy()

    def __close(self):
        self.return_data = {k: v.get() if k != GenType.IMAGE else int(v.get()) for k, v in self.settings.items()}
        self.destroy()
