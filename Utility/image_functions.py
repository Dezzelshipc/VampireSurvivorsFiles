from typing import TypeVar

from PIL import Image, ImageOps
from PIL.Image import Resampling
from dataclasses import dataclass

TRect = TypeVar("TRect", bound="SpriteRect")
TPivot = TypeVar("TPivot", bound="SpritePivot")


@dataclass
class SpriteRect:
    x: float
    y: float
    width: float
    height: float

    @staticmethod
    def from_dict(args: dict) -> TRect:
        return SpriteRect(args["x"], args["y"], args["width"], args["height"])

    def __getitem__(self, item):
        # SHOULD NOT BE USED NORMALLY
        return self.__getattribute__(item)


@dataclass
class SpritePivot:
    x: float
    y: float

    @staticmethod
    def from_dict(args: dict) -> TPivot:
        return SpritePivot(args["x"], args["y"])

    def __getitem__(self, item):
        # SHOULD NOT BE USED NORMALLY
        return self.__getattribute__(item)


def crop_image_rect(image: Image, rect: SpriteRect | dict):
    _rect: SpriteRect = rect if isinstance(rect, SpriteRect) else SpriteRect.from_dict(rect)
    sx, sy = image.size
    return image.crop((_rect.x, sy - _rect.y - _rect.height, _rect.x + _rect.width, sy - _rect.y))


def resize_image(image: Image, scale_factor: float):
    return image.resize((image.size[0] * scale_factor, image.size[1] * scale_factor), Resampling.NEAREST)


def affine_transform(image: Image, matrix: tuple) -> Image:
    e00, e10, e01, e11 = matrix

    if e00 + e10 < 0:
        image = ImageOps.mirror(image)

    if e01 + e11 < 0:
        image = ImageOps.flip(image)

    if e10 or e01:
        image = image.rotate(-90)
        image = ImageOps.flip(image)

    return image
