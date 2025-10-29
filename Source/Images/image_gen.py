import itertools
import os
import re
import sys
from enum import Enum

from PIL import ImageFont, ImageDraw
from PIL.Image import Image, Resampling, open as image_open, new as image_new

import Source.Images.transparent_save as tr_save
from Source.Translations.language import LangType
from Source.Utility.constants import DEFAULT_ANIMATION_FRAME_RATE, IMAGES_FOLDER, to_source_path
from Source.Utility.image_functions import get_anim_sprites_ready, resize_list_images
from Source.Data.meta_data import MetaDataHandler
from Source.Utility.sprite_data import SpriteData
from Source.Utility.utility import normalize_str
from Source.Utility.image_functions import make_image_black

K_ID = "k_id"
IS_K_ID = "is_k_id"
ENUMERATE = "enumerate"

FRAME_NAMES = "frameNames"


# TODO: Rewrite to MetaDataHandler

class OldDataType(Enum):
    NONE = None
    WEAPON = 0
    CHARACTER = 1
    ITEM = 2
    ENEMY = 3
    STAGE = 4
    STAGE_SET = 5
    ARCANA = 6
    POWERUP = 7
    PROPS = 8
    ADV_MERCHANTS = 9
    HIT_VFX = 10
    ALBUM = 11
    MUSIC = 12


class GenType(Enum):
    SCALE = 0
    FRAME = 1
    ANIM = 2
    DEATH_ANIM = 3

    SPECIAL_ANIM = 4

    @classmethod
    def main_list(cls):
        return [*cls][:-1]


class IGFactory:
    @staticmethod
    def get(data_file: str):
        data_file = data_file.lower()
        if "weapon" in data_file:
            return WeaponImageGenerator()
        elif "character" in data_file:
            return CharacterImageGenerator()
        elif "item" in data_file:
            return ItemImageGenerator()
        elif "adventurestages" in data_file:
            return StageImageGenerator()
        elif "stage" in data_file:
            return StageImageGenerator()
        elif "enemy" in data_file:
            return EnemyImageGenerator()
        elif "arcana" in data_file:
            return ArcanaImageGenerator()
        elif "powerup" in data_file:
            return PowerUpImageGenerator()
        elif "props" in data_file:
            return PropsImageGenerator()
        elif "adventuremerchants" in data_file:
            return AdvMerchantsGenerator()
        elif "hitvfx" in data_file:
            return HitVFXGenerator()
        elif "album" in data_file:
            return AlbumCoversGenerator()
        elif "music" in data_file:
            return MusicIconsGenerator()

        return None


