import itertools
import re
from enum import Enum
import os
import sys
from PIL import Image, ImageFont, ImageDraw
import PIL.Image
import Images.transparent_save as tr_save


class Type(Enum):
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


class GenType(Enum):
    SCALE = 0
    FRAME = 1
    ANIM = 2
    DEATH_ANIM = 3

    ATTACK_ANIM = 4

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
        elif "stageset" in data_file:
            return StageSetImageGenerator()
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

        return None


class ImageGenerator:
    def __init__(self):
        self.assets_type = Type.NONE
        self.dataSpriteKey = None
        self.dataTextureKey = None
        self.dataTextureName = None
        self.dataObjectKey = None
        self.scaleFactor = 1
        self.folderToSave = None
        self.frameKey = None
        self.langFileName = None
        self.defaultFrameName = None
        self.dataAnimFramesKey = None

        self.iconGroup = "Icon"

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
    def change_name(name):
        return re.sub(r'[<>:/|\\?*]', '', name.strip())

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

    def save_png(self, meta, im, file_name, name, save_folder, prefix_name="Sprite-", scale_factor=1,
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
                    file_name = f"{file_name}1"
                    meta_data = meta.get(file_name)
                else:
                    meta_data = meta.get(file_name) or meta.get(int(file_name))
            except ValueError as e:
                error = e
                meta_data = None

            if meta_data:
                break

        if meta_data is None:
            print(f"! Image: skipped {name=}, {file_name=}, {error=}",
                  file=sys.stderr)
            return

        rect = meta_data["rect"]

        sx, sy = im.size

        im_crop = im.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

        im_crop_r = im_crop.resize((im_crop.size[0] * scale_factor, im_crop.size[1] * scale_factor),
                                   PIL.Image.NEAREST)

        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}'

        os.makedirs(sf_text, exist_ok=True)

        name = self.change_name(name)
        if is_save:
            im_crop_r.save(f"{sf_text}/{prefix_name}{name}.png")

        return im_crop, meta_data

    def save_png_icon(self, im_frame_data, im_obj_data, name, save_folder, scale_factor=1,
                      add_data: dict = None) -> None:
        p_dir = os.path.split(__file__)[0]

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
                                     PIL.Image.NEAREST)

        name = self.change_name(name)
        im_frame_r.save(f"{sf_text}/{self.iconGroup}-{name}.png")

    def save_gif(self, meta, im: Image, file_name, name, save_folder, prefix_name="Animated-", postfix_name="",
                 save_append="", frame_rate=6, scale_factor=1, base_duration=1000, file_name_clean=None,
                 leading_zeros: None | int = None, limit_frames_count=1000) -> None:
        sx, sy = im.size

        file_name_clean = file_name_clean or file_name

        leading_zeros = self.animLeadingZeros and abs(self.animLeadingZeros) or leading_zeros

        def filter_func(x):
            x = str(x).lower()
            file_name_lower = file_name_clean.lower()
            return x.startswith(file_name_lower) and re.match(
                fr"^{file_name_lower}{r"\d" * leading_zeros}$", x)

        frames_list = sorted(filter(filter_func, meta.keys()))
        frames_count = len(frames_list)

        # print(frames_list, leading_zeros, fr"^{file_name_clean}{r"\d" * leading_zeros}$")

        im_list = []
        for i, frame_name in enumerate(frames_list):
            if limit_frames_count and i >= limit_frames_count:
                break

            try:
                meta_data = meta.get(frame_name) or meta.get(int(frame_name))
            except ValueError:
                meta_data = None

            if meta_data is None:
                print(f"! Anim: skipped {name=}, {frame_name=} not found, total {frames_count=}",
                      file=sys.stderr)
                continue

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
            im_crop = im.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

            im_list.append((im_crop, pivot, rect))

        if not im_list:
            return

        max_pivot = {k: max(d[1][k] for d in im_list) for k in im_list[0][1].keys()}
        # print(file_name_clean, max_pivot)
        # print(*im_list, sep='\n')

        gif_list = []
        for image, pivot, rect in im_list:
            new_size = (
                pivot["x"] - max_pivot["x"],
                pivot["-y"] - max_pivot["-y"],
                rect["width"] + max_pivot["-x"] - pivot["-x"],
                rect["height"] + max_pivot["y"] - pivot["y"]
            )
            im_t = image.crop(new_size)
            # print(new_size, image.size, im_t.size)

            im_r = im_t.resize((im_t.size[0] * scale_factor, im_t.size[1] * scale_factor), PIL.Image.NEAREST)
            gif_list.append(im_r)

        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}/anim{save_append}'

        os.makedirs(sf_text+"/gif", exist_ok=True)
        os.makedirs(sf_text+"/webp", exist_ok=True)
        os.makedirs(sf_text+"/apng", exist_ok=True)

        total_duration = base_duration // frame_rate

        name = self.change_name(name)
        tr_save.save_transparent_gif(gif_list, total_duration, f"{sf_text}/gif/{prefix_name}{name}{postfix_name}.gif")
        tr_save.save_transparent_webp(gif_list, total_duration, f"{sf_text}/webp/{prefix_name}{name}{postfix_name}.webp")
        tr_save.save_transparent_apng(gif_list, total_duration, f"{sf_text}/apng/{prefix_name}{name}{postfix_name}.png")


