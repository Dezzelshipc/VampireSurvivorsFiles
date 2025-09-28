import os
import re
import sys
import tkinter as tk
import tkinter.ttk as ttk
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from PIL import ImageFont, ImageDraw
from PIL.Image import Image, open as image_open, new as image_new

from Source.Config.config import DLCType
from Source.Data.data import DataHandler, DataType, DataFile
from Source.Translations.language import LangHandler, LangType, Lang
from Source.Utility.constants import to_source_path, IMAGES_FOLDER, COMPOUND_DATA_TYPE, GENERATED, \
    PROGRESS_BAR_FUNC_TYPE, COMPOUND_DATA
from Source.Utility.image_functions import make_image_black
from Source.Utility.image_functions import resize_image, get_adjusted_sprites_to_rect, get_rects_by_sprite_list
from Source.Data.meta_data import MetaDataHandler
from Source.Utility.sprite_data import SpriteData
from Source.Utility.utility import normalize_str

PREFIX = "prefix"
CHAR_NAME = "charName"
SURNAME = "surname"
UI = "UI"

KEY_ID = "key_id"
ADD_TO_PATH_ENTRY = "add_to_path_entry"
UNIQUE_SHORT_CHARACTER_NAME = "unique_short_character_name"
FULL_CHARACTER_NAME = "full_character_name"

FONT_FILE_PATH = to_source_path(IMAGES_FOLDER) / "Courier.ttf"


class GenType(Enum):
    IMAGE = 0
    IMAGE_FRAME = 1

    ANIM = 10
    DEATH_ANIM = 11
    ATTACK_ANIM = 12

    ARCANA_PICTURE = 20

    # CHARACTER_SELECT = 30

    STAGE_WITH_NAME = 40

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

            # case GenType.CHARACTER_SELECT:
            #     return "Generate special select"

            case GenType.STAGE_WITH_NAME:
                return "Generate with stage name"
        return None


@dataclass
class EntryToSave:
    image: Image
    name: str
    name_wrapper: Callable[[str], str]
    add_to_path: str | None = None

    def save_entry(self, save_path: Path,
                   entry: dict[str, Any],
                   scale: int,
                   add_to_path: os.PathLike[str] | str = None) -> None:
        entry_save_path = save_path / entry.get("contentGroup", "BASE_GAME")
        key_id = entry.get(KEY_ID)
        if self.name == key_id:
            entry_save_path /= "No lang"
        if entry.get("alwaysHidden"):
            entry_save_path /= "Always hidden"
        if add_to_path:
            entry_save_path /= add_to_path
        if add_to_path_entry := entry.get(ADD_TO_PATH_ENTRY):
            entry_save_path /= add_to_path_entry
        if self.add_to_path:
            entry_save_path /= self.add_to_path

        entry_save_path.mkdir(parents=True, exist_ok=True)

        image = resize_image(self.image, scale)
        image.save(entry_save_path / self.name_wrapper(self.name))


@dataclass
class SpriteEntryToSave(EntryToSave):
    sprite_data: SpriteData = None

    def __init__(self, sprite_data: SpriteData, name: str, name_wrapper: Callable[[str], str]) -> None:
        self.sprite_data = sprite_data
        self.image = sprite_data.sprite
        self.name = name
        self.name_wrapper = name_wrapper


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
            case DataType.ADVENTURE_STAGE:
                return AdventureStageImageGenerator
            case DataType.ADVENTURE_STAGE_SET:
                return None
            case DataType.ALBUM:
                return AlbumCoversGenerator
            case DataType.ARCANA:
                return ArcanaImageGenerator
            case DataType.CHARACTER:
                return CharacterImageGenerator
            case DataType.CPU:
                return CpuGenerator
            case DataType.CUSTOM_MERCHANTS:
                return None
            case DataType.ENEMY:
                return None  # EnemyImageGenerator
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
                return StageImageGenerator
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
        gen_class: BaseImageGenerator.__class__ = ImageGeneratorManager.get_gen(data_type)

        if not gen_class:
            return None

        dialog = GeneratorDialog(gen_class, parent=parent)
        dialog.wait_window()
        req_gens: dict[GenType, int | bool] | None = dialog.return_data

        if not req_gens:
            return None

        print(f"Selected settings for {gen_class.__name__}: {req_gens}")

        gen: BaseImageGenerator = gen_class(dlc_type, data_type, req_gens)

        save_path = gen.main_generator(dlc_type, data_type, func_progress_bar_set_percent)

        return save_path


