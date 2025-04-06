import itertools
from math import log2, pow, ceil
from pathlib import Path
from tkinter.messagebox import showerror, askyesno

from PIL import Image
from unityparser import UnityDocument

from Config.config import Config
from Utility.image_functions import affine_transform
from Utility.meta_data import get_meta_dict_by_guid_set, MetaData
from Utility.singleton import Singleton
from Utility.sprite_data import SpriteData
from Utility.timer import Timeit
from Utility.utility import CheckBoxes, run_multiprocess, write_in_file_end, clear_file

THIS_FOLDER = Path(__file__).parent


class TilemapDataHandler(metaclass=Singleton):
    def __init__(self):
        self.config = Config()

        self.loaded_prefabs: dict[Path, tuple[list[Tilemap | None], int]] = dict()

        self.size_tile = self.get_size_tile()

    @staticmethod
    def get_size_tile() -> tuple[int, int]:
        return 32, 32


class Tilemap:
    def __init__(self, doc):
        self.m_Size = doc.m_Size
        self.m_TileMatrixArray = doc.m_TileMatrixArray
        self.m_TileSpriteArray = doc.m_TileSpriteArray
        self.m_Tiles = doc.m_Tiles

    def extend_tilemap(self, other):
        self.m_Tiles.extend(other.m_Tiles)


def __resize_sprite_for_tile(image: Image, sprite_data: SpriteData, size_tile: tuple[int, int]) -> Image:
    im_crop = image.copy()

    shift_x = int(sprite_data.rect.width * sprite_data.pivot.x)
    shift_y = int(sprite_data.rect.height * sprite_data.pivot.y)

    return im_crop.crop(
        (shift_x, im_crop.height - shift_y - size_tile[1], shift_x + size_tile[0], im_crop.height - shift_y))


def __split_tilemap_prefab(tilemap: list[str]) -> list[list[str]]:
    ref_count = 0
    for line in reversed(tilemap):
        if "m_RefCount" in line:
            ref_count = int(line.split(":")[-1])
            break

    # print(ref_count)
    max_count = 20_000
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


def __load_UnityDocument(path: Path) -> tuple[list[Tilemap | None], int]:
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

        parts_dir = THIS_FOLDER / "Generated/_Tilemaps/_Split for generation"
        parts_dir.mkdir(parents=True, exist_ok=True)

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

        parts_dir.rmdir()

        return out_list, count_layers


def __load_UnityDocument_part(header: list, tilemap: list, index_prefab: int, index_part: int, parts_dir: Path) -> \
        tuple[Tilemap, int, int]:
    text = "".join(header) + "".join(tilemap)

    path_part = parts_dir / f"Prefab-{index_prefab}-{index_part}.prefab"
    with open(path_part, "w") as fp:
        fp.write(text)

    doc = UnityDocument.load_yaml(path_part)
    path_part.unlink()
    return Tilemap(doc.entry), index_prefab, index_part


def __create_Tilemap_image(tilemap: Tilemap, new_image: Image, data_by_guid: dict[str: MetaData],
                           save_path: Path) -> Image:
    size_tile_x, size_tile_y = TilemapDataHandler.get_size_tile()

    tile_sprite_array = [(int(x["m_Data"]["fileID"]), x["m_Data"]["guid"]) for x in tilemap.m_TileSpriteArray]
    tile_matrix_array = [{k: float(v) for k, v in x["m_Data"].items()} if int(x["m_RefCount"]) > 0 else {} for x in
                         tilemap.m_TileMatrixArray]
    tiles = ({
        "pos": {k: int(v) for k, v in tile["first"].items()},
        "tile_index": int(tile["second"]["m_TileIndex"]),
        "matrix_index": int(tile["second"]["m_TileMatrixIndex"])
    } for tile in tilemap.m_Tiles)

    log_list = []
    for tile in tiles:
        tile_inner_id, texture_guid = tile_sprite_array[tile["tile_index"]]

        data: MetaData = data_by_guid.get(texture_guid)
        sprite_data = data.data_id.get(tile_inner_id)
        sprite = sprite_data.sprite

        if not sprite:
            line = f"Sprite error: {texture_guid=} {tile_inner_id=}\n"
            log_list.append(line)
            continue

        sprite = __resize_sprite_for_tile(sprite, sprite_data, (size_tile_x, size_tile_y))

        matrix = tile_matrix_array[tile["matrix_index"]]
        if matrix["e00"] != 1 or matrix["e11"] != 1:
            affine = (matrix["e00"], matrix["e10"], matrix["e01"], matrix["e11"])
            sprite = affine_transform(sprite, affine)

        new_image.alpha_composite(sprite, (tile['pos']['x'] * size_tile_x, abs(tile['pos']['y']) * size_tile_y))

    write_in_file_end(save_path.with_name("errors.log"), log_list)
    __save_image(new_image, save_path)

    return new_image


