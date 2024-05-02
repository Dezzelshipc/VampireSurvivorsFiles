from enum import Enum
import os
import json
from PIL import Image, ImageFont, ImageDraw
import PIL.Image


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
        else:
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

        self.is_with_frame = False

        self.iconGroup = "Icon"

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
        return name

    @staticmethod
    def get_frame(frame_name):
        p_dir = os.path.split(__file__)[0]
        full_path = p_dir + f"/Generated/By meta/UI/{frame_name}"

        if not os.path.exists(full_path):
            return None

        return Image.open(full_path)

    def save_png(self, meta, im, file_name, name, save_folder, prefix_name="Sprite-", scale_factor=1):
        try:
            rect = meta.get(file_name) or meta.get(int(file_name))
        except ValueError:
            rect = None

        if rect is None:
            print(f"Skipped {name}")
            return

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

        return im_crop

    def save_png_icon(self, im_frame, im_obj, name, save_folder, scale_factor=1):
        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        if not os.path.isdir(sf_text):
            os.makedirs(sf_text)

        if im_obj is None:
            return

        sprite_w, sprite_h = im_obj.size
        sprite_w //= 2
        sprite_h //= 2
        frame_w, frame_h = im_frame.size
        frame_w //= 2
        frame_h //= 2
        im_frame.alpha_composite(im_obj, (frame_w - sprite_w, frame_h - sprite_h))

        im_frame_r = im_frame.resize((im_frame.size[0] * scale_factor, im_frame.size[1] * scale_factor),
                                     PIL.Image.NEAREST)

        name = self.change_name(name)
        im_frame_r.save(f"{sf_text}/{self.iconGroup}-{name}.png")


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

    def make_image(self, func_meta, k_id, obj: dict, scale_factor=1, is_with_frame=False, lang_file=None):
        name = obj.get(self.dataObjectKey) or k_id
        texture_name = obj.get(self.dataTextureKey)
        file_name = self.get_sprite_name(obj).replace(".png", "")
        frame_name = self.get_frame_name(obj)
        save_folder = self.folderToSave if self.folderToSave else texture_name

        if save_folder.endswith("/"):
            save_folder += texture_name

        meta, im = func_meta("", texture_name)

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

        save_folder += f"/{save_dlc}"

        if lang_file and lang_file.get(k_id):
            name = lang_file.get(k_id).get(self.dataObjectKey)

        if "Megalo" in obj.get('prefix', ''):
            name = f"Megalo {name}"

        im_obj = self.save_png(meta, im, file_name, name, save_folder, scale_factor=scale_factor)

        if is_with_frame:
            im_frame = self.get_frame(frame_name)
            if im_frame or self.assets_type in [Type.STAGE, Type.STAGE_SET]:
                self.save_png_icon(im_frame, im_obj, name, save_folder, scale_factor=scale_factor)


class ItemImageGenerator(SimpleGenerator):
    def __init__(self):
        super().__init__()
        self.assets_type = Type.ITEM
        self.frameKey = "collectionFrame"
        self.scaleFactor = 8
        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "texture"
        self.dataObjectKey = "name"
        self.langFileName = "itemLang.json"
        self.defaultFrameName = "frameB.png"

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
        self.langFileName = "arcanaLang.json"

    @staticmethod
    def change_name(name):
        return name[name.find("-")+1:].strip()


class TableGenerator(SimpleGenerator):
    def unit_generator(self, data: dict):
        return ((k, self.get_table_unit(v, 0)) for k, v in data.items())

    def textures_set(self, data: dict):
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

        self.folderToSave = "enemy"

    def get_sprite_name(self, obj):
        return super().get_sprite_name(obj)[0]


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

    @staticmethod
    def save_png_icon(im_frame, im_obj, name, save_folder, scale_factor=1):
        if im_obj is None:
            return

        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        if not os.path.isdir(sf_text):
            os.makedirs(sf_text)

        im_frame_r = im_obj.resize((im_obj.size[0] * scale_factor, im_obj.size[1] * scale_factor),
                                   PIL.Image.NEAREST)

        text = name
        font = ImageFont.truetype(fr"{p_dir}/Courier.ttf", 55)
        w = font.getbbox(text)[2]
        h = font.getbbox(text + "|")[3]

        canvas = Image.new('RGBA', (int(w), int(h)))

        draw = ImageDraw.Draw(canvas)
        draw.text((3, -5), text, "#eef92b", font, stroke_width=1)
        canvas.save(f"{sf_text}/Stage-{text}1.png")

        # canvas.show()
        # im_crop.show()
        crx, cry = im_frame_r.size
        crx //= 2
        cry = int(cry / 5)
        frx, fry = canvas.size
        frx //= 2
        fry //= 2
        im_frame_r.alpha_composite(canvas, (crx - frx, cry - fry))
        im_frame_r.save(f"{sf_text}/Stage-{text}.png")


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
    ch = CharacterImageGenerator()
    print(ch.get_lang_path("itemLang.json"))