class BaseImageGenerator:
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.IMAGE_FRAME]

    data_type: DataType = DataType.NONE
    lang_type: LangType = LangType.NONE

    default_scale_factor = 1

    save_image_prefix = "Sprite"
    save_icon_prefix = "Icon"

    key_main_texture_name = None
    key_sprite_name = None
    key_frame_name = None
    key_entry_name = "name"

    default_main_texture_name = None

    default_frame_name = None

    def __init__(self, dlc_type: DLCType | COMPOUND_DATA_TYPE, data_type: DataType,
                 requested_gen_types: dict[GenType, int | bool]):
        self.data_file: DataFile | None = DataHandler.get_data(dlc_type, data_type)

        lang_data_full = LangHandler.get_lang_file(self.lang_type) or {}
        self.lang_data = lang_data_full and lang_data_full.get_lang(Lang.EN) or {}

        self.requested_gens = requested_gen_types
        self._set_entries()
        self.meta_data = MetaDataHandler.get_meta_dict_by_name_set_fullest(self.get_textures_set())

        for texture_name, meta_data in self.meta_data.items():
            meta_data.init_sprites()

    def _set_entries(self):
        self.entries = [
            self.get_unit(key_id, entry.copy()) for key_id, entry in self.data_file.data().items()
        ]

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
        to_update: dict[str, Any] = {
            KEY_ID: key_id,
        }

        if self.lang_type != LangType.NONE:
            lang_entry = self.lang_data and self.lang_data.get(key_id) or {}
            entry_name = lang_entry.get(self.key_entry_name) or ""
            to_update[self.key_entry_name] = entry_name

        entry.update(to_update)

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

        eng_name = entry.get(self.key_entry_name) or entry.get(KEY_ID)

        return SpriteEntryToSave(
            sprite_data,
            eng_name,
            lambda x: f"{self.save_image_prefix}-{self.get_save_name(x)}.png"
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
            lambda x: f"{self.save_icon_prefix}-{self.get_save_name(x)}.png"
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

    data_type: DataType = DataType.ITEM
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

    data_type: DataType = DataType.ARCANA
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
        if entry.get("arcanaType") > 100:
            entry.update({
                ADD_TO_PATH_ENTRY: "Characters"
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

        eng_name = entry.get(self.key_entry_name) or entry.get(KEY_ID)

        return EntryToSave(
            sprite_data.sprite,
            eng_name,
            lambda x: f"{self.save_image_prefix}-{self.get_save_name(x)}.png"
        )


class PropsImageGenerator(BaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.ANIM]

    data_type: DataType = DataType.PROPS
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

    data_type: DataType = DataType.ADVENTURE_MERCHANTS
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

    data_type: DataType = DataType.ALBUM
    lang_type: LangType = LangType.NONE

    default_scale_factor = 1

    save_image_prefix = "Album"

    key_main_texture_name = "icon"
    key_sprite_name = "icon"
    key_entry_name = "title"


class MusicIconsGenerator(BaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE]

    data_type: DataType = DataType.MUSIC
    lang_type: LangType = LangType.NONE

    default_scale_factor = 1

    save_image_prefix = "Music"

    key_main_texture_name = None
    key_sprite_name = "icon"
    key_frame_name = None
    key_entry_name = "title"

    default_main_texture_name = UI

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


class CpuGenerator(BaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE]

    data_type: DataType = DataType.CPU
    lang_type: LangType = LangType.PARTY

    default_scale_factor = 1

    save_image_prefix = "Cpu"

    key_main_texture_name = "AIIconTexture"
    key_sprite_name = "AIIconSprite"
    key_entry_name = "name"


class ListBaseImageGenerator(BaseImageGenerator):
    def get_unit(self, key_id: str, entry: list[dict[str, Any]]) -> dict[str, Any]:
        return super().get_unit(key_id, entry[0])


class WeaponImageGenerator(ListBaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.IMAGE_FRAME]

    data_type: DataType = DataType.WEAPON
    lang_type: LangType = LangType.WEAPON

    key_main_texture_name = "texture"
    key_sprite_name = "frameName"
    key_frame_name = "collectionFrame"

    default_frame_name = "frameB"


class PowerUpImageGenerator(ListBaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.IMAGE_FRAME]

    data_type: DataType = DataType.POWER_UP
    lang_type: LangType = LangType.POWER_UP

    default_scale_factor = 1

    save_image_prefix = "Sprite"
    save_icon_prefix = "PowerUp"

    key_main_texture_name = "texture"
    key_sprite_name = "frameName"

    default_frame_name = "frameD"

    def get_frame_name(self, entry: dict[str, Any]) -> str:
        frame = super().get_frame_name(entry)
        return "frameE" if entry.get("specialBG") and frame == self.default_frame_name else frame


class CharacterImageGenerator(ListBaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.IMAGE_FRAME]

    data_type: DataType = DataType.CHARACTER
    lang_type: LangType = LangType.CHARACTER

    save_image_prefix = "Sprite"
    save_icon_prefix = "Select"

    key_main_texture_name = "textureName"
    key_sprite_name = "spriteName"
    key_frame_name = None
    key_entry_name = FULL_CHARACTER_NAME

    default_frame_name = "CharacterSelectFrame.png"

    def __init__(self, dlc_type: DLCType | COMPOUND_DATA_TYPE, data_type: DataType,
                 requested_gen_types: dict[GenType, int | bool]):
        super().__init__(dlc_type, data_type, requested_gen_types)

        lang_data_full = LangHandler.get_lang_file(LangType.SKIN) or {}
        self.lang_skin_data: dict[str, Any] | None = lang_data_full and lang_data_full.get_lang(Lang.EN) or {}

        self.weapon_image_gen = None
        self.frame_image = None

        if requested_gen_types.get(GenType.IMAGE_FRAME):
            self.weapon_image_gen = WeaponImageGenerator(COMPOUND_DATA, DataType.WEAPON, {GenType.IMAGE: 1})
            image_path = to_source_path(IMAGES_FOLDER) / self.default_frame_name
            self.frame_image = image_open(image_path)

    def get_unit(self, key_id: str, entry: list[dict[str, Any]]) -> dict[str, Any]:
        entry = super().get_unit(key_id, entry)
        lang_entry = self.lang_data and self.lang_data.get(key_id) or {}
        prefix = lang_entry.get(PREFIX) or ""
        char_name = lang_entry.get(CHAR_NAME) or ""
        surname = lang_entry.get(SURNAME) or ""
        entry.update({
            PREFIX: prefix,
            CHAR_NAME: char_name,
            SURNAME: surname,
            FULL_CHARACTER_NAME: f"{prefix} {char_name} {surname}".strip()
        })
        return entry

    def gen_image_with_frame(self, entry: dict[str, Any]) -> EntryToSave | None:
        out_image_data: SpriteEntryToSave | None = self.gen_image(entry)
        if out_image_data is None:
            return None

        image_data = out_image_data.sprite_data
        eng_name = out_image_data.name

        char_sprite = resize_image(image_data.sprite, 3.8)
        frame_image = self.frame_image.copy()

        if (weapon_id := entry.get("startingWeapon")) and weapon_id not in ["VOID", "0", 0, None]:
            weapon_data = self.weapon_image_gen.data_file.data().get(weapon_id)
            weapon_entry = self.weapon_image_gen.gen_image(self.weapon_image_gen.get_unit(weapon_id, weapon_data))

            weapon_image = resize_image(weapon_entry.image, 4)
            weapon_image_shadow = make_image_black(weapon_image)

            weapon_offset = {
                "x": frame_image.width - weapon_image.width - 10, "y": frame_image.height - weapon_image.height - 12
            }

            frame_image.alpha_composite(weapon_image_shadow, (weapon_offset["x"], weapon_offset["y"]))
            frame_image.alpha_composite(weapon_image, (weapon_offset["x"] - 8, weapon_offset["y"] - 4))

        frame_image.alpha_composite(char_sprite, (12, frame_image.height - char_sprite.height - 11))

        text = entry.get(CHAR_NAME)
        font = ImageFont.truetype(FONT_FILE_PATH, 30)
        width = font.getbbox(text)[2] + 4
        height = font.getbbox(text + "|")[3]

        if width > frame_image.size[0] - 4:
            if " " in text:
                text = text[::-1].replace(" ", "\n", 1)[::-1]

            font = ImageFont.truetype(FONT_FILE_PATH, 28)
            width = font.getbbox(text)[2] + 4
            height = (font.getbbox("|" + text + "|")[3] + 1) * 2

        canvas = image_new('RGBA', (int(width), int(height)))

        draw = ImageDraw.Draw(canvas)
        draw.text((3, -5), text, "#ffffff", font, stroke_width=1)

        # canvas.save(f"{sf_text}/text/{self.iconPrefix}-{save_name}.png")

        frame_image.alpha_composite(canvas, (14, 20))

        return EntryToSave(
            frame_image,
            eng_name,
            lambda x: f"{self.save_icon_prefix}-{self.get_save_name(x)}.png"
        )


class EnemyImageGenerator(ListBaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE]

    data_type: DataType = DataType.ENEMY
    lang_type: LangType = LangType.ENEMIES

    save_image_prefix = "Sprite"

    key_main_texture_name = "textureName"
    key_sprite_name = "frameNames"
    key_frame_name = None
    key_entry_name = "bName"

    def __init__(self, dlc_type: DLCType | COMPOUND_DATA_TYPE, data_type: DataType,
                 requested_gen_types: dict[GenType, int | bool]):
        super().__init__(dlc_type, data_type, requested_gen_types)
        raise NotImplementedError(f"{self.__class__.__name__} not implemented")


class StageImageGenerator(ListBaseImageGenerator):
    _available_gens: list[GenType] = [GenType.IMAGE, GenType.STAGE_WITH_NAME]

    data_type: DataType = DataType.STAGE
    lang_type: LangType = LangType.STAGE

    default_scale_factor = 1

    save_image_prefix = "Stage"

    key_main_texture_name = "uiTexture"
    key_sprite_name = "uiFrame"
    key_frame_name = None
    key_entry_name = "stageName"

    def main_generator(self, dlc_type: DLCType | COMPOUND_DATA_TYPE, data_type: DataType,
                       func_progress_bar_set_percent: PROGRESS_BAR_FUNC_TYPE = lambda c, t: 0) -> Path | None:
        scale = self.requested_gens[GenType.IMAGE]
        save_path = super().main_generator(dlc_type, data_type, func_progress_bar_set_percent)

        total_len = len(self.entries)

        if self.requested_gens.get(GenType.STAGE_WITH_NAME):
            for i, entry in enumerate(self.entries):
                out_entry = self.gen_image_with_name(entry)
                if out_entry:
                    out_entry.save_entry(save_path, entry, scale, add_to_path="With name")

                func_progress_bar_set_percent(i + 1, total_len)

        return save_path

    def gen_image_with_name(self, entry: dict[str, Any]) -> EntryToSave | None:
        out_image_data: SpriteEntryToSave | None = self.gen_image(entry)
        if out_image_data is None:
            return None

        image_data = out_image_data.sprite_data
        eng_name = out_image_data.name

        stage_image = resize_image(image_data.sprite, 4)

        text = eng_name.strip()
        base_scale = 50
        while True:
            font = ImageFont.truetype(FONT_FILE_PATH, base_scale)
            w = font.getbbox(text)[2] + 4
            h = font.getbbox(text + "|")[3]
            if w + 40 > stage_image.size[0]:
                base_scale -= 2
            else:
                break

        canvas = image_new('RGBA', (int(w), int(h)))

        draw = ImageDraw.Draw(canvas)
        draw.text((3, -5), text, "#eef92b", font, stroke_width=1)

        crx, cry = stage_image.size
        crx //= 2
        cry //= 5
        frx, fry = canvas.size
        frx //= 2
        fry //= 2
        stage_image.alpha_composite(canvas, (crx - frx, cry - fry))

        return EntryToSave(
            stage_image,
            eng_name,
            lambda x: f"{self.save_image_prefix}-{self.get_save_name(x)}.png"
        )


class AdventureStageImageGenerator(StageImageGenerator):
    data_type: DataType = DataType.ADVENTURE_STAGE

    stage_set: DataFile = None
    stage_to_stage_set: dict[str, str] | None = None

    def __init__(self, dlc_type: DLCType | COMPOUND_DATA_TYPE, data_type: DataType,
                 requested_gen_types: dict[GenType, int | bool]):
        self.stage_set: DataFile | None = DataHandler.get_data(dlc_type, DataType.ADVENTURE_STAGE_SET)
        self.stage_to_stage_set = {
            stage: stage_set
            for stage_set, stages in self.stage_set.data().items()
            for stage in stages
        }

        super().__init__(dlc_type, data_type, requested_gen_types)


    def get_unit(self, key_id: str, entry: list[dict[str, Any]]) -> dict[str, Any]:
        entry = super().get_unit(key_id, entry)
        entry.update({
            ADD_TO_PATH_ENTRY: self.stage_to_stage_set[key_id],
        })
        return entry


class GeneratorDialog(tk.Toplevel):
    def __init__(self, gen: BaseImageGenerator.__class__, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("Select settings")
        ttk.Label(self, text="Select settings for image generator").pack()
        ttk.Label(self, text=f"({gen.data_type})").pack()

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
