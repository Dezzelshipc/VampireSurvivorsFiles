from PIL import Image
from PIL.Image import Resampling

def crop_image_rect(image: Image, rect: dict):
    sx, sy = image.size
    return image.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))


def resize_image(image: Image, scale_factor: float):
    return image.resize((image.size[0] * scale_factor, image.size[1] * scale_factor), Resampling.NEAREST)