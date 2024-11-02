from tkinter.messagebox import showerror, askyesno

import os
from math import log2, pow, ceil
import time
from unityparser import UnityDocument
from PIL import Image, ImageOps

from Config.config import Config
from Utility.singleton import Singleton
from Utility.utility import CheckBoxes, run_multiprocess
from Utility.meta_data import MetaData, get_meta_dict_by_guid_set, get_meta_by_guid_set
from Utility.image_functions import crop_image_rect, resize_image

this_dir, this_file = os.path.split(__file__)


class TilemapDataHandler(metaclass=Singleton):
    def __init__(self):
        self.config = Config()

        self.loaded_prefabs = dict()
        self.loaded_sprites = dict()
        self.loaded_textures = dict()

        self.size_tile = self.get_size_tile()

    @staticmethod
    def get_size_tile():
        return 32, 32


def __get_sprite(spritesheet: Image, sprite_data: dict, size_tile: tuple) -> Image:

    if not sprite_data:
        return None

    im_crop = crop_image_rect(spritesheet, sprite_data["rect"])

    shift_x = int(sprite_data['rect']['width'] * sprite_data['pivot']['x'])
    shift_y = int(sprite_data['rect']['height'] * sprite_data['pivot']['y'])

    im_crop = im_crop.crop(
        (shift_x, im_crop.height - shift_y - size_tile[1], size_tile[0] - shift_x, im_crop.height - shift_y))

    return im_crop


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


def __split_tilemap_prefab(tilemap: list):
    ref_count = 0
    for line in reversed(tilemap):
        if "m_RefCount" in line:
            ref_count = int(line.split(":")[-1])
            break

    # print(ref_count)
    max_count = 10_000
    if not ref_count or ref_count < max_count:
        return [tilemap]

    last_header_i = tilemap.index("  m_Tiles:\n")
    first_footer_i = tilemap.index("  m_AnimatedTiles: {}\n")

    header = tilemap[:last_header_i + 1]
    footer = tilemap[first_footer_i:]
    content = tilemap[last_header_i + 1:first_footer_i]

    buckets = int(pow(2, ceil(log2(ref_count) - log2(max_count))))
    bucket = ref_count // buckets

    total_index = 0
    split_content = []
    for line in content:
        if "- first" in line:
            if total_index == 0:
                split_content.append([])
            total_index = (total_index + 1) % bucket

        split_content[-1].append(line)

    out_list = []
    for part_content in split_content:
        lst = []
        lst.extend(header)
        lst.extend(part_content)
        lst.extend(footer)
        out_list.append(lst)

    return out_list


def __load_UnityDocument(path):
    with open(path, "r") as fp:
        header = fp.readlines()[:2]
        fp.seek(0)
        line_prev = ""
        list_tilemaps = []
        is_tilemap = False
        for line in fp.readlines():
            split = line.split(":")
            if split[-1] == "\n" and " " not in split[0] or "---" in split[0]:
                is_tilemap = (split[0] == "Tilemap")
                if is_tilemap:
                    list_tilemaps.append([line_prev])

            if is_tilemap:
                list_tilemaps[-1].append(line)

            line_prev = line

        count_layers = len(list_tilemaps)
        list_part_tilemaps = run_multiprocess(__split_tilemap_prefab, list_tilemaps, is_many_args=False)

        parts_dir = f"{this_dir}/Generated/_Split for generation"
        if not os.path.exists(parts_dir):
            os.makedirs(parts_dir)

        for file_path in os.scandir(parts_dir):
            os.remove(file_path)

        args_list = ((header, part_tilmap, i, j, parts_dir) for i, part_tilemaps in enumerate(list_part_tilemaps) for
                     j, part_tilmap in enumerate(part_tilemaps))

        processed_parts = run_multiprocess(__load_UnityDocument_part, args_list)
        out_list: list[Tilemap | None] = [None] * count_layers

        # print(processed_parts, count_layers, out_list)
        for part in processed_parts:
            ind = part[1]
            if not out_list[ind]:
                out_list[ind] = part[0]
            else:
                out_list[ind].extend_tilemap(part[0])

        return out_list, count_layers


class Tilemap:
    def __init__(self, doc):
        self.m_Size = doc.m_Size
        self.m_TileMatrixArray = doc.m_TileMatrixArray
        self.m_TileSpriteArray = doc.m_TileSpriteArray
        self.m_Tiles = doc.m_Tiles

    def extend_tilemap(self, other):
        self.m_Tiles.extend(other.m_Tiles)


def __load_UnityDocument_part(header: list, tilemap: list, index_prefab: int, index_part: int, parts_dir: str) -> (
        Tilemap, int, int):
    text = "".join(header) + "".join(tilemap)

    path_part = f"{parts_dir}/Prefab-{index_prefab}-{index_part}.prefab"
    with open(path_part, "w") as fp:
        fp.write(text)

    doc = UnityDocument.load_yaml(path_part)
    return Tilemap(doc.entry), index_prefab, index_part


