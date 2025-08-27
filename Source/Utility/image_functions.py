import re
from typing import Iterable

from PIL import ImageOps
from PIL.Image import Image, Resampling

from Source.Utility.sprite_data import SpriteData, SpriteRect, AnimationData


def crop_image_rect_left_bot(image: Image, rect: SpriteRect | dict) -> Image:
    _rect: SpriteRect = rect if isinstance(rect, SpriteRect) else SpriteRect.from_dict(rect)
    sx, sy = image.size
    return image.crop((_rect.x, sy - _rect.y - _rect.height, _rect.x + _rect.width, sy - _rect.y))


def crop_image_rect_left_top(image: Image, rect: SpriteRect | dict) -> Image:
    _rect: SpriteRect = rect if isinstance(rect, SpriteRect) else SpriteRect.from_dict(rect)
    return image.crop((_rect.x, _rect.y, _rect.width + _rect.x, _rect.height + _rect.y))


def resize_image(image: Image, scale_factor: int | float) -> Image:
    return image.resize((int(image.size[0] * scale_factor), int(image.size[1] * scale_factor)), Resampling.NEAREST)


def resize_list_images(images: list[Image], scale_factor: int) -> list[Image]:
    return list(map(resize_image, images, (scale_factor,) * len(images)))


def affine_transform(image: Image, matrix: tuple[int, int, int, int]) -> Image:
    e00, e10, e01, e11 = matrix

    if e00 + e10 < 0:
        image = ImageOps.mirror(image)

    if e01 + e11 < 0:
        image = ImageOps.flip(image)

    if e10 or e01:
        image = image.rotate(-90)
        image = ImageOps.flip(image)

    return image


def split_name_count(name: str) -> tuple[str, int]:
    name = str(name)
    count = re.search(r"\d+$", name)

    if not count:
        return name, -1

    num = count.group()
    return name.replace(num, "") or "_", int(num)


# Note: pivots for sprites of animation are on the same relative pixel for the whole animation
def get_rects_by_sprite_list(sprites_list: list[SpriteData]) -> list[SpriteRect]:
    relative_pivots = []
    for sprite in sprites_list:
        pivot = {
            "x": round(sprite.rect.width * sprite.pivot.x),
            "y": round(sprite.rect.height * sprite.pivot.y),
        }
        pivot.update({
            "-x": sprite.rect.width - pivot["x"],
            "-y": sprite.rect.height - pivot["y"]
        })
        relative_pivots.append(pivot)

    max_pivot = {k: max(p[k] for p in relative_pivots) for k in relative_pivots[0].keys()}

    sprite_rects = []
    for sprite, pivot in zip(sprites_list, relative_pivots):
        sprite_rects.append(SpriteRect(
            x := pivot["x"] - max_pivot["x"],
            y := pivot["-y"] - max_pivot["-y"],
            sprite.rect.width + max_pivot["-x"] - pivot["-x"] - x,
            sprite.rect.height + max_pivot["y"] - pivot["y"] - y,
        ))

    return sprite_rects


def get_adjusted_sprites_to_rect(image_rect: Iterable[tuple[Image, SpriteRect]]) -> list[Image]:
    sprites_list = []
    for img, rect in image_rect:
        sprite = crop_image_rect_left_top(img, rect)
        sprites_list.append(sprite)
    return sprites_list


def get_anim_sprites_ready(anim: AnimationData) -> list[Image]:
    return get_adjusted_sprites_to_rect((img, rect) for img, rect, sprite_name in anim.get_sprites_iter())


def apply_tint(image: Image, tint_color: tuple[int, int, int]) -> Image:
    img = image.copy().convert('RGBA')
    pixels = img.load()

    width, height = img.size

    for x in range(width):
        for y in range(height):
            r, g, b, a = pixels[x, y]

            r = int(r * tint_color[0] / 255)
            g = int(g * tint_color[1] / 255)
            b = int(b * tint_color[2] / 255)

            pixels[x, y] = (r, g, b, a)

    return img


def make_image_black(_image: Image, threshold: int = 10) -> Image:
    image = _image.copy()
    pixdata = image.load()
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            if pixdata[x, y][3] > threshold:
                pixdata[x, y] = (0, 0, 0, 255)
            else:
                pixdata[x, y] = (0,)*4
    return image

if __name__ == "__main__":
    pass
    # (255, 170, 255) (136,136, 238)
