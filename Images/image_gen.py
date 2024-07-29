from enum import Enum
import os
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
    PROPS = 8


class GenType(Enum):
    SCALE = 0
    FRAME = 1
    ANIM = 2
    DEATH_ANIM = 3


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
        return name.strip()

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

        return im.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

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

        return im_crop

    def save_png_icon(self, im_frame, im_obj, name, save_folder, scale_factor=1) -> None:
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

    def save_gif(self, meta, im: Image, file_name, name, save_folder, frames_count, prefix_name="Animated-",
                 save_append="",
                 duration_factor=8, scale_factor=1, base_duration=150, leading_zeros: None | int = None) -> None:
        sx, sy = im.size

        start_index = 0
        if file_name.endswith("01"):
            file_name_clean = file_name[:-2]
            start_index = 1
        elif file_name.endswith("0"):
            file_name_clean = file_name[:-1]
        else:
            file_name_clean = file_name

        if not frames_count:
            frames_count = len(list(filter(lambda k: str(k).startswith(file_name_clean), meta.keys())))
            if not file_name_clean.endswith("i"):
                frames_count -= len(list(filter(lambda k: str(k).startswith(file_name_clean + "i"), meta.keys())))

        im_list = []
        skipped_frames = 0
        for i in range(frames_count):
            frame_name = f"{file_name_clean}{str(i + start_index).zfill(leading_zeros or self.animLeadingZeros)}"

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
        # print(file_name_clean, max_pivot, im_list)

        gif_list = []
        for image, pivot, rect in im_list:
            new_size = (
                pivot["x"] - max_pivot["x"],
                pivot["-y"] - max_pivot["-y"],
                rect["width"] + max_pivot["-x"] - pivot["-x"],
                rect["height"] + max_pivot["y"] - pivot["y"]
            )
            im_t = image.crop(new_size)
            # print(new_size, image.size)

            im_r = im_t.resize((im_t.size[0] * scale_factor, im_t.size[1] * scale_factor), PIL.Image.NEAREST)
            gif_list.append(im_r)

        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}/anim{save_append}'

        if not os.path.isdir(sf_text):
            os.makedirs(sf_text)

        duration_scale = 8 / duration_factor if duration_factor else 4 / frames_count

        name = self.change_name(name)
        gif_list[0].save(f"{sf_text}/{prefix_name}{name}.gif", save_all=True, append_images=gif_list[1:],
                         duration=base_duration * duration_scale, loop=0, disposal=2)


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

    def make_image(self, func_meta, k_id, obj: dict, lang_file=None, **settings):
        name = obj.get(self.dataObjectKey) or k_id
        texture_name = obj.get(self.dataTextureKey)
        file_name = self.get_sprite_name(obj).replace(".png", "")
        frame_name = self.get_frame_name(obj)
        save_folder = self.folderToSave if self.folderToSave else texture_name

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

        scale_factor = settings["scale_factor"]

        im_obj = self.save_png(meta, im, file_name, name, save_folder, scale_factor=scale_factor)

        if settings.get("is_with_frame"):
            im_frame = self.get_frame(frame_name, *func_meta("", "UI"))
            if im_frame or self.assets_type in [Type.STAGE, Type.STAGE_SET]:
                self.save_png_icon(im_frame, im_obj, name, save_folder, scale_factor=scale_factor)

        if settings.get("is_with_anim"):
            if self.assets_type in [Type.ENEMY]:
                self.save_gif(meta, im, f"{file_name[:-1]}i01", name, save_folder,
                              obj.get(self.dataAnimFramesKey), scale_factor=scale_factor, leading_zeros=2)

            else:
                self.save_gif(meta, im, file_name, name, save_folder, obj.get(self.dataAnimFramesKey),
                              duration_factor=obj.get("walkFrameRate"), scale_factor=scale_factor)

        if settings.get("is_with_death_anim"):
            self.save_gif(meta, im, file_name, name, save_folder,
                          None, save_append="_death", scale_factor=scale_factor, duration_factor=0,
                          prefix_name="Animated-Death-", base_duration=250)


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

        self.available_gen.remove(GenType.FRAME)

    @staticmethod
    def change_name(name):
        return name[name.find("-") + 1:].strip()


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

        self.available_gen.remove(GenType.FRAME)
        self.available_gen.append(GenType.ANIM)

    @staticmethod
    def len_data(data: dict):
        return sum(len(v[0].get("skins")) if v[0].get("skins") else 1 for v in data.values())

    def unit_generator(self, data: dict):
        return self.skins_generator(data)

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

    def save_png_icon(self, im_frame, im_obj, name, save_folder, scale_factor=1):
        if im_obj is None:
            return

        p_dir = os.path.split(__file__)[0]

        sf_text = f'{p_dir}/Generated/{save_folder}/icon'

        if not os.path.isdir(sf_text):
            os.makedirs(sf_text)
            os.makedirs(sf_text + "/text")

        im_frame_r = im_obj.resize((im_obj.size[0] * scale_factor, im_obj.size[1] * scale_factor),
                                   PIL.Image.NEAREST)

        text = self.change_name(name)
        font = ImageFont.truetype(fr"{p_dir}/Courier.ttf", 50)
        w = font.getbbox(text)[2] + scale_factor
        h = font.getbbox(text + "|")[3]

        canvas = Image.new('RGBA', (int(w), int(h)))

        draw = ImageDraw.Draw(canvas)
        draw.text((3, -5), text, "#eef92b", font, stroke_width=1)
        canvas.save(f"{sf_text}/text/Stage-{text}.png")

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
    pass
