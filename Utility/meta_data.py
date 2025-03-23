import sys
import time

from pathlib import Path
from tkinter import Image
from typing import Dict

from unityparser import UnityDocument
from PIL import Image

from Utility.image_functions import crop_image_rect, SpriteRect, SpritePivot
from Utility.singleton import Singleton
from Utility.utility import run_multiprocess
from Config.config import Config, CfgKey


def normalize_str(s: str) -> str:
    return str(s).lower().replace(".png", "").replace(".meta", "")


class MetaDataHandler(metaclass=Singleton):
    def __init__(self):
        self.config = Config()
        self.assets_paths: set[Path] = set()
        self.assets_guid_path = dict()

        self.loaded_assets_meta: dict[str: MetaData] = dict()

    def load_assets_meta_files(self):
        dirs = [self.config[CfgKey.VS].joinpath("Resources", "spritesheets")]
        for f in filter(lambda x: "ASSETS" in x.value, self.config.data):
            p = self.config[f].joinpath("Texture2D")
            if p.exists():
                dirs.append(p)

        files = []
        missing_paths = []
        while dirs:
            this_dir = dirs.pop(0)
            if not this_dir.exists():
                missing_paths.append(this_dir)
                continue

            files.extend(f for f in this_dir.iterdir() if ".meta" in f.suffixes and not f.is_dir())
            dirs.extend(f for f in this_dir.iterdir() if f.is_dir())

        if missing_paths:
            print(f"! Missing paths {missing_paths} while trying to access meta files for images.",
                  file=sys.stderr)

        self.assets_paths.update(map(Path, files))
        print("Loaded meta paths")

        return self

    def load(self):
        if self.assets_guid_path:
            return

        if not self.assets_paths:
            self.load_assets_meta_files()

        print("Started collecting guid of every asset")
        guid_path = run_multiprocess(_get_meta_guid, self.assets_paths, is_many_args=False)
        for entry in guid_path:
            self.assets_guid_path.update(entry)
        print("Finished collecting guid of every asset")

        return self


def _get_meta_guid(path: Path):
    if not path or not path.exists():
        return None

    with open(path, 'r', encoding="UTF-8") as f:
        for line in f.readlines()[:10]:
            key, val = line.split(":")

            if key.strip() == "guid":
                return {val.strip(): path}

            if not val:
                return None


class SpriteData:
    def __init__(self, name, real_name, internal_id, rect, pivot):
        self.name: str = name
        self.real_name: str = real_name
        self.internal_id: int = internal_id
        self.rect: SpriteRect = rect if isinstance(rect, SpriteRect) else SpriteRect.from_dict(rect)
        self.pivot: SpritePivot = pivot if isinstance(pivot, SpritePivot) else SpritePivot.from_dict(pivot)

        self.sprite = None

    def __repr__(self):
        return f"[{self.__class__.__name__}: {self.real_name=} {self.internal_id=} {self.rect} {self.pivot} {self.sprite}]"

    def __getitem__(self, item):
        # SHOULD NOT BE USED NORMALLY
        return self.__getattribute__(item)


class MetaData:
    def __init__(self, name: str, guid: str, image: Image, data_name: Dict[str, SpriteData], data_id: Dict[int, SpriteData]):
        self.name: str = name
        self.guid: str = guid
        self.image: Image = image
        self.data_name: Dict[str, SpriteData] = data_name
        self.data_id: Dict[int, SpriteData] = data_id

        self.__added_sprites = False

    def init_sprites(self) -> None:
        if not self.__added_sprites:
            for entries in self.data_name.values():
                entries.sprite = crop_image_rect(self.image, entries.rect)
                pass

        self.__added_sprites = True

    def __getitem__(self, item):
        # SHOULD NOT BE USED NORMALLY
        return self.__getattribute__(item)


