from PIL import Image
from PIL.Image import Resampling

from Utility.utility import run_multiprocess
from .meta_data import MetaData

def crop_image_rect(image: Image, rect: dict):
    sx, sy = image.size
    return image.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))


def resize_image(image: Image, scale_factor: float):
    return image.resize((image.size[0] * scale_factor, image.size[1] * scale_factor), Resampling.NEAREST)


def split_image(meta_data: MetaData) -> dict[str|int: Image]:
    sprites_args = [ (meta_data.image, data['rect']) for name, data in meta_data.data_name.items() ]
    sprites = run_multiprocess(crop_image_rect, sprites_args)

    sprites_zipped = zip(sprites, meta_data.data_name.items())
    sprites_dict = dict()
    for sprite, (_, data) in sprites_zipped:
        sprites_dict.update({
            data["name"]: sprite,
            data["internalID"]: sprite
        })
    return sprites_dict