def __create_Tilemap_image(tilemap: Tilemap, im_map: Image, textures: dict[str: dict], save_path: str):
    size_tile_x, size_tile_y = TilemapDataHandler.get_size_tile()

    tile_sprite_array = [(int(x["m_Data"]["fileID"]), x["m_Data"]["guid"]) for x in tilemap.m_TileSpriteArray]
    tile_matrix_array = [{k: int(float(v)) for k, v in x["m_Data"].items()} for x in tilemap.m_TileMatrixArray]
    tiles = ({
        "pos": {k: int(v) for k, v in x["first"].items()},
        "tile_index": int(x["second"]["m_TileIndex"]),
        "matrix_index": int(x["second"]["m_TileMatrixIndex"])
    } for x in tilemap.m_Tiles)

    for tile in tiles:
        tile_inner_id, texture_guid = tile_sprite_array[tile["tile_index"]]

        image, data_id = textures.get(texture_guid)
        sprite_data = data_id.get(tile_inner_id)
        sprite = __get_sprite(image, sprite_data, (size_tile_x, size_tile_y))

        if not sprite:
            print(f"Sprite error: {image=} {len(data_id)=} {texture_guid=} {tile_inner_id=} {sprite_data=}")
            continue

        matrix = tile_matrix_array[tile["matrix_index"]]
        if matrix["e00"] != 1 or matrix["e11"] != 1:
            affine = (matrix["e00"], matrix["e10"], matrix["e20"], matrix["e01"], matrix["e11"], matrix["e21"])
            sprite = __affine_transform(sprite, affine)

        im_map.alpha_composite(sprite, (tile['pos']['x'] * size_tile_x, abs(tile['pos']['y']) * size_tile_y))

    __save_image(im_map, save_path)

    return im_map


def __save_image(image: Image, path: str):
    image.save(path)


def gen_tilemap(path: str):
    handler = TilemapDataHandler()

    p_dir, p_file = os.path.split(path)
    save_file = p_file.replace(".prefab", "")
    save_folder = f"{this_dir}/Generated/_Tilemaps/{save_file}/"

    if path not in handler.loaded_prefabs:
        with open(path, "r") as f:
            count_layers = f.readlines().count("Tilemap:\n")
            if not count_layers:
                showerror("Error", f"Not found any tilemap for {p_file}.")
                return
    else:
        count_layers = handler.loaded_prefabs[path][1]

    is_proceed = askyesno("Generation", f"Found tilemap for {p_file}.\nDo you want to generate it?")

    if not is_proceed:
        return

    exclude_cbs = CheckBoxes(range(count_layers),
                             title="Layers to exclude",
                             label="Select layers to exclude in generation")
    exclude_cbs.wait_window()
    exclude_data = exclude_cbs.return_data
    exclude_layers = [i for i in range(count_layers) if exclude_data[i]]

    print(f"Multiprocessing: {handler.config["MULTIPROCESSING"]}")
    print(f"Excluded layers: {exclude_layers}")

    if path not in handler.loaded_prefabs:
        print(f"Started {p_file} parsing")
        time_start_generation = time.time()
        handler.loaded_prefabs.update({
            path: __load_UnityDocument(path)
        })
        print(f"Finished {p_file} parsing ({round(time.time() - time_start_generation, 2)} sec)")
    else:
        print(f"Already parsed {p_file}")

    tilemaps, _ = handler.loaded_prefabs[path]

    guid_set = {sprite["m_Data"]["guid"] for tilemap in tilemaps for sprite in tilemap.m_TileSpriteArray}

    print(f"Required guids: {guid_set}")

    meta_datas = get_meta_by_guid_set(guid_set)

    # TODO: texture splitter before creating tilemap
    textures = {
        meta_data.guid: (meta_data.image, meta_data.data_id) for meta_data in meta_datas
    }

    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    print(f"Started generating tilemap for {p_file}")
    time_start_generation = time.time()

    size_tile_x, size_tile_y = handler.size_tile

    size_map_x, size_map_y = 0, 0
    for tilemap in tilemaps:
        _size = tilemap.m_Size
        size_map_x = max(size_map_x, int(_size['x']))
        size_map_y = max(size_map_y, int(_size['y']))

    im_map = Image.new(mode="RGBA", size=(size_map_x * size_tile_x, size_map_y * size_tile_y))

    args_create_tilemap = (
        (tilemap, im_map.copy(), textures, f"{save_folder}/{save_file}-Layer-{i}.png")
        for i, tilemap in enumerate(tilemaps)
    )

    tilemap_layers = run_multiprocess(__create_Tilemap_image, args_create_tilemap)

    print(f"Started composing layers for {p_file}")

    composed_tilemaps = []
    for i, layer in enumerate(tilemap_layers):
        if i in exclude_layers:
            continue
        im_map.alpha_composite(layer)
        composed_tilemaps.append(im_map.copy())

        # __save_image(im_map, f"{save_folder}/{save_file}-{i}.png")

    args_composed = ((image, f"{save_folder}/{save_file}-{i}.png") for i, image in enumerate(composed_tilemaps))

    run_multiprocess(__save_image, args_composed)

    print(f"Finished generation for tilemap {p_file} ({round(time.time() - time_start_generation, 2)} sec)")

    return save_folder


def __test(path, func_get_meta):
    tile_id = 21300000

    meta, image = func_get_meta(*os.path.split(path), is_internal_id=True)

    sprite = __get_sprite(image, meta.get(tile_id), (32, 32))

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