def __save_image(image: Image, path: Path) -> None:
    image.save(path)


def gen_tilemap(path: Path) -> Path | None:
    handler = TilemapDataHandler()

    p_file = path.name
    save_file = path.with_suffix("").name
    save_folder = Path(THIS_FOLDER, "Generated/_Tilemaps", save_file)

    if path not in handler.loaded_prefabs:
        _text = path.read_text(encoding="UTF-8")
        count_layers = _text.count("Tilemap:")
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
    exclude_layers = set(itertools.compress(range(count_layers), exclude_data))

    print(f"Multiprocessing: {handler.config.get_multiprocessing()}")
    print(f"Excluded layers: {exclude_layers}")

    if path not in handler.loaded_prefabs:
        print(f"Started {p_file} parsing")
        timeit = Timeit()
        handler.loaded_prefabs.update({
            path: __load_UnityDocument(path)
        })
        print(f"Finished {p_file} parsing ({timeit:.2f} sec)")
    else:
        print(f"Already parsed {p_file}")

    tilemaps, _ = handler.loaded_prefabs[path]

    guid_set = {sprite["m_Data"]["guid"] for tilemap in tilemaps for sprite in tilemap.m_TileSpriteArray}

    print(f"Required guids: {guid_set}")

    meta_data = get_meta_dict_by_guid_set(guid_set)

    for md in meta_data.values():
        md.init_sprites()

    save_folder.mkdir(parents=True, exist_ok=True)

    print(f"Started generating tilemap layers for {p_file}")
    clear_file(save_folder / "errors.log")
    timeit = Timeit()

    size_map_x, size_map_y = 0, 0
    for tilemap in tilemaps:
        _size = tilemap.m_Size
        size_map_x = max(size_map_x, int(_size['x']))
        size_map_y = max(size_map_y, int(_size['y']))

    size_tile_x, size_tile_y = handler.size_tile
    im_map = Image.new(mode="RGBA", size=(size_map_x * size_tile_x, size_map_y * size_tile_y))

    args_create_tilemap = (
        (tilemap, im_map.copy(), meta_data, save_folder / f"{save_file}-Layer-{i}.png")
        for i, tilemap in enumerate(tilemaps)
    )

    tilemap_layers = run_multiprocess(__create_Tilemap_image, args_create_tilemap, is_multiprocess=False)

    print(f"Finished generation for tilemap layers {p_file} ({timeit:.2f} sec)")

    print(f"Started composing layers for {p_file}")
    timeit = Timeit()

    for i, layer in enumerate(tilemap_layers):
        if i in exclude_layers:
            continue
        im_map.alpha_composite(layer)
        __save_image(im_map, save_folder / f"{save_file}-{i}.png")

    print(f"Finished generation for tilemap {p_file} ({timeit:.2f} sec)")

    return save_folder


if __name__ == "__main__":
    def __test(name: str, tile_id: int):
        from Utility.meta_data import get_meta_by_name, MetaDataHandler
        MetaDataHandler()
        meta = get_meta_by_name(name, is_multiprocess=False)
        meta.init_sprites()

        meta = meta.data_id

        size_tile = (32,) * 2
        sprite_data = meta.get(tile_id)
        sprite = sprite_data.sprite
        if not sprite:
            return

        transform_list = ((1, 1), (1, -1), (-1, 1), (-1, -1))

        save_folder = Path("./Generated/_Tilemaps/_Test")
        save_folder.mkdir(parents=True, exist_ok=True)
        sprite.save(save_folder.joinpath(f"{tile_id}.png"))

        for i, (x1, x2) in enumerate(transform_list):
            aff1 = (x1, 0, 0, x2)
            aff2 = (0, x1, x2, 0)

            sprite1 = sprite.copy()
            sprite2 = sprite.copy()

            sprite1 = __resize_sprite_for_tile(sprite1, sprite_data, size_tile)
            sprite2 = __resize_sprite_for_tile(sprite2, sprite_data, size_tile)

            sprite1 = affine_transform(sprite1, aff1)
            sprite2 = affine_transform(sprite2, aff2)

            sprite1.save(save_folder.joinpath(f"{tile_id}-1_{i}.png"))
            sprite2.save(save_folder.joinpath(f"{tile_id}-2_{i}.png"))


    texture = "Collab1_Tileset1_V6"
    t_id = 21303880
    __test(texture, t_id)