class SimpleGenerator(ImageGenerator):
    def unit_generator(self, data: dict):
        return ((k, self.get_simple_uint(v)) for k, v in data.items())

    def textures_set(self, data: dict):
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
            zeros = len(number.group(1))
            if add == "i":
                zeros = 2

            return f"{fn}{add}{number.group(1)}", zeros, f"{fn}{add}"

        if add == "i":
            return f"{frame_name}_{add}01", 2, f"{fn}_{add}"

        return frame_name, 0, frame_name

    def make_image(self, func_meta, k_id, obj: dict, lang_data: dict = None, add_data: dict = None, **settings):
        name = obj.get(self.dataObjectKey) or k_id
        texture_name = obj.get(self.dataTextureKey, self.dataTextureName)
        file_name = self.get_sprite_name(obj).replace(".png", "")
        frame_name = self.get_frame_name(obj)
        save_folder = self.folderToSave or texture_name

        add_data = add_data or {}
        add_data.update({
            "func_meta": func_meta,
            "k_id": k_id,
            "object": obj
        })

        pst = settings.get("add_postfix")
        if pst:
            save_folder += f"_{pst}"

        save_folder += "/" + (obj.get("contentGroup") if obj.get("contentGroup") else "BASE_GAME")

        meta, im = func_meta("", texture_name)
        if not meta:
            print(f"! Skipped {name}: {texture_name} texture not found",
                  file=sys.stderr)
            return

        if osf := obj.get("save_folder"):
            save_folder += osf

        if self.dataObjectKey and lang_data:
            name = lang_data.get(self.dataObjectKey)

        add_data.update({
            "clear_name": name,
        })

        if pst:
            name += f"_{pst}"

        # find with same name for char
        if self.assets_type in [Type.CHARACTER] and (prefix := obj.get('prefix')):
            flt = lambda x: not x[0].get("prefix") and x[0].get(self.dataObjectKey) == name

            main_object = list(filter(flt, add_data["character"].values()))
            if main_object or "megalo" in prefix.lower():
                name = f"{prefix} {name}"

        if obj.get("skinType", "default").lower() != "default":
            name += f"-{obj.get("name", "Default")}"
            save_folder += "/skins"
        elif obj.get("id", 0) != 0:
            name += f"-{obj.get("id")}"

        if obj.get("alwaysHidden") and self.assets_type in [Type.CHARACTER]:
            name += f"-{k_id}"
            save_folder += "/hidden_skins"

        if osfp := obj.get("save_folder_postfix"):
            save_folder += osfp

        using_list = obj.get('for', GenType.main_list())
        scale_factor = settings[str(GenType.SCALE)]

        if GenType.SCALE in using_list:
            if self.assets_type in [Type.ENEMY]:
                prep = self.get_prepared_frame(file_name)
                prep_i = self.get_prepared_frame(file_name, "i")

                im_obj = self.save_png(meta, im, prep_i[0], name, save_folder, scale_factor=scale_factor,
                                       leading_zeros=prep_i[1], file_name_clean=prep_i[2], add_data={"prep": prep})
            else:
                im_obj = self.save_png(meta, im, file_name, name, save_folder, scale_factor=scale_factor,
                                       is_save=GenType.SCALE not in obj.get("not_save", []))

        if settings.get(str(GenType.FRAME)) and GenType.FRAME in using_list:
            im_frame = self.get_frame(frame_name, *func_meta("", "UI"))
            if im_frame or self.assets_type in [Type.STAGE, Type.STAGE_SET]:
                self.save_png_icon(im_frame, im_obj, name, save_folder, scale_factor=scale_factor, add_data=add_data)

        if settings.get(str(GenType.ANIM)) and GenType.ANIM in using_list:
            if self.assets_type in [Type.ENEMY]:
                prep = self.get_prepared_frame(file_name, "i")
                self.save_gif(meta, im, prep[0], name, save_folder, scale_factor=scale_factor, file_name_clean=prep[2],
                              leading_zeros=2)
            else:
                prep = self.get_prepared_frame(file_name)
                self.save_gif(meta, im, prep[0], name, save_folder, frame_rate=obj.get("walkFrameRate", 6),
                              scale_factor=scale_factor, file_name_clean=prep[2], leading_zeros=prep[1],
                              limit_frames_count=obj.get(self.dataAnimFramesKey))

                prep = self.get_prepared_frame(file_name + "1")
                self.save_gif(meta, im, prep[0], name + "__1", save_folder, frame_rate=obj.get("walkFrameRate", 6),
                              scale_factor=scale_factor, file_name_clean=prep[2], leading_zeros=prep[1],
                              limit_frames_count=obj.get(self.dataAnimFramesKey))

        if settings.get(str(GenType.DEATH_ANIM)) and GenType.DEATH_ANIM in using_list:
            prep = self.get_prepared_frame(file_name)
            self.save_gif(meta, im, prep[0], name, save_folder, prefix_name="Animated-Death-", save_append="_death",
                          frame_rate=20, scale_factor=scale_factor, file_name_clean=prep[2], leading_zeros=prep[1])

        if settings.get(str(GenType.ATTACK_ANIM)) and GenType.ATTACK_ANIM in using_list:
            prep = self.get_prepared_frame(file_name)
            self.save_gif(meta, im, prep[0], name, save_folder, prefix_name="Animated-",
                          postfix_name=obj.get("postfix_name"), save_append="_special",
                          frame_rate=obj.get("frameRate", 6), scale_factor=scale_factor, file_name_clean=prep[2],
                          leading_zeros=2, limit_frames_count=obj.get("framesNumber"))


class ItemImageGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = Type.ITEM
        self.frameKey = "collectionFrame"
        self.scaleFactor = 8
        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "texture"
        self.folderToSave = "items"
        self.dataObjectKey = "name"
        self.langFileName = "itemLang.json"
        self.defaultFrameName = "frameC.png"

        self.available_gen.extend([GenType.ANIM])

    def get_frame_name(self, obj):
        return obj.get(self.frameKey, self.defaultFrameName if not obj.get("isRelic") else "frameF.png")


class ArcanaImageGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = Type.ARCANA
        self.frameKey = None
        self.scaleFactor = 4
        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "texture"
        self.dataObjectKey = "name"
        self.folderToSave = "arcana"
        self.langFileName = "arcanaLang.json"

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
        self.assets_type = Type.PROPS
        self.scaleFactor = 8
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
        self.assets_type = Type.ADV_MERCHANTS
        self.scaleFactor = 4
        self.dataSpriteKey = "staticSprite"
        self.dataTextureKey = "staticSpriteTexture"

        self.dataObjectKey = "charName"
        self.langFileName = "characterLang.json"

        self.folderToSave = "adventure merchants"

        self.animLeadingZeros = 2

        self.available_gen.remove(GenType.FRAME)
        self.available_gen.append(GenType.ANIM)


class HitVFXGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = Type.HIT_VFX
        self.scaleFactor = 4
        self.dataSpriteKey = "impactFrameName"
        # self.dataTextureKey = "staticSpriteTexture"
        self.dataTextureName = "vfx"

        # self.dataObjectKey = "charName"
        # self.langFileName = "characterLang.json"

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
        self.assets_type = Type.WEAPON
        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "texture"
        self.dataObjectKey = "name"
        self.scaleFactor = 8
        self.frameKey = "collectionFrame"
        self.folderToSave = "weapons"
        self.defaultFrameName = "frameB.png"
        self.langFileName = "weaponLang.json"


