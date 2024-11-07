import os
import sys
import time
from tkinter import Image

from unityparser import UnityDocument
from tkinter.messagebox import showerror
from PIL import Image

from Utility.singleton import Singleton
from Utility.utility import run_multiprocess
from Config.config import Config


class MetaDataHandler(metaclass=Singleton):
    def __init__(self):
        self.config = Config()
        self.assets_paths = set()
        self.assets_guid_path = dict()

        self.loaded_assets_meta: dict[str: MetaData] = dict()

    def load_assets_meta_files(self):
        paths = [f"{self.config["VS_ASSETS"]}/Resources/spritesheets"]
        for f in filter(lambda x: "ASSETS" in x, self.config.data):
            p = os.path.join(self.config[f], "Texture2D")
            if os.path.exists(p):
                paths.append(p)

        dirs = list(map(os.path.normpath, paths))
        files = []
        missing_paths = []
        while dirs:
            this_dir = dirs.pop(0)
            if not os.path.exists(this_dir):
                missing_paths.append(this_dir)
                continue

            files.extend(f.path for f in os.scandir(this_dir) if f.name.endswith(".meta") and not f.is_dir())
            dirs.extend(f for f in os.scandir(this_dir) if f.is_dir())

        if missing_paths:
            print(f"! Missing paths {missing_paths} while trying to access meta files for images.",
                  file=sys.stderr)
            # showerror("Error", f"Missing paths: {missing_paths}")

        self.assets_paths.update(files)
        print("Loaded meta paths")

        return self

    def load_guid_paths(self):
        if self.assets_guid_path:
            return

        if not self.assets_paths:
            self.load_assets_meta_files()

        print("Started collecting guid of every asset")
        guid_path = run_multiprocess(get_meta_guid, self.assets_paths, is_many_args=False)
        for entry in guid_path:
            self.assets_guid_path.update(entry)
        print("Finished collecting guid of every asset")

        return self


def get_meta_guid(path: str):
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


def __get_meta(meta_path: str) -> MetaData:
    time_start_parsing = time.time()

    meta_path_name = os.path.basename(meta_path)
    print(f"Started parsing {meta_path_name}")
    image_path = meta_path.replace(".meta", "")
    image = Image.open(image_path)

    doc = UnityDocument.load_yaml(meta_path, try_preserve_types=True)
    entry = doc.entry
    data = entry["TextureImporter"]["spriteSheet"]["sprites"]

    prepared_data_name = dict()
    prepared_data_id = dict()
    for data_entry in data:
        prepared_data_entry = {
            'name': data_entry['name'],
            'internalID': data_entry['internalID'],
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
            data_entry['internalID']: prepared_data_entry
        })

    guid = entry['guid']
    name = os.path.basename( meta_path_name.replace(".meta", "") ).lower()

    print(f"Finished parsing {meta_path_name} [{guid=}] ({round(time.time() - time_start_parsing, 2)} sec)")

    return MetaData(name, guid, image, prepared_data_name, prepared_data_id)


def get_meta_by_name_set(name_set: set, is_multiprocess=True) -> list[MetaData]:
    handler = MetaDataHandler()
    not_loaded_name_set = {name for name in name_set if name.lower() not in handler.loaded_assets_meta}

    if not_loaded_name_set:
        lower_set = {name.lower() for name in not_loaded_name_set}

        def filter_assets(x):
            x = os.path.split(x)[1]
            name_low = x.lower().replace(".png", "").replace(".meta", "")
            return name_low in lower_set

        paths = list(filter(filter_assets, handler.assets_paths))
        loaded_data: list[MetaData] = run_multiprocess(__get_meta, paths, is_many_args=False,
                                                       is_multiprocess=is_multiprocess)

        for data_file in loaded_data:
            handler.loaded_assets_meta.update({
                data_file.name: data_file,
                data_file.guid: data_file,
            })

    return [handler.loaded_assets_meta.get(name.lower()) for name in name_set]


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


if __name__ == "__main__":
    MetaDataHandler().load_guid_paths()

    a = get_meta_dict_by_name_set({"UI", "enemies2023"})
    print(a)
