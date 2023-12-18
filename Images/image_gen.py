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
    PROP = 6


class IGFactory:
    @staticmethod
    def get(data_file: str):
        if "weapon" in data_file:
            return WeaponImageGenerator()
        elif "character" in data_file:
            return CharacterImageGenerator()
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

    def textures_set(self, data):
        pass

    def uint_generator(self, data):
        pass

    @staticmethod
    def get_simple_uint(obj):
        return obj

    @staticmethod
    def get_table_unit(obj, index):
        return obj[index]

    @staticmethod
    def get_frame(frame_name):
        p_dir = os.path.split(__file__)[0]
        full_path = p_dir + f"/Generated/By meta/UI/{frame_name}"

        if not os.path.exists(full_path):
            return None

        return Image.open(full_path)


    @staticmethod
    def save_png(meta, im, file_name, name, save_folder, prefix_name="Sprite-", scale_factor=1):
        rect = meta[file_name]

        sx, sy = im.size

        im_crop = im.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

        im_crop_r = im_crop.resize((im_crop.size[0] * scale_factor, im_crop.size[1] * scale_factor),
                                   PIL.Image.NEAREST)

        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}'

        if not os.path.isdir(sf_text):
            os.makedirs(sf_text)

        im_crop_r.save(f"{sf_text}/{prefix_name}{name}.png")

        return im_crop

    @staticmethod
    def save_png_icon(im_frame, im_obj, name, save_folder, scale_factor=1):
        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        if not os.path.isdir(sf_text):
            os.makedirs(sf_text)

        sprite_w, sprite_h = im_obj.size
        sprite_w //= 2
        sprite_h //= 2
        frame_w, frame_h = im_frame.size
        frame_w //= 2
        frame_h //= 2
        im_frame.alpha_composite(im_obj, (frame_w - sprite_w, frame_h - sprite_h))

        im_frame_r = im_frame.resize((im_frame.size[0] * scale_factor, im_frame.size[1] * scale_factor),
                                     PIL.Image.NEAREST)

        im_frame_r.save(f"{sf_text}/Icon-{name}.png")


class TableGenerator(ImageGenerator):
    def uint_generator(self, data: dict):
        return ((k, self.get_table_unit(v, 0)) for k, v in data.items())

    def textures_set(self, data: dict):
        return set(self.get_table_unit(v, 0).get(self.dataTextureKey) for v in data.values())

    def len_data(self, data: dict):
        return len(data)

    def make_image(self, func_meta, k_id, obj: dict, scale_factor=1, is_with_frame=False, lang_file=None):
        name = obj.get(self.dataObjectKey)
        file_name = obj.get(self.dataSpriteKey).replace(".png", "")
        texture_name = obj.get(self.dataTextureKey)
        frame_name = obj.get(self.frameKey, self.defaultFrameName)
        save_folder = self.folderToSave if self.folderToSave else texture_name

        meta, im = func_meta("", texture_name)


        save_dlc = ''
        match frame_name:
            case "frameB_blue.png":
                save_dlc = "/moonspell"
            case "frameB_green.png":
                save_dlc = "/foscari"
            case "frameB_purple.png":
                save_dlc = "/chalcedony"
            case "frameB_red.png":
                save_dlc = "/red_dlc"
        save_folder += f"/{save_dlc}"

        if lang_file:
            name = lang_file.get(k_id).get(self.dataObjectKey)

        if "Megalo" in obj.get('prefix', ''):
            name = f"Megalo {name}"

        im_obj = self.save_png(meta, im, file_name, name, save_folder, scale_factor=scale_factor)

        if is_with_frame:
            im_frame = self.get_frame(frame_name)
            if im_frame:
                self.save_png_icon(im_frame, im_obj, name, save_folder, scale_factor=scale_factor)


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
        self.langPath = "characterLang.json"


if __name__ == "__main__":
    ch = CharacterImageGenerator()
    print(ch.get_lang_path("characterData_Full.json"))