class CharacterImageGenerator(TableGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = Type.CHARACTER
        self.frameKey = "collectionFrame"
        self.scaleFactor = 4
        self.dataSpriteKey = "spriteName"
        self.dataTextureKey = "textureName"
        self.dataObjectKey = "charName"
        self.folderToSave = "characters"
        self.langFileName = "characterLang.json"
        self.dataAnimFramesKey = "walkingFrames"
        self.iconGroup = "Select"

        self.available_gen.extend([GenType.ANIM, GenType.ATTACK_ANIM])

    @staticmethod
    def len_data(data: dict):
        return (sum(len(v[0].get("skins")) if v[0].get("skins") else 1 for v in data.values()) +
                sum(len(v[0].get("spriteAnims")) if v[0].get("spriteAnims") else 0 for v in data.values()) +
                sum(1 if v[0].get("charSelFrame") else 0 for v in data.values()))

    def unit_generator(self, data: dict):
        return itertools.chain(self.skins_generator(data), self.sprite_anims_generator(data))

    def skins_generator(self, data: dict):

        for k, vv in data.items():
            v = self.get_table_unit(vv, 0)
            if skins := v.get("skins", False):
                for skin in skins:
                    char = v.copy()
                    char.update(skin)

                    yield k, char

                    if v.get("charSelFrame"):
                        char.update({
                            "textureName": v.get("charSelTexture"),
                            "spriteName": v.get("charSelFrame"),
                            "for": [GenType.SCALE, GenType.FRAME],
                            # "not_save": [GenType.SCALE],
                            "save_folder_postfix": "/select"
                        })
                        yield k, char
            else:
                yield k, v

                if v.get("charSelFrame"):
                    char = v.copy()
                    char.update({
                        "textureName": v.get("charSelTexture"),
                        "spriteName": v.get("charSelFrame"),
                        "for": [GenType.SCALE, GenType.FRAME],
                        # "not_save": [GenType.SCALE],
                        "save_folder_postfix": "/select"
                    })
                    yield k, char

    def sprite_anims_generator(self, data: dict):
        for k, vv in data.items():
            v = self.get_table_unit(vv, 0)
            if skins := v.get("skins", False):
                for skin in skins:
                    if anims := skin.get("spriteAnims", False):
                        # print(k, anims)
                        for anim_type, anim_data in anims.items():
                            postfix_words = re.findall('.[^A-Z]*', anim_type)
                            postfix_words[0] = postfix_words[0].title()
                            char = v.copy()
                            char.update(anim_data)
                            char.update({
                                "animType": anim_type,
                                "postfix_name": f"-{"-".join(postfix_words)}",
                                "for": [GenType.ATTACK_ANIM]
                            })
                            yield k, char

    @staticmethod
    def get_frame(_frame_name, _meta, _im):
        p_dir = os.path.split(__file__)[0]
        p_file = f"{p_dir}/CharacterSelectFrame.png"

        im = Image.open(p_file)
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
        k_id = add_data["k_id"]

        w_id = char_data.get("startingWeapon")

        if w_id and (weapon_data := weapon_data.get(w_id)):
            w_texture = weapon_data[0].get("texture")
            meta, im = func_meta("", w_texture)
            file_name = weapon_data[0].get("frameName").replace(".png", "")

            try:
                if meta.get(f"{file_name}1"):
                    file_name = f"{file_name}1"
                    meta_data = meta.get(file_name)
                else:
                    meta_data = meta.get(file_name) or meta.get(int(file_name))
            except ValueError:
                meta_data = None

            if meta_data is None:
                print(f"! Skipped {name}, {file_name}",
                      file=sys.stderr)
                return

            rect = meta_data["rect"]

            sx, sy = im.size
            w_sprite = im.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))
            w_sprite = w_sprite.resize((w_sprite.size[0] * 4, w_sprite.size[1] * 4), PIL.Image.NEAREST)

            w_sprite_black = w_sprite.copy()

            pixdata = w_sprite_black.load()
            for y in range(w_sprite_black.size[1]):
                for x in range(w_sprite_black.size[0]):
                    if pixdata[x, y][3] > 10:
                        pixdata[x, y] = (0, 0, 0, 255)

            weapon_offset = {
                "x": frame_im.width - w_sprite.width - 10, "y": frame_im.height - w_sprite.height - 12,
            }

            frame_im.alpha_composite(w_sprite_black, (weapon_offset["x"], weapon_offset["y"]))

            frame_im.alpha_composite(w_sprite, (weapon_offset["x"] - 8, weapon_offset["y"] - 4))

        obj_im = obj_im.resize((int(obj_im.size[0] * 3.8), int(obj_im.size[1] * 3.8)), PIL.Image.NEAREST)

        frame_im.alpha_composite(obj_im, (12, frame_im.height - obj_im.height - 11))

        p_dir = os.path.split(__file__)[0]
        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        os.makedirs(sf_text, exist_ok=True)
        os.makedirs(sf_text + '/text', exist_ok=True)

        save_name = self.change_name(name)
        text = add_data["clear_name"].strip()
        font = ImageFont.truetype(fr"{p_dir}/Courier.ttf", 30)
        w = font.getbbox(text)[2] + scale_factor
        h = font.getbbox(text+"|")[3]

        if w > frame_im.size[0] - 4 * scale_factor:
            if " " in text:
                text = text[::-1].replace(" ", "\n", 1)[::-1]

            font = ImageFont.truetype(fr"{p_dir}/Courier.ttf", 28)
            w = font.getbbox(text)[2] + scale_factor
            h = (font.getbbox("|" + text + "|")[3] + scale_factor) * 2

        canvas = Image.new('RGBA', (int(w), int(h)))

        draw = ImageDraw.Draw(canvas)
        draw.text((3, -5), text, "#ffffff", font, stroke_width=1)

        canvas.save(f"{sf_text}/text/{self.iconGroup}-{save_name}.png")

        frame_im.alpha_composite(canvas, (14, 20))

        frame_im.save(f"{sf_text}/{self.iconGroup}-{save_name}.png")


