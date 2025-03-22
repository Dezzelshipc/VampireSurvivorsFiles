import os
import sys
import time

from pathlib import Path
from tkinter import Image

from unityparser import UnityDocument
from tkinter.messagebox import showerror
from PIL import Image

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
            if not os.path.exists(this_dir):
                missing_paths.append(this_dir)
                continue

            files.extend(f for f in this_dir.iterdir() if ".meta" in Path(f).suffixes and not f.is_dir())
            dirs.extend(f for f in this_dir.iterdir() if f.is_dir())

        if missing_paths:
            print(f"! Missing paths {missing_paths} while trying to access meta files for images.",
                  file=sys.stderr)
            # showerror("Error", f"Missing paths: {missing_paths}")

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


def _get_meta_guid(path: str):
    if not path or not os.path.exists(path):
        return None

    with open(path, 'r', encoding="UTF-8") as f:
        for line in f.readlines()[:10]:
            key, val = line.split(":")

            if key.strip() == "guid":
                return {val.strip(): path}

            if not val:
                return None


class MetaData:
    def __init__(self, name, guid, image, data_name, data_id):
        self.name: str = name
        self.guid: str = guid
        self.image: Image = image
        self.data_name: dict[str: dict] = data_name
        self.data_id: dict[int: dict] = data_id
        self._sprites: dict[str: Image] = dict() # Other signature (type)?

    def get_sprites(self) -> dict[str: Image]:
        raise NotImplementedError("Not implemented splitting sprites")


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
            "name": image_path.stem,
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

        prepared_data_entry = {
            'name': normalize_str(data_entry['name']),
            'internalID': internal_id,
            'rect': {
                k: float(v) for k, v in data_entry['rect'].items()
            },
            'pivot': {
                k: float(v) for k, v in data_entry['pivot'].items()
            }
        }
        prepared_data_name.update({
            data_entry['name']: prepared_data_entry
        })
        prepared_data_id.update({
            internal_id: prepared_data_entry
        })

    guid = entry['guid']
    name = os.path.basename(normalize_str(meta_path_name))

    print(f"Finished parsing {meta_path_name} [{guid=}] ({round(time.time() - time_start_parsing, 2)} sec)")

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
    def _print_guid(data: MetaData):
        print(data.guid)


    def __test():
        handler = MetaDataHandler()
        handler.load()

        def _print_all_guids():
            list(map(_print_guid, handler.loaded_assets_meta.values()))
            print()

        get_meta_by_name("UI")

        print(handler.loaded_assets_meta)

        _print_all_guids()
        a = get_meta_by_name("enemies2023")
        _print_all_guids()
        a.guid += "-!_ADDED HERE_!"
        _print_all_guids()


    __test()
