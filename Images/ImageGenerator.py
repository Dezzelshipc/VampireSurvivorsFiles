from enum import Enum
import yaml
import json
import os
from PIL import Image, ImageFont, ImageDraw
import PIL.Image


def read_env(file: os.path) -> dict:
    d = {}
    with open(file, 'r', encoding="UTF-8") as f:
        for line in f.readlines():
            k, v = line.split("=")
            k = k.strip()
            v = v.strip()
            d.update({k: v})
    return d


class Type(Enum):
    WEAPON = 0
    CHARACTER = 1
    ITEM = 2
    ENEMY = 3
    STAGE = 4
    STAGE_SET = 5
    PROP = 6


class PictureGenerator:
    @staticmethod
    def assets_gen(path):
        dirs = [path]
        files = []
        while len(dirs) > 0:
            this_dir = dirs.pop(0)
            files.extend(f for f in os.scandir(this_dir) if f.name.endswith(".meta") and not f.is_dir())
            dirs.extend(f for f in os.scandir(this_dir) if f.is_dir())

        return files

    def __init__(self, assets_type: Type, env: dict):
        folder_with_data = r"../Data/Auto Generated"
        folder_with_lang = r"../Translations/lang"
        assets_files_folder = env["ASSETS_FOLDER"]  # \Assets\Resources\spritesheets

        self.assets_type = assets_type

        self.assets = self.assets_gen(assets_files_folder)

        self.json = {}
        self.lang = {}

        self.loaded_meta = {}

        self.dataSpriteKey = "frameName"
        self.dataTextureKey = "texture"
        self.dataObjectKey = "name"
        self.scaleFactor = 8
        self.folderToSave = None
        self.frameKey = "collectionFrame"
        self.langPath = ""

        match self.assets_type:
            case Type.WEAPON:
                self.dataPath = folder_with_data + "/weaponData_Full.json"
                self.folderToSave = "weapons"
            case Type.CHARACTER:
                self.dataPath = folder_with_data + "/characterData_Full.json"
                self.scaleFactor = 4
                self.dataSpriteKey = "spriteName"
                self.dataTextureKey = "textureName"
                self.dataObjectKey = "charName"
                # self.folderToSave = "characters"
            case Type.ITEM:
                self.dataPath = folder_with_data + "/itemData_Full.json"
            case Type.ENEMY:
                self.folderToSave = "enemies"
                self.dataTextureKey = "textureName"
                self.dataSpriteKey = "frameNames"
                self.dataPath = folder_with_data + "/enemyData_Full.json"
            case Type.STAGE:
                self.scaleFactor = 4
                self.folderToSave = "stages"
                self.dataTextureKey = "uiTexture"
                self.dataSpriteKey = "uiFrame"
                self.dataObjectKey = "stageName"
                self.dataPath = folder_with_data + "/stageData_Full.json"
                self.langPath = folder_with_lang + "/stageLang.json"
            case Type.STAGE_SET:
                self.scaleFactor = 4
                self.folderToSave = "stagesets"
                self.dataTextureKey = "uiTexture"
                self.dataSpriteKey = "uiFrame"
                self.dataObjectKey = "stageName"
                self.dataPath = folder_with_data + "/stagesetData_Full.json"
                self.langPath = folder_with_lang + "/stageLang.json"
            case Type.PROP:
                self.dataTextureKey = "textureName"
                self.dataObjectKey = "frameName"
                self.folderToSave = "props"
                self.dataPath = folder_with_data + "/propsData_Full.json"

    def generate_by_meta(self, file, scale_factor: int = 1):
        meta, im = self.get_meta(file)
        folder_to_save = "./Generated/By meta"
        subfolder_to_save = f"{folder_to_save}/{file}"

        if not os.path.isdir(folder_to_save):
            os.mkdir(folder_to_save)
        if not os.path.isdir(subfolder_to_save):
            os.mkdir(subfolder_to_save)

        print(f"Files out of {len(meta)}:")

        for i, (pic_name, rect) in enumerate(meta.items()):
            print(f"\r{i + 1}", end="")
            sx, sy = im.size

            im_crop = im.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

            im_crop = im_crop.resize((im_crop.size[0] * scale_factor, im_crop.size[1] * scale_factor),
                                     PIL.Image.NEAREST)
            im_crop.save(f"{subfolder_to_save}/{pic_name}.png")

    def generate(self):
        if not os.path.isdir("./Generated"):
            os.mkdir("./Generated")

        self.load_json_data()
        self.iterate()

    def load_json_data(self):
        with open(self.dataPath, 'r', encoding="UTF-8") as f:
            self.json = dict(json.loads(f.read()))

        if self.langPath:
            with open(self.langPath, 'r', encoding="UTF-8") as f:
                self.lang = dict(json.loads(f.read()))["en"]

    def iterate(self):
        for k_id, val in self.json.items():
            match self.assets_type:
                case Type.ITEM | Type.PROP:
                    self.simple_object(k_id, val)
                case Type.WEAPON | Type.CHARACTER | Type.ENEMY | Type.STAGE:
                    self.table_object(k_id, val, 0)
                case Type.STAGE_SET:
                    for k_id2, val2 in val.items():
                        self.table_object(k_id2, val2, 0)
                case _:
                    pass

    def simple_object(self, k_id, obj):
        name = obj.get(self.dataObjectKey, '')
        match self.assets_type:
            case Type.ENEMY:
                name = k_id
                file_name = obj[self.dataSpriteKey][0].replace(".png", "")
            case _:
                if "Megalo" in obj.get('prefix', ''):
                    name = f"Megalo {name}"
                file_name = obj[self.dataSpriteKey].replace(".png", "")
        texture_name = obj[self.dataTextureKey]

        save_folder = self.folderToSave if self.folderToSave else texture_name
        sf_text = f'./Generated/{save_folder}'
        sf_text_i = f'{sf_text}/icon'
        if not os.path.isdir(sf_text):
            os.mkdir(sf_text)
        if not os.path.isdir(sf_text_i):
            os.mkdir(sf_text_i)

        print(k_id, texture_name, file_name)
        if len(file_name) == 0 or len(name) == 0:
            print("-")
            return

        frame_name = obj.get(self.frameKey, "").replace(".png", "")
        if frame_name == "":
            match self.assets_type, obj:
                case Type.ITEM, {"isRelic": True}:
                    frame_name = "frameF"
                case Type.ITEM, _:
                    frame_name = "frameC"
                case Type.WEAPON, _:
                    frame_name = "frameB"
                case _:
                    pass

        self.read_asset_and_save_png(file_name, k_id, name, texture_name, save_folder, frame_name)

    def table_object(self, k_id, obj, index):
        self.simple_object(k_id, obj[index])

    def read_asset_and_save_png(self, file_name, k_id, name, texture_name, save_folder, frame_name=None,
                                prefix_name="Sprite-"):

        meta, im = self.get_meta(texture_name)

        y = meta[file_name]

        sx, sy = im.size

        im_crop = im.crop((y['x'], sy - y['y'] - y['height'], y['x'] + y['width'], sy - y['y']))

        im_crop = im_crop.resize((im_crop.size[0] * self.scaleFactor, im_crop.size[1] * self.scaleFactor),
                                 PIL.Image.NEAREST)

        save_dlc = ''
        match frame_name:
            case "frameB_blue":
                save_dlc = "/moonspell"
            case "frameB_green":
                save_dlc = "/foscari"
            case "frameB_purple":
                save_dlc = "/meeting"
            case "frameB_red":
                save_dlc = "/red_dlc"

        sf_text = f'./Generated/{save_folder}{save_dlc}'
        sf_text_i = f'{sf_text}/icon'

        if not os.path.isdir(sf_text):
            os.mkdir(sf_text)
        if not os.path.isdir(sf_text_i):
            os.mkdir(sf_text_i)

        im_crop.save(f"{sf_text}/{prefix_name}{name}.png")

        match self.assets_type, frame_name:
            case Type.STAGE | Type.STAGE_SET, _:
                obj_lang = self.lang.get(k_id, None)
                if not obj_lang:
                    text = name
                else:
                    text = obj_lang["stageName"]

                font = ImageFont.truetype(r"./Courier.ttf", 55)
                canvas = Image.new('RGBA', (font.getsize(text)[0], font.getsize(text + "|")[1]))

                draw = ImageDraw.Draw(canvas)
                draw.text((3, -5), text, "#eef92b", font, stroke_width=1)

                # canvas.show()
                # im_crop.show()
                crx, cry = im_crop.size
                crx //= 2
                cry = int(cry / 5)
                frx, fry = canvas.size
                frx //= 2
                fry //= 2
                im_crop.alpha_composite(canvas, (crx - frx, cry - fry))
                im_crop.save(f"{sf_text_i}/Stage-{text}.png")
            case _, None:
                pass
            case Type.WEAPON | Type.ITEM, _:
                im_frame = self.get_frame(frame_name)
                crx, cry = im_crop.size
                crx //= 2
                cry //= 2
                frx, fry = im_frame.size
                frx //= 2
                fry //= 2
                im_frame.alpha_composite(im_crop, (frx - crx, fry - cry))

                im_frame.save(f"{sf_text_i}/Icon-{name}.png")

    def get_frame(self, frame_name):
        if f'{frame_name}.png' not in os.listdir("./Generated/frames"):
            asset = list(filter(lambda x: x.name.startswith(frame_name), self.assets))
            self.read_asset_and_save_png(asset[0], frame_name, "UI", "frames", prefix_name="")

        return Image.open(f'./Generated/frames/{frame_name}.png')

    def get_meta(self, file) -> (dict, Image.Image):
        if file not in self.loaded_meta:
            asset = sorted(filter(lambda x: file in x.name, self.assets), key=lambda x: abs(len(x.name) - len(file)))
            print(f"Parsing {asset[0].name}")
            with open(asset[0]) as f:
                sprites = dict(yaml.safe_load(f.read()))["TextureImporter"]["spriteSheet"]["sprites"]
            self.loaded_meta.update({file: {s["name"]: s["rect"] for s in sprites},
                                     file + "Image": Image.open(asset[0].path.replace(".meta", ""))})
            print(f"Parse {asset[0].name} ended")
        return self.loaded_meta[file], self.loaded_meta[file + "Image"]


if __name__ == "__main__":
    env_f = read_env(r".env")  # ASSETS_FOLDER
    gen = PictureGenerator(Type.STAGE_SET, env_f)
    # gen.generate()
    gen.generate_by_meta("randomazzo")
