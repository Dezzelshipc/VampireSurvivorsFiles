import itertools
from pathlib import Path
from tkinter.messagebox import showerror, askyesno

from PIL.Image import Image, new as image_new

from Source.Config.config import Config
from Source.Utility.constants import IMAGES_FOLDER, GENERATED, TILEMAPS, PROGRESS_BAR_FUNC_TYPE
from Source.Utility.image_functions import affine_transform, crop_image_rect_left_bot
from Source.Data.meta_data import MetaData, MetaDataHandler
from Source.Utility.multirun import run_multiprocess, run_concurrent_sync
from Source.Utility.special_classes import Objectless
from Source.Utility.sprite_data import SpriteData, SpriteRect
from Source.Utility.timer import Timeit
from Source.Utility.unityparser2 import UnityDoc, UnityYAMLEntry
from Source.Utility.utility import CheckBoxes, write_in_file_end, clear_file


class Tilemap:
    def __init__(self, doc: UnityYAMLEntry):
        self.m_Size = doc.get("m_Size")
        self.m_TileMatrixArray = doc.get("m_TileMatrixArray")
        self.m_TileSpriteArray = doc.get("m_TileSpriteArray")
        self.m_Tiles = doc.get("m_Tiles")

    def extend_tilemap(self, other: "Tilemap"):
        self.m_Tiles.extend(other.m_Tiles)

    @staticmethod
    def get_size_tile() -> tuple[int, int]:
        return 32, 32


class TilemapDataHandler(Objectless):
    loaded_prefabs: dict[Path, tuple[list[Tilemap | None], int]] = dict()


def __resize_sprite_for_tile(image: Image, sprite_data: SpriteData, size_tile: tuple[int, int]) -> Image:
    shift_x = int(sprite_data.rect.width * sprite_data.pivot.x)
    shift_y = int(sprite_data.rect.height * sprite_data.pivot.y)

    rect = SpriteRect(shift_x, shift_y, size_tile[0], size_tile[1])
    return crop_image_rect_left_bot(image, rect)


def __load_unity_document(path: Path) -> tuple[list[Tilemap | None], int]:
    doc = UnityDoc.yaml_parse_file_smart(path, lambda x: "Tilemap:" in x)
    tilemaps = [Tilemap(tilemap) for tilemap in doc.entries]
    return tilemaps, len(tilemaps)


def __create_tilemap_image(tilemap: Tilemap, new_image: Image, data_by_guid: dict[str: MetaData],
                           save_path: Path) -> Image:
    size_tile_x, size_tile_y = Tilemap.get_size_tile()

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

    return new_image


def __save_image(image: Image, path: Path) -> None:
    image.save(path)


