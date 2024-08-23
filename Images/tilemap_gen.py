from tkinter.messagebox import showerror, askyesno

import os

from unityparser import UnityDocument
from PIL import Image, ImageOps

__loaded_prefabs = dict()
__loaded_sprites = dict()


def __get_sprite(spritesheet: Image, internal_id: int, meta: dict, size_tile: tuple) -> Image:
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


def __affine_transform(image: Image, matrix: tuple) -> Image:
    a, b, c, d, e, f = matrix

    if a + b < 0:
        image = ImageOps.mirror(image)

    if d + e < 0:
        image = ImageOps.flip(image)

    if b or d:
        image = image.rotate(-90)
        image = ImageOps.flip(image)

    return image


def gen_tilemap(path: str, func_get_meta=None, func_path_by_guid=None):
    p_dir, p_file = os.path.split(path)
    save_file = p_file.replace(".prefab", "")
    this_dir, this_file = os.path.split(__file__)

    if path not in __loaded_prefabs:
        is_found_tilemap = False
        with open(path, "r") as f:
            for line in f.readlines():
                if "Tilemap" in line:
                    is_found_tilemap = True
                    break

        if not is_found_tilemap:
            showerror("Error", f"Not found any tilemap for {p_file}.")
            return

    is_proceed = askyesno("Generation", f"Found tilemap for {p_file}.\nDo you want to generate it?")

    if not is_proceed:
        return

    if path not in __loaded_prefabs:
        print(f"Started {p_file} parsing")
        doc = UnityDocument.load_yaml(path)
        doc.file_path = None
        __loaded_prefabs.update({
            path: doc
        })
        print(f"Finished {p_file} parsing")
    else:
        print(f"Already parsed {p_file}")

    prefab = __loaded_prefabs[path]

    tilemaps = prefab.filter(class_names=("Tilemap",), attributes=("m_Tiles",))
    if not tilemaps:
        showerror("Error", f"Not found any tilemap for {p_file}.")
        return

    guid_set = set()
    for tilemap in tilemaps:
        array = map(lambda x: x["m_Data"]["guid"], tilemap.m_TileSpriteArray)
        guid_set.update(array)

    print(f"Required guids: {guid_set}")

    texture_paths_meta = {guid: func_path_by_guid(guid) for guid in guid_set}
    print(texture_paths_meta)

    if None in texture_paths_meta.items():
        showerror("Error", f"Packed texture not found for {p_file}. (guids: {texture_paths_meta})")
        return

    print(f"Started generating tilemap for {p_file}")

    textures = {
        guid: func_get_meta(*os.path.split(path), is_internal_id=True) for guid, path in texture_paths_meta.items()
    }

    size_tile_x, size_tile_y = 32, 32

    save_folder = f"{this_dir}/Generated/_Tilemaps/{save_file}/"
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    size_map_x, size_map_y = 0, 0
    for tilemap in tilemaps:
        _size = tilemap.m_Size
        size_map_x = max(size_map_x, int(_size['x']))
        size_map_y = max(size_map_y, int(_size['y']))

    im_map = Image.new(mode="RGBA", size=(size_map_x * size_tile_x, size_map_y * size_tile_y))
    for i, tilemap in enumerate(tilemaps):
        tile_sprite_array = list(
            map(lambda x: (int(x["m_Data"]["fileID"]), x["m_Data"]["guid"]), tilemap.m_TileSpriteArray))
        tile_matrix_array = list(
            map(lambda x: {k: int(float(v)) for k, v in x["m_Data"].items()}, tilemap.m_TileMatrixArray))
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
            if matrix["e00"] != 1 or matrix["e11"] != 1:
                affine = (matrix["e00"], matrix["e01"], matrix["e02"], matrix["e10"], matrix["e11"], matrix["e12"])
                affine = (matrix["e00"], matrix["e10"], matrix["e20"], matrix["e01"], matrix["e11"], matrix["e21"])
                sprite = __affine_transform(sprite, affine)

            im_map.alpha_composite(sprite, (tile['pos']['x'] * size_tile_x, abs(tile['pos']['y']) * size_tile_y))

        im_map.save(f"{save_folder}/{save_file}-{i}.png")

    im_map.save(f"{save_folder}/{save_file}.png")

    print(f"Generation for tilemap {p_file} finished")

    return save_folder


def __test(path, func_get_meta):
    tile_id = 21300000

    meta, image = func_get_meta(*os.path.split(path), is_internal_id=True)

    sprite = __get_sprite(image, tile_id, meta, (32, 32))

    transform_list = ((1, 1), (1, -1), (-1, 1), (-1, -1))

    save_folder = "./Generated/_Test"
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    for i, (x1, x2) in enumerate(transform_list):
        aff1 = (x1, 0, 0, 0, x2, 0)
        aff2 = (0, x1, 0, x2, 0, 0)

        sprite1 = __affine_transform(sprite, aff1)
        sprite2 = __affine_transform(sprite, aff2)

        sprite1.save(f"{save_folder}/{tile_id}-1_{i}.png")
        sprite2.save(f"{save_folder}/{tile_id}-2_{i}.png")


if __name__ == "__main__":
    from unpacker import Unpacker

    unp = Unpacker()
    all_assets = unp.get_assets_meta_files()

    texture = "Atlas_LibraryTexturePacked_1_0"

    def filter_assets(x):
        name_low = x.name.lower()
        texture_low = texture.lower()
        return name_low.startswith(f"{texture_low}") and name_low.endswith(f"{texture_low}.png.meta")

    meta_path = list(filter(filter_assets, all_assets))[0]
    print(meta_path)

    __test(meta_path, unp.get_meta_by_full_path)
