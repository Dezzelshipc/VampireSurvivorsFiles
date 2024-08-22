from tkinter.messagebox import showerror

import yaml
import json
import os
import re
from unityparser import UnityDocument
from PIL import Image, ImageFont, ImageDraw
from PIL import ImageOps

__loaded_prefabs = dict()
__loaded_sprites = dict()


def __get_sprite(spritesheet: Image, internal_id: int, meta: dict, size_tile: tuple):
    image_key = str(spritesheet)
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
        sx, sy = spritesheet.size
        im_crop = spritesheet.crop(
            (rect['x'], sy - rect['y'] - rect['height'], rect['x'] + rect['width'], sy - rect['y']))

        shift_x = int(sprite_data['rect']['width'] * sprite_data['pivot']['x'])
        shift_y = int(sprite_data['rect']['height'] * sprite_data['pivot']['y'])

        im_crop = im_crop.crop(
            (shift_x, im_crop.height - shift_y - size_tile[1], size_tile[0] - shift_x, im_crop.height - shift_y))

        __loaded_sprites[image_key].update({
            internal_id: im_crop
        })

    return __loaded_sprites[image_key][internal_id]


def gen_tilemap(path: str, func_get_meta=None, func_path_by_guid=None):
    p_dir, p_file = os.path.split(path)
    this_dir, this_file = os.path.split(__file__)

    if path not in __loaded_prefabs:
        print(f"Started {p_file} parsing")
        doc = UnityDocument.load_yaml(path)
        doc.file_path = None
        __loaded_prefabs.update({
            path: doc
        })
        print(f"Ended {p_file} parsing")

    prefab = __loaded_prefabs[path]

    tilemaps = prefab.filter(class_names=("Tilemap",), attributes=("m_Tiles",))
    if not tilemaps:
        showerror("Error", f"Not found any tilemap for {p_file}.")
        return

    guid_set = set()
    for tilemap in tilemaps:
        array = map(lambda x: x["m_Data"]["guid"], tilemap.m_TileSpriteArray)
        guid_set.update(array)

    print(guid_set)

    texture_paths_meta = { guid: func_path_by_guid(guid) for guid in guid_set }
    print(texture_paths_meta)

    if None in texture_paths_meta.items():
        showerror("Error", f"Packed texture not found for {p_file}. (guids: {texture_paths_meta})")
        return

    print(f"Started generating tilemap for {p_file}")

    textures = {
        guid: func_get_meta(*os.path.split(path), is_internal_id=True) for guid, path in texture_paths_meta.items()
    }

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
        tile_sprite_array = list(map(lambda x: (int(x["m_Data"]["fileID"]), x["m_Data"]["guid"]) , tilemap.m_TileSpriteArray))
        tile_matrix_array = list(
            map(lambda x: {k: float(v) for k, v in x["m_Data"].items()}, tilemap.m_TileMatrixArray))
        tiles = map(lambda x: {
            "pos": {k: int(v) for k, v in x["first"].items()},
            "tile_index": int(x["second"]["m_TileIndex"]),
            "matrix_index": int(x["second"]["m_TileMatrixIndex"])
        }, tilemap.m_Tiles)

        for tile in tiles:
            tile_index, texture_guid = tile_sprite_array[tile["tile_index"]]

            meta, image = textures[texture_guid]
            sprite = __get_sprite(image, tile_index, meta, (size_tile_x, size_tile_y))

            matrix = tile_matrix_array[tile["matrix_index"]]
            if matrix["e00"] < 0:
                sprite = ImageOps.mirror(sprite)

            if matrix["e11"] < 0:
                sprite = ImageOps.flip(sprite)

            im_map.alpha_composite(sprite, (tile['pos']['x'] * size_tile_x, abs(tile['pos']['y']) * size_tile_y))

    save_file = p_file.replace(".prefab", "")
    im_map.save(f"{save_folder}/{save_file}.png")

    print(f"Generation for tilemap {p_file} ended")
