import itertools
import re
from enum import Enum
import os
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

        return None


class ImageGenerator:
    def __init__(self):
        self.assets_type = Type.NONE
        self.dataSpriteKey = None
        self.dataTextureKey = None
        self.dataObjectKey = None
        self.scaleFactor = 1
        self.folderToSave = None
        self.frameKey = None
        self.langFileName = None
        self.defaultFrameName = None
        self.dataAnimFramesKey = None

        self.iconGroup = "Icon"

        self.animLeadingZeros = 2

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

    def save_png(self, meta, im, file_name, name, save_folder, prefix_name="Sprite-", scale_factor=1) -> Image:
        try:
            if meta.get(f"{file_name}1"):
                file_name = f"{file_name}1"
                meta_data = meta.get(file_name)
            else:
                meta_data = meta.get(file_name) or meta.get(int(file_name))
        except ValueError:
            meta_data = None

        if meta_data is None:
            print(f"Skipped {name}, {file_name}")
            return

        rect = meta_data["rect"]

        sx, sy = im.size

        im_crop = im.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

        im_crop_r = im_crop.resize((im_crop.size[0] * scale_factor, im_crop.size[1] * scale_factor),
                                   PIL.Image.NEAREST)

        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}'

        if not os.path.isdir(sf_text):
            os.makedirs(sf_text)

        name = self.change_name(name)
        im_crop_r.save(f"{sf_text}/{prefix_name}{name}.png")

        return im_crop, meta_data

    def save_png_icon(self, im_frame_data, im_obj_data, name, save_folder, scale_factor=1) -> None:
        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        if not os.path.isdir(sf_text):
            os.makedirs(sf_text)

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

    def save_gif(self, meta, im: Image, file_name, name, save_folder, frames_count: None | int = None,
                 prefix_name="Animated-", postfix_name="", save_append="", frame_rate=6, scale_factor=1,
                 base_duration=1000, start_index=1, file_name_clean=None,
                 leading_zeros: None | int = None) -> None:
        sx, sy = im.size

        file_name_clean = file_name_clean or file_name

        if not frames_count:
            frames_count = len(list(
                filter(lambda k: str(k).startswith(file_name_clean) and re.match(fr"^{file_name_clean}\d", str(k)),
                       meta.keys())))

        im_list = []
        skipped_frames = 0
        for i in range(frames_count):
            append = ""
            if start_index or leading_zeros:
                append = str(i + start_index).zfill(leading_zeros or self.animLeadingZeros)
            frame_name = f"{file_name_clean}{append}"

            try:
                meta_data = meta.get(frame_name) or meta.get(int(frame_name))
            except ValueError:
                meta_data = None

            if meta_data is None:
                print(f"Skipped {name}, {frame_name} not found, total frames count {frames_count}")
                skipped_frames += 1
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
        frames_count -= skipped_frames

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

        if not os.path.isdir(sf_text):
            os.makedirs(sf_text)

        total_duration = base_duration // frame_rate

        name = self.change_name(name)
        tr_save.save_transparent_gif(gif_list, total_duration, f"{sf_text}/{prefix_name}{name}{postfix_name}.gif")


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

    @staticmethod
    def get_prepared_frame(frame_name, add="") -> (str, int, int, str):
        number = re.search(r"(\d+)$", frame_name)
        fn = frame_name

        if number:
            fn = fn[:number.start()]
            zeros = len(number.group(1))
            start = int(number.group(1))
            if add == "i":
                zeros = 2
                start = 1

            return f"{fn}{add}{number.group(1)}", zeros, start, f"{fn}{add}"

        if add == "i":
            return f"{frame_name}_{add}01", 2, 1, f"{fn}_{add}"

        return frame_name, 0, 0, frame_name

    def make_image(self, func_meta, k_id, obj: dict, lang_file=None, **settings):
        name = obj.get(self.dataObjectKey) or k_id
        texture_name = obj.get(self.dataTextureKey)
        file_name = self.get_sprite_name(obj).replace(".png", "")
        frame_name = self.get_frame_name(obj)
        save_folder = self.folderToSave or texture_name

        if save_folder.endswith("/"):
            save_folder += texture_name

        meta, im = func_meta("", texture_name)
        if not meta:
            print(f"Skipped {name}: {texture_name} texture not found")
            return

        save_dlc = ''
        match frame_name:
            case "frameB_blue.png":
                save_dlc = "/moonspell"
            case "frameB_green.png":
                save_dlc = "/foscari"
            case "frameB_purple.png":
                save_dlc = "/meeting"
            case "frameB_gray.png":
                save_dlc = "/guns"
            case "frameB_red.png":
                save_dlc = "/red_dlc"

        if osf := obj.get("save_folder"):
            save_folder += osf

        save_folder += f"/{save_dlc}"

        if self.dataObjectKey and lang_file and lang_file.get(k_id):
            name = lang_file.get(k_id).get(self.dataObjectKey)

        sprite_id = obj.get("id", 0)
        if obj.get("name") == "Hallows":
            name += f"-H"
        elif sprite_id != 0:
            name += f"-{sprite_id + 1}"

        if "Megalo" in obj.get('prefix', ''):
            name = f"Megalo {name}"

        using_list = obj.get('for', GenType.main_list())
        scale_factor = settings[str(GenType.SCALE)]

        if GenType.SCALE in using_list:
            if self.assets_type in [Type.ENEMY]:
                prep = self.get_prepared_frame(file_name, "i")
                im_obj = self.save_png(meta, im, prep[0], name, save_folder, scale_factor=scale_factor)
            else:
                im_obj = self.save_png(meta, im, file_name, name, save_folder, scale_factor=scale_factor)

        if settings.get(str(GenType.FRAME)) and GenType.FRAME in using_list:
            im_frame = self.get_frame(frame_name, *func_meta("", "UI"))
            if im_frame or self.assets_type in [Type.STAGE, Type.STAGE_SET]:
                self.save_png_icon(im_frame, im_obj, name, save_folder, scale_factor=scale_factor)

        if settings.get(str(GenType.ANIM)) and GenType.ANIM in using_list:
            if self.assets_type in [Type.ENEMY]:
                prep = self.get_prepared_frame(file_name, "i")
                self.save_gif(meta, im, prep[0], name, save_folder, obj.get(self.dataAnimFramesKey),
                              scale_factor=scale_factor, leading_zeros=2, start_index=prep[2],
                              file_name_clean=prep[3])

            else:
                prep = self.get_prepared_frame(file_name)
                self.save_gif(meta, im, prep[0], name, save_folder, obj.get(self.dataAnimFramesKey),
                              frame_rate=obj.get("walkFrameRate", 6), scale_factor=scale_factor, leading_zeros=2,
                              start_index=prep[2],
                              file_name_clean=prep[3])

        if settings.get(str(GenType.DEATH_ANIM)) and GenType.DEATH_ANIM in using_list:
            prep = self.get_prepared_frame(file_name)
            self.save_gif(meta, im, prep[0], name, save_folder, None, prefix_name="Animated-Death-",
                          save_append="_death", scale_factor=scale_factor, frame_rate=20, leading_zeros=prep[1],
                          start_index=prep[2], file_name_clean=prep[3])

        if settings.get(str(GenType.ATTACK_ANIM)) and GenType.ATTACK_ANIM in using_list:
            prep = self.get_prepared_frame(file_name)
            self.save_gif(meta, im, prep[0], name, save_folder, None, prefix_name="Animated-",
                          save_append="_attack", scale_factor=scale_factor, frame_rate=obj.get("frameRate", 6),
                          leading_zeros=2, start_index=prep[2], file_name_clean=prep[3],
                          postfix_name=obj.get("postfix_name"))


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
            vv.update({
                "for": [GenType.SCALE],
                "save_folder": "/picture"
            })
            yield k, vv

            vv = v.copy()
            vv.update({
                "texture": "items",
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

        self.animLeadingZeros = 0

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
        self.folderToSave = "characters/"
        self.langFileName = "characterLang.json"
        self.dataAnimFramesKey = "walkingFrames"

        self.available_gen.remove(GenType.FRAME)
        self.available_gen.append(GenType.ANIM)
        self.available_gen.append(GenType.ATTACK_ANIM)

    @staticmethod
    def len_data(data: dict):
        return (sum(len(v[0].get("skins")) if v[0].get("skins") else 1 for v in data.values()) +
                sum(len(v[0].get("spriteAnims")) if v[0].get("spriteAnims") else 0 for v in data.values()))

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
            else:
                yield k, v

    def sprite_anims_generator(self, data: dict):
        sprite_anims_types = {
            "rangedAttack": ("-Ranged-Attack",),
            "meleeAttack": ("-Melee-Attack",),
        }
        for k, vv in data.items():
            v = self.get_table_unit(vv, 0)
            if anims := v.get("spriteAnims", False):
                for anim_type, anim_data in anims.items():
                    char = v.copy()
                    char.update(anim_data)
                    char.update({
                        "animType": anim_type,
                        "postfix_name": sprite_anims_types[anim_type][0],
                        "for": [GenType.ATTACK_ANIM]
                    })

                    yield k, char


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
        self.animLeadingZeros = 1

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
            for i, frame in enumerate(v.get("frameNames")):
                enemy = v.copy()
                enemy["frameNames"] = frame
                enemy["id"] = i

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

    def save_png_icon(self, _, im_obj, name, save_folder, scale_factor=1):
        im_obj = im_obj[0]
        if im_obj is None:
            return

        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        if not os.path.isdir(sf_text):
            os.makedirs(sf_text)
            os.makedirs(sf_text + "/text")

        im_frame_r = im_obj.resize((im_obj.size[0] * scale_factor, im_obj.size[1] * scale_factor),
                                   PIL.Image.NEAREST)

        text = name.strip()
        save_name = self.change_name(name)
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
