import re

from PIL import Image, ImageOps
from PIL.Image import Resampling
from matplotlib.animation import Animation

from Utility.sprite_data import SpriteData, SpriteRect, AnimationData


def crop_image_rect_left_bot(image: Image, rect: SpriteRect | dict) -> Image:
    _rect: SpriteRect = rect if isinstance(rect, SpriteRect) else SpriteRect.from_dict(rect)
    sx, sy = image.size
    return image.crop((_rect.x, sy - _rect.y - _rect.height, _rect.x + _rect.width, sy - _rect.y))


def crop_image_rect_left_top(image: Image, rect: SpriteRect | dict) -> Image:
    _rect: SpriteRect = rect if isinstance(rect, SpriteRect) else SpriteRect.from_dict(rect)
    return image.crop((_rect.x, _rect.y, _rect.width + _rect.x, _rect.height + _rect.y))


def resize_image(image: Image, scale_factor: float) -> Image:
    return image.resize((image.size[0] * scale_factor, image.size[1] * scale_factor), Resampling.NEAREST)


def resize_list_images(images: list[Image], scale_factor: float) -> list[Image]:
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


def get_anim_sprites_ready(anim: AnimationData, scale_factor: int = 1) -> list[Image]:
    sprites_list = []
    for img, rect, sprite_name in anim.get_sprites_iter():
        sprite = crop_image_rect_left_top(img, rect)
        sprite = resize_image(sprite, scale_factor)
        sprites_list.append(sprite)
    return sprites_list


from PIL import Image, ImageColor

from PIL import Image


def apply_tint(image_path, output_path, tint_color):
    """
    Apply tint by manually modifying pixel values.

    Args:
        image_path: Path to the input image
        output_path: Path to save the tinted image
        tint_color: RGB tuple for tint color (e.g., (255, 153, 0))
    """
    img = Image.open(image_path).convert('RGB')
    pixels = img.load()

    # Get image dimensions
    width, height = img.size

    # Process each pixel
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y]

            # Blend with tint color
            r = int(r * tint_color[0] /255 )
            g = int(g * tint_color[1] /255 )
            b = int(b * tint_color[2] /255 )

            pixels[x, y] = (r, g, b)



    img.rotate(180).save(output_path)



if __name__ == "__main__":
    apply_tint(r"",
               r"",
               (255, 170, 255)
               )

    # (136,136, 238)