class ImageGenerator:
    def __init__(self):
        self.fontFilePath = to_source_path(IMAGES_FOLDER) / "Courier.ttf"

        self.assets_type = OldDataType.NONE
        self.dataSpriteKey = None
        self.dataTextureKey = None
        self.dataTextureName = None
        self.dataObjectKey = None
        self.scaleFactor = 1
        self.folderToSave = None
        self.frameKey = None
        self.langFileName: LangType = LangType.NONE
        self.defaultFrameName = None
        self.dataAnimFramesKey = None

        self.imagePrefix = None
        self.iconPrefix = "Icon"

        self.animLeadingZeros = None

        self.available_gen = [GenType.SCALE, GenType.FRAME]

    def textures_set(self, data):
        pass

    def unit_generator(self, data):
        pass

    @staticmethod
    def get_simple_uint(obj):
        return obj

    @staticmethod
    def get_table_unit(obj, index):
        return obj[index]

    @staticmethod
    def change_name(name: str):
        return re.sub(r'[<>:/|\\?*\"]', '', name.strip())

    @staticmethod
    def is_anim(settings):
        return (settings.get(str(GenType.ANIM)) or
                settings.get(str(GenType.SPECIAL_ANIM)) or
                settings.get(str(GenType.DEATH_ANIM)))

    @staticmethod
    def get_frame(frame_name, meta, im):
        try:
            frame_name = frame_name.replace(".png", "")
            meta_data = meta.get(frame_name)
        except (ValueError, AttributeError):
            meta_data = None

        if meta_data is None:
            return None

        rect = meta_data["rect"]
        sx, sy = im.size

        return im.crop(
            (rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y'])), meta_data

    def get_name_clear_path(self, obj, name, lang_data, add_data) -> (str, str | None, str):
        clear_name = None
        add_path = ""

        if obj.get(IS_K_ID):
            name = add_data.get(K_ID)
            add_path = "/ID"
        elif self.dataObjectKey and lang_data and (tmp_name := lang_data.get(self.dataObjectKey)):
            name = clear_name = tmp_name

        if obj.get(ENUMERATE, 0) != 0:
            name += f"-{obj.get(ENUMERATE) + 1}"

        return name, clear_name, add_path

    def save_png(self, meta: dict[str, SpriteData], im: Image, file_name, name, save_folder, prefix_name=None,
                 scale_factor=1,
                 is_save=True, file_name_clean=None, leading_zeros=0, add_data: dict = None) -> Image:

        file_name_clean = file_name_clean or file_name

        leading_zeros = self.animLeadingZeros and abs(self.animLeadingZeros) or leading_zeros

        def filter_func(x):
            x = str(x).lower()
            file_name_lower = file_name_clean.lower()
            return x.startswith(file_name_lower) and re.match(
                fr"^{file_name_lower}{r"\d" * leading_zeros}$", x)

        frames_list = sorted(filter(filter_func, meta.keys()))
        file_name = frames_list[0] if frames_list else file_name

        file_names = [file_name]
        if add_data and add_data.get("prep"):
            file_names.append(add_data["prep"][0])

        meta_data = None
        error = None
        while file_names:
            file_name = file_names.pop(0)
            try:
                if meta.get(f"{file_name}1"):
                    print(file_name + "1", meta.get(f"{file_name}1"))

                if self.assets_type in [OldDataType.PROPS] and meta.get(f"{file_name}1"):
                    file_name = f"{file_name}1"
                    meta_data = meta.get(file_name)
                else:
                    meta_data = meta.get(file_name) or meta.get(int(file_name)) or meta.get(str(int(file_name)))
            except ValueError as e:
                error = e
                meta_data = None

            if meta_data:
                break

        if meta_data is None:
            print(f"! Image: skipped {name=}, {file_name=}, {error=}",
                  file=sys.stderr)
            return

        name = self.change_name(name)

        rect = meta_data["rect"]

        sx, sy = im.size

        im_crop: Image = im.crop(
            (rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

        im_crop_r = im_crop.resize((im_crop.size[0] * scale_factor, im_crop.size[1] * scale_factor),
                                   Resampling.NEAREST)

        p_dir = IMAGES_FOLDER

        sf_text = f'{p_dir}/Generated/{save_folder}'

        os.makedirs(sf_text, exist_ok=True)

        prefix_name = prefix_name or self.imagePrefix or "Sprite-"
        if is_save:
            im_crop_r.save(f"{sf_text}/{prefix_name}{name}.png")

        return im_crop, meta_data

    def save_png_icon(self, im_frame_data, im_obj_data, name, save_folder, scale_factor=1,
                      add_data: dict = None) -> None:
        p_dir = IMAGES_FOLDER

        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        os.makedirs(sf_text, exist_ok=True)

        if im_obj_data is None:
            return

        im_data = [im_frame_data, im_obj_data]
        im_list = []
        for im, meta_data in im_data:
            rect = meta_data["rect"]
            pivot = meta_data["pivot"]
            pivot = {
                "x": round(pivot["x"] * rect["width"]),
                "y": round(pivot["y"] * rect["height"])
            }
            pivot.update({
                "-x": rect["width"] - pivot["x"],
                "-y": rect["height"] - pivot["y"],
            })

            im_list.append((im, pivot, rect))

        max_pivot = {k: max(d[1][k] for d in im_list) for k in im_list[0][1].keys()}

        comp_list = []
        for image, pivot, rect in im_list:
            new_size = (
                pivot["x"] - max_pivot["x"],
                pivot["-y"] - max_pivot["-y"],
                rect["width"] + max_pivot["-x"] - pivot["-x"],
                rect["height"] + max_pivot["y"] - pivot["y"]
            )
            comp_list.append(image.crop(new_size))

        im_frame, im_obj = comp_list
        im_frame.alpha_composite(im_obj)

        im_frame_r = im_frame.resize((im_frame.size[0] * scale_factor, im_frame.size[1] * scale_factor),
                                     Resampling.NEAREST)

        name = self.change_name(name)
        im_frame_r.save(f"{sf_text}/{self.iconPrefix}-{name}.png")

    def save_anim(self, meta: dict[str, SpriteData], file_name, name, save_folder, prefix_name="Animated-",
                  postfix_name="", save_append="", frame_rate=DEFAULT_ANIMATION_FRAME_RATE, scale_factor=1,
                  base_duration=1000, add_data: dict = None) -> None:

        duration = base_duration // frame_rate

        sprite_data = meta.get(normalize_str(file_name))

        if sprite_data is None or sprite_data.animation is None:
            # print(f"! Anim: skipped {name=}, {sprite_data=} not found", file=sys.stderr)
            return

        sprites = get_anim_sprites_ready(sprite_data.animation)
        sprites = resize_list_images(sprites, scale_factor)

        sf_text = IMAGES_FOLDER / f'Generated/{save_folder}/anim{save_append}'

        name = self.change_name(name)

        for ext, folder, func in itertools.compress(tr_save.SAVE_DATA, add_data["selected_anim_types"]):
            path = sf_text.joinpath(folder)
            path.mkdir(exist_ok=True, parents=True)
            func(sprites, duration, path.joinpath(f"{prefix_name}{name}{postfix_name}{ext}"))


class SimpleGenerator(ImageGenerator):
    def unit_generator(self, data: dict):
        return ((k, self.get_simple_uint(v)) for k, v in data.items())

    def textures_set(self, data: dict) -> set[str]:
        return set(self.get_simple_uint(v).get(self.dataTextureKey) for v in data.values())

    @staticmethod
    def len_data(data: dict):
        return len(data)

    def get_sprite_name(self, obj):
        return obj.get(self.dataSpriteKey)

    def get_frame_name(self, obj):
        return obj.get(self.frameKey, self.defaultFrameName)

    def get_prepared_frame(self, frame_name, add="") -> (str, int, str):
        if self.animLeadingZeros and self.animLeadingZeros < 0:
            return frame_name, 0, 0, frame_name

        number = re.search(r"(\d+)$", frame_name)
        fn = frame_name

        if number:
            fn = fn[:number.start()]
            if add == "i":
                zeros = 2
                num = int("1")
            else:
                zeros = len(number.group(1))
                num = int(number.group(1))

            return f"{fn}{add}{num:0{zeros}}", zeros, f"{fn}{add}"

        if add == "i":
            return f"{frame_name}_{add}01", 2, f"{fn}_{add}"

        return frame_name, 0, frame_name

    def make_image(self, k_id, obj: dict, lang_data: dict = None, add_data: dict = None, **settings):
        add_data = add_data or {}

        name = obj.get(self.dataObjectKey) or k_id
        texture_name = obj.get(self.dataTextureKey, self.dataTextureName)
        file_name = self.get_sprite_name(obj).replace(".png", "")
        frame_name = self.get_frame_name(obj)
        save_folder = f"{normalize_str(add_data.get("p_file"))}/{self.folderToSave or texture_name}"

        def func_meta(x):
            d = MetaDataHandler.get_meta_by_name_fullest(x)
            if d:
                return d.data_name, d.image
            else:
                return (None,) * 2

        add_data.update({
            "func_meta": func_meta,
            K_ID: k_id,
            "object": obj
        })

        pst = settings.get("add_postfix")
        if pst:
            save_folder += f"_{pst}"

        save_folder += "/" + (obj.get("contentGroup") if obj.get("contentGroup") else "BASE_GAME")

        meta_data = MetaDataHandler.get_meta_by_name_fullest(texture_name)
        meta_data.init_sprites()
        if self.is_anim(settings):
            meta_data.init_animations()

        meta = meta_data.data_name
        im = meta_data.image
        if not meta:
            print(f"! Skipped {name}: {texture_name} texture not found",
                  file=sys.stderr)
            return

        if osf := obj.get("save_folder"):
            save_folder += osf

        name, clear_name, add_save_path = self.get_name_clear_path(obj, name, lang_data, add_data)

        save_folder += add_save_path

        if not obj.get(IS_K_ID) and k_id in name:
            save_folder += "/No lang id"

        add_data.update({
            "clear_name": clear_name or name,
        })

        if pst:
            name += f"_{pst}"

        if osfp := obj.get("save_folder_postfix"):
            save_folder += osfp

        using_list = obj.get('for', GenType.main_list())
        scale_factor = settings[str(GenType.SCALE)]

        if GenType.SCALE in using_list:
            if self.assets_type in [OldDataType.ENEMY]:
                prep = self.get_prepared_frame(file_name)
                prep_i = self.get_prepared_frame(file_name, "i")

                im_obj = self.save_png(meta, im, prep_i[0], name, save_folder, scale_factor=scale_factor,
                                       leading_zeros=prep_i[1], file_name_clean=prep_i[2], add_data={"prep": prep})
            else:
                im_obj = self.save_png(meta, im, file_name, name, save_folder, scale_factor=scale_factor,
                                       is_save=GenType.SCALE not in obj.get("not_save", []))

        if settings.get(str(GenType.FRAME)) and GenType.FRAME in using_list:
            im_frame = self.get_frame(frame_name, *func_meta("UI"))
            if im_frame or self.assets_type in [OldDataType.STAGE, OldDataType.STAGE_SET]:
                self.save_png_icon(im_frame, im_obj, name, save_folder, scale_factor=scale_factor, add_data=add_data)

        if settings.get(str(GenType.ANIM)) and GenType.ANIM in using_list:
            if self.assets_type in [OldDataType.ENEMY]:
                prep = self.get_prepared_frame(file_name, "i")
                self.save_anim(meta, prep[0], name, save_folder, scale_factor=scale_factor, add_data=add_data)
            else:
                prep = self.get_prepared_frame(file_name)
                self.save_anim(meta, prep[0], name, save_folder,
                               frame_rate=obj.get("walkFrameRate", DEFAULT_ANIMATION_FRAME_RATE),
                               scale_factor=scale_factor, add_data=add_data)

                prep = self.get_prepared_frame(file_name + "1")
                self.save_anim(meta, prep[0], name + "__1", save_folder,
                               frame_rate=obj.get("walkFrameRate", DEFAULT_ANIMATION_FRAME_RATE),
                               scale_factor=scale_factor, add_data=add_data)

        if settings.get(str(GenType.DEATH_ANIM)) and GenType.DEATH_ANIM in using_list:
            prep = self.get_prepared_frame(file_name)
            self.save_anim(meta, prep[0], name, save_folder, prefix_name="Animated-Death-", save_append="_death",
                           frame_rate=20, scale_factor=scale_factor, add_data=add_data)

        if settings.get(str(GenType.SPECIAL_ANIM)) and GenType.SPECIAL_ANIM in using_list:
            prep = self.get_prepared_frame(file_name)
            self.save_anim(meta, prep[0], name, save_folder, prefix_name="Animated-",
                           postfix_name=obj.get("postfix_name"), save_append="_special",
                           frame_rate=obj.get("frameRate", DEFAULT_ANIMATION_FRAME_RATE), scale_factor=scale_factor,
                           add_data=add_data)


class ItemImageGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.ITEM
        self.frameKey = "collectionFrame"
        self.scaleFactor = 1
        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "texture"
        self.folderToSave = "items"
        self.dataObjectKey = "name"
        self.langFileName = LangType.ITEM
        self.defaultFrameName = "frameC.png"

        self.available_gen.extend([GenType.ANIM])

    def get_frame_name(self, obj):
        return obj.get(self.frameKey, self.defaultFrameName if not obj.get("isRelic") else "frameF.png")


class ArcanaImageGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.ARCANA
        self.frameKey = None
        self.scaleFactor = 1
        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "texture"
        self.dataObjectKey = "name"
        self.folderToSave = "arcana"
        self.langFileName = LangType.ARCANA

        self.defaultFrameName = "frameG.png"

    def get_frame_name(self, obj):
        return obj.get(self.frameKey, self.defaultFrameName if not obj.get("arcanaType") >= 22 else "frameH.png")

    @staticmethod
    def change_name(name):
        return name[name.find("-") + 1:].strip()

    def len_data(self, data: dict):
        return 2 * super().len_data(data)

    def unit_generator(self, data: dict):
        return self.arcana_generator(data)

    @staticmethod
    def arcana_generator(data: dict):
        for k, v in data.items():
            vv = v.copy()
            add_folder = "/dark" if vv.get("arcanaType") >= 22 else ""

            vv.update({
                "for": [GenType.SCALE],
                "save_folder": f"{add_folder}/picture"
            })
            yield k, vv

            vv = v.copy()
            vv.update({
                "texture": "items",
                "save_folder": add_folder
            })
            yield k, vv


class PropsImageGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.PROPS
        self.scaleFactor = 1
        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "textureName"
        self.dataObjectKey = "frameName"

        self.folderToSave = "props"

        self.animLeadingZeros = -1

        self.available_gen.remove(GenType.FRAME)
        self.available_gen.append(GenType.ANIM)


class AdvMerchantsGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.ADV_MERCHANTS
        self.scaleFactor = 1
        self.dataSpriteKey = "staticSprite"
        self.dataTextureKey = "staticSpriteTexture"

        self.dataObjectKey = "charName"
        self.langFileName = LangType.CHARACTER

        self.folderToSave = "adventure merchants"

        self.animLeadingZeros = 2

        self.available_gen.remove(GenType.FRAME)
        self.available_gen.append(GenType.ANIM)


class AlbumCoversGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.ALBUM
        self.scaleFactor = 1
        self.dataSpriteKey = "icon"
        self.dataTextureKey = "icon"

        self.dataObjectKey = "title"

        self.folderToSave = "album covers"
        self.imagePrefix = "Album-"

        self.available_gen.remove(GenType.FRAME)


class MusicIconsGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.MUSIC
        self.scaleFactor = 1
        self.dataSpriteKey = "icon"
        self.dataTextureName = "UI"

        self.dataObjectKey = "title"

        self.folderToSave = "music icons"
        self.imagePrefix = "Music-"

        self.available_gen.remove(GenType.FRAME)

    def get_name_clear_path(self, obj, name, lang_data, add_data) -> (str, str, str):
        add_save_path = ""
        postfix_list = [
            ("castlevania", "source"),
            ("vampire survivors", "author")
        ]
        source_l = obj.get("source").lower() or obj.get("title").lower()
        check = [postfix[0] in source_l for postfix in postfix_list]
        if (any(check)
                and (true_index := check.index(True)) is not None
                and (to_add := obj.get(postfix_list[true_index][1]))
        ):
            name += f"-{to_add}"
            add_save_path += f"/{to_add}"
        return name, None, add_save_path

    def textures_set(self, data: dict) -> set:
        return {self.dataTextureName}


class HitVFXGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.HIT_VFX
        self.scaleFactor = 1
        self.dataSpriteKey = "impactFrameName"
        self.dataTextureName = "vfx"

        self.folderToSave = "hit vfx"

        self.available_gen.remove(GenType.FRAME)
        self.available_gen.append(GenType.ANIM)

    def textures_set(self, data: dict) -> set:
        return {self.dataTextureName}


class TableGenerator(SimpleGenerator):
    def unit_generator(self, data: dict):
        return ((k, self.get_table_unit(v, 0)) for k, v in data.items())

    def textures_set(self, data: dict) -> set:
        return set(self.get_table_unit(v, 0).get(self.dataTextureKey) for v in data.values())


class WeaponImageGenerator(TableGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.WEAPON
        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "texture"
        self.dataObjectKey = "name"
        self.scaleFactor = 1
        self.frameKey = "collectionFrame"
        self.folderToSave = "weapons"
        self.defaultFrameName = "frameB.png"
        self.langFileName = LangType.WEAPON


class CharacterImageGenerator(TableGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.CHARACTER
        self.frameKey = "collectionFrame"
        self.scaleFactor = 1
        self.dataSpriteKey = "spriteName"
        self.dataTextureKey = "textureName"
        self.dataObjectKey = "charName"
        self.folderToSave = "characters"
        self.langFileName = LangType.CHARACTER
        self.dataAnimFramesKey = "walkingFrames"
        self.iconPrefix = "Select"

        self.available_gen.extend([GenType.ANIM, GenType.SPECIAL_ANIM])

    def get_name_clear_path(self, obj, name, lang_data, add_data) -> (str, str, str):
        add_save_path = ""
        clear_name = None
        if self.dataObjectKey and lang_data:
            name = clear_name = lang_data.get(self.dataObjectKey)

            is_full_name = obj.get("is_full_name")
            add_save_path += (is_full_name and "/full_name") or "/short_name"

            if is_full_name:
                surname = lang_data.get('surname') or " "
                space2 = surname[0] not in [":", ","] and " " or ""
                name = f"{lang_data.get('prefix') or ""} {clear_name}{space2}{surname}".strip()
            elif prefix := obj.get('prefix'):
                # find with same name for char
                flt = lambda x: not x[0].get("prefix") and x[0].get(self.dataObjectKey) == clear_name

                main_object = list(filter(flt, add_data["character"].values()))
                if main_object or "megalo" in prefix.lower():
                    name = f"{prefix} {clear_name}"

            if obj.get("is_weapon_skin"):
                add_save_path += "/skins_weapon"

                lang_weapon = add_data.get("lang_weapon")

                start_weapon_id = obj.get("startingWeapon")
                if obj.get("defaultStartingWeapon") == start_weapon_id:
                    add_save_path += "/default_weapon"

                if start_weapon_id not in ["VOID", 0, "0", None]:
                    weapon_name = lang_weapon.get(start_weapon_id, {}).get("name")
                    name += f" ({weapon_name})"

            else:
                add_save_folder = False

                skin_type = obj.get("skinType", "DEFAULT")
                lang_skins = add_data.get("lang_skins")
                if (skin_obj := lang_skins.get(skin_type)) and (obj.get('name', 'default').lower() != "default"):
                    suffix = skin_obj.get("suffix") or " "
                    space_suf = suffix[0] not in [":", ","] and " " or ""
                    name = f"{skin_obj.get("prefix") or ""} {name}{space_suf}{suffix}"
                    add_save_folder = True
                elif obj.get('name', 'default').lower() != "default":
                    name += f" {obj.get('name')}"
                    add_save_folder = True
                elif obj.get("id", 0) != 0:
                    name += f"-{obj.get("id")}"
                    add_save_folder = True

                if add_save_folder:
                    add_save_path += "/skins"

                if obj.get("charSelFrame") and not obj.get("is_select"):
                    add_save_path += "/without_select_img"

        else:
            add_save_path += "/other_names"

        if obj.get("alwaysHidden"):
            add_save_path += "/hidden_skins"

        return name, clear_name, add_save_path

    @staticmethod
    def len_data(data: dict):
        return (sum(len(v[0].get("skins")) if v[0].get("skins") else 1 for v in data.values()) +
                sum(len(v[0].get("spriteAnims")) if v[0].get("spriteAnims") else 0 for v in data.values()) +
                sum(1 if v[0].get("charSelFrame") else 0 for v in data.values()))

    def unit_generator(self, data: dict):
        return itertools.chain(self.skins_generator(data), self.sprite_anims_generator(data))

    def skins_generator(self, data: dict):
        for k, vv in data.items():
            v_unit = self.get_table_unit(vv, 0)
            for is_full_name, is_weapon_skin in itertools.product([False, True], repeat=2):
                v = v_unit.copy()
                v.update({
                    "is_full_name": is_full_name,
                    "is_weapon_skin": is_weapon_skin,
                    "defaultStartingWeapon": v.get("startingWeapon"),
                })
                skins = v.get("skins") or [{}]
                for skin in skins:
                    char = v.copy()
                    char.update(skin)
                    yield k, char

                    if skin.get("charSelFrame") or v.get("charSelTexture"):
                        char.update({
                            "textureName": skin.get("charSelTexture") or v.get("charSelTexture"),
                            "spriteName": skin.get("charSelFrame") or v.get("charSelFrame"),
                            "for": [GenType.SCALE, GenType.FRAME],
                            "save_folder_postfix": "/select",
                            "is_select": True
                        })
                        yield k, char

    def sprite_anims_generator(self, data: dict):
        for k, vv in data.items():
            v = self.get_table_unit(vv, 0)
            if skins := v.get("skins", False):
                for is_full_name, is_weapon_skin in itertools.product([False, True], repeat=2):
                    for skin in skins:
                        if anims := skin.get("spriteAnims", False):
                            for anim_type, anim_data in anims.items():
                                postfix_words = re.findall('.[^A-Z]*', anim_type)
                                postfix_words[0] = postfix_words[0].title()
                                char = v.copy()
                                char.update(skin)
                                char.update(anim_data)
                                char.update({
                                    "animType": anim_type,
                                    "postfix_name": f"-{"-".join(postfix_words)}",
                                    "for": [GenType.SPECIAL_ANIM],

                                    "defaultStartingWeapon": v.get("startingWeapon"),

                                    "is_full_name": is_full_name,
                                    "is_weapon_skin": is_weapon_skin,
                                })
                                yield k, char

    @staticmethod
    def get_frame(_frame_name, _meta, _im):
        p_dir = to_source_path(IMAGES_FOLDER)
        p_file = f"{p_dir}/CharacterSelectFrame.png"

        im = image_open(p_file)
        meta_data = {
            "rect": {
                "x": 0, "y": 0, "width": im.width, "height": im.height
            },
            "pivot": {"x": 6 / im.width, "y": 0}
        }

        return im, meta_data

    def save_png_icon(self, im_frame_data, im_obj_data, name, save_folder, scale_factor=1,
                      add_data: dict = None) -> None:
        obj_im, obj_data = im_obj_data
        frame_im, frame_data = im_frame_data

        func_meta = add_data["func_meta"]
        weapon_data = add_data["weapon"]
        char_data = add_data["object"]

        w_id = char_data.get("startingWeapon")

        if w_id and (weapon_data := weapon_data.get(w_id)):
            w_texture = weapon_data[0].get("texture")
            meta, im = func_meta(w_texture)
            file_name = weapon_data[0].get("frameName").replace(".png", "")

            try:
                if meta.get(f"{file_name}1"):
                    print(file_name + "1", meta.get(f"{file_name}1"))

                if self.assets_type in [OldDataType.PROPS] and meta.get(f"{file_name}1"):
                    file_name = f"{file_name}1"
                    meta_data = meta.get(file_name)
                else:
                    meta_data = meta.get(file_name) or meta.get(int(file_name))
            except ValueError as e:
                error = e
                meta_data = None

            if meta_data is None:
                print(f"! Skipped {name}, {file_name}",
                      file=sys.stderr)
                return

            rect = meta_data["rect"]

            sx, sy = im.size
            w_sprite: Image = im.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))
            w_sprite = w_sprite.resize((w_sprite.size[0] * 4, w_sprite.size[1] * 4), Resampling.NEAREST)

            w_sprite_black = make_image_black( w_sprite.copy() )

            weapon_offset = {
                "x": frame_im.width - w_sprite.width - 10, "y": frame_im.height - w_sprite.height - 12,
            }

            frame_im.alpha_composite(w_sprite_black, (weapon_offset["x"], weapon_offset["y"]))

            frame_im.alpha_composite(w_sprite, (weapon_offset["x"] - 8, weapon_offset["y"] - 4))

        obj_im = obj_im.resize((int(obj_im.size[0] * 3.8), int(obj_im.size[1] * 3.8)), Resampling.NEAREST)

        frame_im.alpha_composite(obj_im, (12, frame_im.height - obj_im.height - 11))

        p_dir = IMAGES_FOLDER
        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        os.makedirs(sf_text, exist_ok=True)
        os.makedirs(sf_text + '/text', exist_ok=True)

        save_name = self.change_name(name)
        text = add_data["clear_name"].strip()
        font = ImageFont.truetype(self.fontFilePath, 30)
        w = font.getbbox(text)[2] + scale_factor
        h = font.getbbox(text + "|")[3]

        if w > frame_im.size[0] - 4 * scale_factor:
            if " " in text:
                text = text[::-1].replace(" ", "\n", 1)[::-1]

            font = ImageFont.truetype(self.fontFilePath, 28)
            w = font.getbbox(text)[2] + scale_factor
            h = (font.getbbox("|" + text + "|")[3] + scale_factor) * 2

        canvas = image_new('RGBA', (int(w), int(h)))

        draw = ImageDraw.Draw(canvas)
        draw.text((3, -5), text, "#ffffff", font, stroke_width=1)

        canvas.save(f"{sf_text}/text/{self.iconPrefix}-{save_name}.png")

        frame_im.alpha_composite(canvas, (14, 20))

        frame_im.save(f"{sf_text}/{self.iconPrefix}-{save_name}.png")


class PowerUpImageGenerator(TableGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.POWERUP
        self.scaleFactor = 1
        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "texture"
        self.dataObjectKey = "name"
        self.langFileName = LangType.POWER_UP

        self.defaultFrameName = "frameD.png"

        self.folderToSave = "power up"
        self.iconPrefix = "PowerUp"

    def get_frame_name(self, obj):
        return "frameE.png" if obj.get("specialBG") else super().get_frame_name(obj)


class EnemyImageGenerator(TableGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.ENEMY
        self.frameKey = None
        self.scaleFactor = 1
        self.dataSpriteKey = "frameNames"
        self.dataTextureKey = "textureName"
        self.dataObjectKey = "bName"
        self.langFileName = LangType.ENEMIES
        self.dataAnimFramesKey = "idleFrameCount"

        self.folderToSave = "enemy"

        self.available_gen.remove(GenType.FRAME)
        self.available_gen.extend([GenType.ANIM, GenType.DEATH_ANIM])

    @staticmethod
    def len_data(data: dict):
        return sum(len(v[0].get("frameNames")) for v in data.values())

    def unit_generator(self, data: dict):
        return self.skins_generator(data)

    def skins_generator(self, data: dict):
        variants_to_skip: set[str] = set()
        for k, vv in data.items():
            v = self.get_table_unit(vv, 0)
            if (b_vars := v.get("bVariants")) and (v.get("bInclude")):
                fn = vv[0][FRAME_NAMES]
                for b_var in b_vars:
                    variants_to_skip.add(b_var)
                    if b_var in data:
                        to_add = data[b_var][0].get(FRAME_NAMES)
                        fn.extend(to_add)
                vv[0][FRAME_NAMES] = list(dict.fromkeys(fn))

        for k, vv in data.items():
            if k in variants_to_skip:
                continue

            v = vv[0]

            for is_k_id in [False, True]:
                v[IS_K_ID] = is_k_id
                add_i = 0
                if alias := v.get("alias"):
                    v1 = v.copy()
                    v1.update(alias)
                    for _, frame in enumerate(v1.get(FRAME_NAMES)):
                        enemy = v1.copy()
                        enemy[FRAME_NAMES] = frame
                        enemy[ENUMERATE] = add_i

                        add_i += 1

                        yield k, enemy

                    add_i = len(v1.get(FRAME_NAMES))

                for _, frame in enumerate(v.get(FRAME_NAMES)):
                    enemy = v.copy()
                    enemy[FRAME_NAMES] = frame
                    enemy[ENUMERATE] = add_i

                    add_i += 1

                    yield k, enemy


class StageImageGenerator(TableGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.STAGE
        self.frameKey = None
        self.scaleFactor = 4
        self.defaultScaleFactor = 4
        self.dataSpriteKey = "uiFrame"
        self.dataTextureKey = "uiTexture"
        self.dataObjectKey = "stageName"
        self.langFileName = LangType.STAGE

        self.folderToSave = "stage"

    def save_png_icon(self, _, im_obj, name, save_folder, scale_factor=1,
                      add_data: dict = None):
        im_obj = im_obj[0]
        if im_obj is None:
            return

        p_dir = IMAGES_FOLDER

        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        os.makedirs(sf_text, exist_ok=True)
        os.makedirs(sf_text + "/text", exist_ok=True)

        im_frame_r = im_obj.resize((im_obj.size[0] * scale_factor, im_obj.size[1] * scale_factor),
                                   Resampling.NEAREST)

        save_name = self.change_name(name)
        text = add_data["clear_name"].strip()
        base_scale = 50
        while True:
            font = ImageFont.truetype(self.fontFilePath,
                                      base_scale * scale_factor / self.defaultScaleFactor)
            w = font.getbbox(text)[2] + scale_factor
            h = font.getbbox(text + "|")[3]
            if w / scale_factor + 10 > im_obj.size[0]:
                base_scale -= 2
            else:
                break

        canvas = image_new('RGBA', (int(w), int(h)))

        draw = ImageDraw.Draw(canvas)
        draw.text((3, -5), text, "#eef92b", font, stroke_width=1)
        canvas.save(f"{sf_text}/text/Stage-{save_name}.png")

        # canvas.show()
        # im_crop.show()
        crx, cry = im_frame_r.size
        crx //= 2
        cry = int(cry / 5)
        frx, fry = canvas.size
        frx //= 2
        fry //= 2
        im_frame_r.alpha_composite(canvas, (crx - frx, cry - fry))
        im_frame_r.save(f"{sf_text}/Stage-{save_name}.png")


class StageSetImageGenerator(StageImageGenerator):
    # Deprecated VS - v1.14
    def __init__(self):
        super().__init__()
        self.assets_type = OldDataType.STAGE_SET

        self.folderToSave = "stageset"

    @staticmethod
    def len_data(data: dict):
        return sum(len(d) for d in data.values())

    def unit_generator(self, data: dict):
        def get_adv_unit(main_obj: dict, add_obj: dict):
            main_obj.update(add_obj)
            return main_obj

        return ((k, get_adv_unit(self.get_table_unit(v, 0), {"save_folder": "/" + adv_id.strip()})) for adv_id, set_v in
                data.items() for k, v in set_v.items())

    def textures_set(self, data: dict):
        return set(
            self.get_table_unit(v, 0).get(self.dataTextureKey) for set_v in data.values() for v in set_v.values())


if __name__ == "__main__":
    pass
