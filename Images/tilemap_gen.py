from tkinter.messagebox import showerror

import yaml
import json
import os
import re
from unityparser import UnityDocument
from PIL import Image, ImageFont, ImageDraw
from PIL import ImageOps

__loaded_sprites = dict()
def __get_sprite(image: Image, internal_id: int, meta: dict):
    image_key = str(image)
    if image_key not in __loaded_sprites:
        __loaded_sprites.update({
            image_key: dict()
        })

    if internal_id not in __loaded_sprites[image_key]:
        sprite_data = meta.get(internal_id)

        if not sprite_data:
            print(internal_id)
            return None

        rect = sprite_data["rect"]
        sx, sy = image.size
        im_crop = image.crop((rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

        __loaded_sprites[image_key].update({
            internal_id: im_crop
        })

    return __loaded_sprites[image_key][internal_id]


def gen_tilemap(path: str, assets_files: list, func_get_meta=None):
    p_dir, p_file = os.path.split(path)
    this_dir, this_file = os.path.split(__file__)


    print(f"Started {p_file} parsing")
    doc = UnityDocument.load_yaml(path)
    doc.file_path = None
    print(f"Ended {p_file} Started")

    tilemaps = doc.filter(class_names=("Tilemap",), attributes=("m_Tiles",))
    if not tilemaps:
        showerror("Error", f"Not found any tilemap for {p_file}.")
        return

    name = doc.entry.m_Name
    texture = f"{name}TexturePacked"

    def filter_assets(x):
        name_low = x.name.lower()
        texture_low = texture.lower()
        return name_low.startswith(f"{texture_low}") and name_low.endswith(f".png.meta")

    metas = list(filter(filter_assets, assets_files))

    if not metas:
        showerror("Error", f"{texture} not found for {p_file}.")
        return

    def dir_key(x):
        try:
            return int(x.name.split("_")[-1])
        except ValueError:
            return -1

    metas = sorted(metas, key=dir_key)
    print(metas)
    meta_file = metas[-1]

    meta, image = func_get_meta(*os.path.split(meta_file), is_internal_id=True)

    size_tile_x, size_tile_y = 32, 32

    save_folder = f"{this_dir}/Generated/tilemaps"
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    size_map_x, size_map_y = 0, 0
    for tilemap in tilemaps:
        _size = tilemap.m_Size
        size_map_x = max(size_map_x, int(_size['x']))
        size_map_y = max(size_map_y, int(_size['y']))

    im_map = Image.new(mode="RGBA", size=(size_map_x * size_tile_x, size_map_y * size_tile_y))
    for tilemap in tilemaps:
        # _origin = tilemap.m_Origin
        # origin_x, origin_y = int(_origin['x']), int(_origin['y'])

        tile_sprite_array = list(map(lambda x: int(x["m_Data"]["fileID"]), tilemap.m_TileSpriteArray))
        tile_matrix_array = list(map(lambda x: { k: float(v) for k,v in x["m_Data"].items() }, tilemap.m_TileMatrixArray))
        tiles = map(lambda x: {
            "pos": { k: int(v) for k, v in x["first"].items() },
            "tile_index": int(x["second"]["m_TileIndex"]),
            "matrix_index": int(x["second"]["m_TileMatrixIndex"])
        }, tilemap.m_Tiles)

        for tile in tiles:
            tile_index = tile_sprite_array[tile["tile_index"]]
            sprite = __get_sprite(image, tile_index, meta)

            matrix = tile_matrix_array[tile["matrix_index"]]
            if matrix["e00"] < 0:
                sprite = ImageOps.mirror(sprite)

            if matrix["e11"] < 0:
                sprite = ImageOps.flip(sprite)

            im_map.alpha_composite(sprite, (tile['pos']['x'] * size_tile_x, abs(tile['pos']['y']) * size_tile_y))

    save_file = p_file.replace(".prefab", "")
    im_map.save(f"{save_folder}/{save_file}.png")

    print(f"Done {p_file}")