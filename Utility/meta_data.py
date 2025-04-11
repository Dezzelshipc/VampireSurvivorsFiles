from collections.abc import Callable
from pathlib import Path
from tkinter import Image

from PIL import Image
from unityparser import UnityDocument

from Config.config import Config, DLCType
from Utility.image_functions import crop_image_rect_left_bot, split_name_count, get_rects_by_sprite_list
from Utility.singleton import Singleton
from Utility.sprite_data import SpriteData, AnimationData, SKIP_ANIM_NAMES_LIST
from Utility.timer import Timeit
from Utility.utility import normalize_str
from Utility.multirun import run_multiprocess


class MetaDataHandler(metaclass=Singleton):
    def __init__(self):
        self.config = Config()

        self._found_files: list[Path] = []

        self._assets_name_path: dict[str, Path] = {}
        self._assets_guid_path: dict[str, Path] = {}

        self.loaded_assets_meta: dict[str, MetaData] = {}

        self._load_assets_meta_file_paths()
        self._load_assets_meta_files_guids()

    def _load_assets_meta_file_paths(self) -> None:
        if self._assets_name_path:
            return

        timeit = Timeit()

        path_roots = ["Resources", "Texture2D", "TextAsset", "GameObject", "PrefabInstance", "AudioClip"]

        dirs = []
        for dlc in DLCType.get_all_dlc():
            for root in path_roots:
                path = self.config[dlc.config_key] and self.config[dlc.config_key].joinpath(root)
                if path and path.exists():
                        dirs.append(path)

        for this_dir in dirs:
            self._found_files.extend(this_dir.rglob("*.meta"))

        # deduplication
        files_by_stem = {}
        for f in self._found_files:
            name_norm = normalize_str(f)
            if not files_by_stem.get(name_norm):
                files_by_stem[name_norm] = []
            files_by_stem[name_norm].append(f)

        biggest_files = []
        for f_list in files_by_stem.values():
            if len(f_list) > 1:
                biggest_files.append(list(reversed(sorted(f_list, key=lambda x:  1e10 * int("png" in x.name) + x.stat().st_size)))[0])
            else:
                biggest_files.append(f_list[0])
        #

        self._assets_name_path.update({normalize_str(f): f for f in biggest_files})
        print(f"Loaded {len(self._found_files)} meta paths ({timeit:.2f} sec)")

    def _load_assets_meta_files_guids(self) -> None:
        self._load_assets_meta_file_paths()

        if not self._assets_guid_path:
            print("Started collecting guid of every asset")
            timeit = Timeit()
            guid_path = run_multiprocess(_get_meta_guid, self._found_files, is_many_args=False)
            self._assets_guid_path.update(guid_path)
            print(f"Finished collecting guid of every asset ({timeit:.2f} sec)")

    def get_path_by_name(self, name: str) -> Path | None:
        return self._assets_name_path.get(normalize_str(name))

    def get_path_by_name_no_meta(self, name: str) -> Path | None:
        path = self.get_path_by_name(name)
        return path.with_suffix("") if path else None

    def get_path_by_guid(self, guid: str) -> Path | None:
        return self._assets_guid_path.get(normalize_str(guid))

    def filter_paths(self, f_filter: Callable[[tuple[str, Path]], bool]) -> set[(str, Path)]:
        return set(filter(f_filter, self._assets_name_path.items()))


def _get_meta_guid(path: Path) -> tuple[str, Path] | None:
    if not path or not path.exists():
        return None

    with open(path, 'r', encoding="UTF-8") as f:
        for line in f.readlines()[:10]:
            key, val = line.split(":")

            if key.strip() == "guid":
                return val.strip(), path

            if not val:
                return None


class MetaData:
    def __init__(self, name: str, real_name: str, guid: str, image: Image, data_name: dict[str, SpriteData],
                 data_id: dict[int, SpriteData]):
        self.name: str = name
        self.real_name: str = real_name
        self.guid: str = guid
        self.image: Image = image
        self.data_name: dict[str, SpriteData] = data_name
        self.data_id: dict[int, SpriteData] = data_id

        self.__added_sprites = False
        self.__added_animations = False

    def init_sprites(self) -> None:
        if not self.__added_sprites:
            timeit = Timeit()

            for entry in set(self.data_name.values()):
                entry.sprite = crop_image_rect_left_bot(self.image, entry.rect)
            self.__added_sprites = True

            print(f"Generated sprites for {self.real_name} ({timeit:.2f} sec)")

    def init_animations(self) -> None:
        if not self.__added_animations:
            self.init_sprites()
            timeit = Timeit()

            anim_frames = {}
            for entry in set(self.data_name.values()):
                sprite_name = entry.real_name
                name, count = split_name_count(sprite_name)
                if sprite_name in SKIP_ANIM_NAMES_LIST:
                    print(f"! Skipped frame: {sprite_name} with. If it should be part of animation, tell this to dev!")
                    continue
                if name not in anim_frames:
                    anim_frames[name] = set()
                anim_frames[name].add((sprite_name, count))

            anim_frames = {
                name: list(map(lambda x: x[0], sorted(frames, key=lambda x: x[-1])))
                for name, frames in anim_frames.items()
            }

            for name, sprite_name_list in anim_frames.items():
                sprite_list = [self.data_name.get(sprite) for sprite in sprite_name_list]
                rect_list = get_rects_by_sprite_list(sprite_list)

                anim_data = AnimationData(name, sprite_name_list, rect_list, [s.sprite for s in sprite_list])

                if len(anim_data) > 1:
                    for sprite_name in sprite_name_list:
                        self.data_name[sprite_name].animation = anim_data

            self.__added_animations = True

            print(f"Generated animations for {self.real_name} ({timeit:.2f} sec)")

    def get_animations(self) -> set[AnimationData]:
        return set(sprite.animation for sprite in self.data_name.values() if sprite.animation is not None)

    def __getitem__(self, item):
        # SHOULD NOT BE USED NORMALLY
        return self.__getattribute__(item)