def gen_tilemap(path: Path, __is_full_auto=True,
                func_progress_bar_set_percent: PROGRESS_BAR_FUNC_TYPE = lambda c, t: 0) -> Path | None:
    p_file = path.name
    save_file = path.with_suffix("").name
    save_folder = Path(IMAGES_FOLDER, GENERATED, TILEMAPS, save_file)

    if path not in TilemapDataHandler.loaded_prefabs:
        _text = path.read_text(encoding="UTF-8")
        count_layers = _text.count("Tilemap:")
        if not count_layers:
            showerror("Error", f"Not found any tilemap for {p_file}.")
            return None
    else:
        count_layers = TilemapDataHandler.loaded_prefabs[path][1]

    is_proceed = askyesno("Generation",
                          f"Found tilemap for {p_file}.\nDo you want to generate it?") if __is_full_auto else True

    if not is_proceed:
        return None

    if __is_full_auto:
        exclude_cbs = CheckBoxes(range(count_layers),
                                 title="Layers to exclude",
                                 label="Select layers to exclude in generation")
        exclude_cbs.wait_window()
        exclude_data = exclude_cbs.return_data
        exclude_layers = set(itertools.compress(range(count_layers), exclude_data))
    else:
        exclude_layers = set()

    print(f"Multiprocessing: {Config.get_multiprocessing()}")
    print(f"Excluded layers: {exclude_layers}")

    if path not in TilemapDataHandler.loaded_prefabs:
        print(f"Started {p_file} parsing")
        timeit = Timeit()
        TilemapDataHandler.loaded_prefabs.update({
            path: __load_unity_document(path)
        })
        print(f"Finished {p_file} parsing ({timeit:.2f} sec)")
    else:
        print(f"Already parsed {p_file}")

    tilemaps, _ = TilemapDataHandler.loaded_prefabs[path]

    guid_set = {sprite["m_Data"]["guid"] for tilemap in tilemaps for sprite in tilemap.m_TileSpriteArray}

    print(f"Required guids: {guid_set}")

    meta_data = MetaDataHandler.get_meta_dict_by_guid_set(guid_set)

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

    size_tile_x, size_tile_y = Tilemap.get_size_tile()

    def get_transparent_image():
        return image_new(mode="RGBA", size=(size_map_x * size_tile_x, size_map_y * size_tile_y))

    total_map_size = size_map_x * size_map_y
    is_concurrent = total_map_size < 100_000
    print(f"Tilemap size: x={size_map_x}, y={size_map_y}; total={total_map_size}, {is_concurrent=}")

    args_create_tilemap = (
        (tilemap, get_transparent_image(), meta_data, save_folder / f"{save_file}-Layer-{i}.png")
        for i, tilemap in enumerate(tilemaps)
    )

    tilemap_layers = run_multiprocess(__create_tilemap_image, args_create_tilemap,
                                      is_multiprocess=False, is_generator=not is_concurrent)

    if is_concurrent:
        args_save_tilemap_layers = (
            (tilemap_layer, save_folder / f"{save_file}-Layer-{i}.png")
            for i, tilemap_layer in enumerate(tilemap_layers)
        )
        run_concurrent_sync(__save_image, args_save_tilemap_layers)

    print(f"Finished generation for tilemap layers {p_file} ({timeit:.2f} sec)")

    print(f"Started composing layers for {p_file}")
    timeit = Timeit()

    im_map = get_transparent_image()

    if is_concurrent:
        save_composite = []
        for i, layer in enumerate(tilemap_layers):
            func_progress_bar_set_percent(i, count_layers - 1)

            if i in exclude_layers:
                continue
            im_map.alpha_composite(layer)
            save_composite.append((im_map.copy(), save_folder / f"{save_file}-{i}.png"))

        run_concurrent_sync(__save_image, save_composite)
    else:
        for i, layer in enumerate(tilemap_layers):
            func_progress_bar_set_percent(i, count_layers - 1)

            __save_image(layer.copy(), save_folder / f"{save_file}-Layer-{i}.png")
            if i in exclude_layers:
                continue
            im_map.alpha_composite(layer)
            __save_image(im_map.copy(), save_folder / f"{save_file}-{i}.png")

    print(f"Finished generation for tilemap {p_file} ({timeit:.2f} sec)")

    return save_folder


if __name__ == "__main__":
    def __test():
        name = "Collab1_Tileset1_V6"
        tile_id = 21303880

        from Source.Data.meta_data import MetaDataHandler
        meta = MetaDataHandler.get_meta_by_name(name, is_multiprocess=False)
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


    # __test()

    def __profile():
        from tkinter import filedialog as fd
        from Config.config import DLCType
        full_path = fd.askopenfilename(
            title='Select prefab file of tilemap',
            initialdir=Config.get_assets_dir(DLCType.VS),
            filetypes=[('Prefab', '*.prefab')]
        )
        if not full_path:
            return
        full_path = Path(full_path)

        import cProfile
        print("Started")
        with cProfile.Profile() as pr:
            gen_tilemap(full_path, False)
            pr.print_stats('time')

    # __profile()