class PowerUpImageGenerator(TableGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = Type.POWERUP
        self.scaleFactor = 8
        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "texture"
        self.dataObjectKey = "name"
        self.langFileName = "powerUpLang.json"

        self.defaultFrameName = "frameD.png"

        self.folderToSave = "power up"
        self.iconGroup = "PowerUp"

    def get_frame_name(self, obj):
        return "frameE.png" if obj.get("specialBG") else super().get_frame_name(obj)


class EnemyImageGenerator(TableGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = Type.ENEMY
        self.frameKey = None
        self.scaleFactor = 4
        self.dataSpriteKey = "frameNames"
        self.dataTextureKey = "textureName"
        self.dataObjectKey = None
        self.langFileName = "enemiesLang.json"
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
        for k, vv in data.items():
            v = self.get_table_unit(vv, 0)

            add_i = 0
            if alias := v.get("alias"):
                v1 = v.copy()
                v1.update(alias)
                for i, frame in enumerate(v1.get("frameNames")):
                    enemy = v1.copy()
                    enemy["frameNames"] = frame
                    enemy["id"] = i

                    yield k, enemy

                add_i = len(v1.get("frameNames"))

            for i, frame in enumerate(v.get("frameNames")):
                enemy = v.copy()
                enemy["frameNames"] = frame
                enemy["id"] = i + add_i

                yield k, enemy


class StageImageGenerator(TableGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = Type.STAGE
        self.frameKey = None
        self.scaleFactor = 4
        self.dataSpriteKey = "uiFrame"
        self.dataTextureKey = "uiTexture"
        self.dataObjectKey = "stageName"
        self.langFileName = "stageLang.json"

        self.folderToSave = "stage"

    def save_png_icon(self, _, im_obj, name, save_folder, scale_factor=1,
                      add_data: dict = None):
        im_obj = im_obj[0]
        if im_obj is None:
            return

        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        os.makedirs(sf_text, exist_ok=True)
        os.makedirs(sf_text + "/text", exist_ok=True)

        im_frame_r = im_obj.resize((im_obj.size[0] * scale_factor, im_obj.size[1] * scale_factor),
                                   PIL.Image.NEAREST)

        save_name = self.change_name(name)
        text = add_data["clear_name"].strip()
        font = ImageFont.truetype(fr"{p_dir}/Courier.ttf", 50 * scale_factor / self.scaleFactor)
        w = font.getbbox(text)[2] + scale_factor
        h = font.getbbox(text + "|")[3]

        canvas = Image.new('RGBA', (int(w), int(h)))

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
    def __init__(self):
        super().__init__()
        self.assets_type = Type.STAGE_SET

        self.folderToSave = "stageset"

    @staticmethod
    def len_data(data: dict):
        return sum(len(d) for d in data.values())

    def unit_generator(self, data: dict):
        return ((k, self.get_table_unit(v, 0)) for set_v in data.values() for k, v in set_v.items())

    def textures_set(self, data: dict):
        return set(
            self.get_table_unit(v, 0).get(self.dataTextureKey) for set_v in data.values() for v in set_v.values())


if __name__ == "__main__":
    pass