def __get_meta(meta_path: Path) -> MetaData:
    timeit = Timeit()

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
        data_name = str(data_entry['name'])
        norm_name = normalize_str(data_name)

        if prepared_data_entry := prepared_data_name.get(norm_name):
            prepared_data_entry.internal_id_set.add(internal_id)
        else:
            prepared_data_entry = SpriteData(
                name=norm_name,
                real_name=data_name,
                internal_id_set={internal_id},
                rect={
                    k: float(v) for k, v in data_entry['rect'].items()
                },
                pivot={
                    k: float(v) for k, v in data_entry['pivot'].items()
                }
            )

            prepared_data_name.update({
                data_name: prepared_data_entry,
                norm_name: prepared_data_entry
            })

        prepared_data_id.update({
            internal_id: prepared_data_entry
        })

    guid = entry['guid']
    name = normalize_str(meta_path_name)

    print(f"Finished parsing {meta_path_name} [{guid=}] ({timeit:.2f} sec)")

    return MetaData(name, meta_path_name, guid, image, prepared_data_name, prepared_data_id)


def get_meta_by_name_set(name_set: set, is_multiprocess=True) -> set[MetaData]:
    normalized_set = {normalize_str(name) for name in name_set}
    handler = MetaDataHandler()
    not_loaded_name_set = {name for name in normalized_set if name not in handler.loaded_assets_meta}

    if not_loaded_name_set:
        paths = [handler.get_path_by_name(name) for name in not_loaded_name_set]
        loaded_data: list[MetaData] = run_multiprocess(__get_meta, paths, is_many_args=False,
                                                       is_multiprocess=is_multiprocess)

        for data_file in loaded_data:
            handler.loaded_assets_meta.update({
                data_file.name: data_file,
                data_file.guid: data_file,
            })

    return {handler.loaded_assets_meta.get(name) for name in normalized_set}


def get_meta_dict_by_name_set(name_set: set, is_multiprocess=True) -> dict[str, MetaData]:
    datas = get_meta_by_name_set(name_set, is_multiprocess)
    return {
        name: data for name, data in zip(name_set, datas)
    }


def get_meta_by_guid_set(guid_set: set, is_multiprocess=True) -> set[MetaData]:
    handler = MetaDataHandler()
    not_loaded_guid_set = {guid for guid in guid_set if guid not in handler.loaded_assets_meta}

    if not_loaded_guid_set:
        paths = [handler.get_path_by_guid(guid) for guid in not_loaded_guid_set]
        loaded_data: list[MetaData] = run_multiprocess(__get_meta, paths, is_many_args=False,
                                                       is_multiprocess=is_multiprocess)

        for data_file in loaded_data:
            handler.loaded_assets_meta.update({
                data_file.name: data_file,
                data_file.guid: data_file,
            })

    return {handler.loaded_assets_meta.get(guid) for guid in guid_set}


def get_meta_dict_by_guid_set(guid_set: set, is_multiprocess=True) -> dict[str, MetaData]:
    meta_datas = get_meta_by_guid_set(guid_set, is_multiprocess)
    return {
        meta_data.guid: meta_data for meta_data in meta_datas
    }


def get_meta_by_name(name: str, is_multiprocess=True) -> MetaData:
    meta_data = get_meta_by_name_set({name}, is_multiprocess)
    return meta_data.pop() if meta_data else None


def get_meta_by_guid(guid: str, is_multiprocess=True) -> MetaData:
    meta_data = get_meta_by_guid_set({guid}, is_multiprocess)
    return meta_data.pop() if meta_data else None


if __name__ == "__main__":
    hndlr = MetaDataHandler()

    a = get_meta_by_name("character_mortaccio")
    # a = get_meta_by_name("enemies")
    # a = get_meta_by_guid('f2e351beec1ed57408f2e8aab0db8951')

    a.init_sprites()

    pass