def __get_meta(meta_path: Path) -> MetaData:
    time_start_parsing = time.time()

    meta_path_name = meta_path.name
    print(f"Started parsing {meta_path_name}")
    image_path = meta_path.with_suffix("")
    image = Image.open(image_path)

    doc = UnityDocument.load_yaml(meta_path, try_preserve_types=True)
    entry = doc.entry

    internal_id_to_name_table = entry["TextureImporter"]["internalIDToNameTable"]
    sprites_data = entry["TextureImporter"]["spriteSheet"]["sprites"]

    # if single sprite
    if not internal_id_to_name_table and not sprites_data:
        sprite_sheet = entry["TextureImporter"]["spriteSheet"]
        internal_id = sprite_sheet['internalID']
        internal_id_to_name_table = [{'first': {0: internal_id}}]
        sprites_data = [{
            "name": normalize_str(image_path.stem),
            'real_name': image_path.stem,
            "internalID": internal_id,
            "rect": {
                "x": 0, "y": 0, "width": image.width, "height": image.height
            },
            "pivot": {"x": 0.5, "y": 0.5}
        }]

    prepared_data_name = dict()
    prepared_data_id = dict()
    for i, data_entry in enumerate(sprites_data):
        internal_id = list(internal_id_to_name_table[i]['first'].values())[0]  # not depends on key

        prepared_data_entry = SpriteData(
            name=normalize_str(data_entry['name']),
            real_name=data_entry['name'],
            internal_id=internal_id,
            rect={
                k: float(v) for k, v in data_entry['rect'].items()
            },
            pivot={
                k: float(v) for k, v in data_entry['pivot'].items()
            }
        )

        prepared_data_name.update({
            data_entry['name']: prepared_data_entry
        })
        prepared_data_id.update({
            internal_id: prepared_data_entry
        })

    guid = entry['guid']
    name = normalize_str(meta_path_name)

    print(f"Finished parsing {meta_path_name} [{guid=}] ({time.time() - time_start_parsing:.2f} sec)")

    return MetaData(name, guid, image, prepared_data_name, prepared_data_id)


def get_meta_by_name_set(name_set: set, is_multiprocess=True) -> list[MetaData]:
    normalized_set = {normalize_str(name) for name in name_set}
    handler = MetaDataHandler()
    not_loaded_name_set = {name for name in normalized_set if name not in handler.loaded_assets_meta}

    if not_loaded_name_set:
        lower_set = {normalize_str(name) for name in not_loaded_name_set}

        def filter_assets(x):
            name_low = normalize_str(Path(x).name)
            return name_low in lower_set

        paths = list(filter(filter_assets, handler.assets_paths))
        loaded_data: list[MetaData] = run_multiprocess(__get_meta, paths, is_many_args=False,
                                                       is_multiprocess=is_multiprocess)

        for data_file in loaded_data:
            handler.loaded_assets_meta.update({
                data_file.name: data_file,
                data_file.guid: data_file,
            })

    return [handler.loaded_assets_meta.get(name) for name in normalized_set]


def get_meta_dict_by_name_set(name_set: set, is_multiprocess=True) -> dict[str: MetaData]:
    datas = get_meta_by_name_set(name_set, is_multiprocess)
    return {
        name: data for name, data in zip(name_set, datas)
    }


def get_meta_by_guid_set(guid_set: set, is_multiprocess=True) -> list[MetaData]:
    handler = MetaDataHandler()
    not_loaded_guid_set = {guid for guid in guid_set if guid not in handler.loaded_assets_meta}

    if not_loaded_guid_set:
        paths = [handler.assets_guid_path.get(guid) for guid in not_loaded_guid_set]
        loaded_data: list[MetaData] = run_multiprocess(__get_meta, paths, is_many_args=False,
                                                       is_multiprocess=is_multiprocess)

        for data_file in loaded_data:
            handler.loaded_assets_meta.update({
                data_file.name: data_file,
                data_file.guid: data_file,
            })

    return [handler.loaded_assets_meta.get(guid) for guid in guid_set]


def get_meta_dict_by_guid_set(guid_set: set, is_multiprocess=True) -> dict[str: MetaData]:
    meta_datas = get_meta_by_guid_set(guid_set, is_multiprocess)
    return {
        meta_data.guid: meta_data for meta_data in meta_datas
    }


def get_meta_by_name(name: str, is_multiprocess=True) -> MetaData:
    meta_data = get_meta_by_name_set({name}, is_multiprocess)
    return meta_data[0] if meta_data else None


def get_meta_by_guid(guid: str, is_multiprocess=True) -> MetaData:
    meta_data = get_meta_by_guid_set({guid}, is_multiprocess)
    return meta_data[0] if meta_data else None


if __name__ == "__main__":
    def __test():
        handler = MetaDataHandler()
        handler.load()

        ui = get_meta_by_name("UI")

        print(handler.loaded_assets_meta)

        ui.init_sprites()

        for g, a in handler.loaded_assets_meta.items():
            print(g)
            for k, v in a.data_name.items():
                print(k, v)
                break

            for k, v in a.data_id.items():
                print(k, v)
                break


    __test()
