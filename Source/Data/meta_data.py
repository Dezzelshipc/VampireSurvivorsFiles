from collections.abc import Callable
from pathlib import Path
from tkinter import Image

from PIL.Image import Image, open as image_open

from Source.Config.config import DLCType, Config, Game
from Source.Utility.constants import RESOURCES, TEXTURE_2D, TEXT_ASSET, GAME_OBJECT, PREFAB_INSTANCE, AUDIO_CLIP, \
    MONO_BEHAVIOUR, DATA_MANAGER_SETTINGS, BUNDLE_MANIFEST_DATA
from Source.Utility.image_functions import crop_image_rect_left_bot, split_name_count, get_rects_by_sprite_list
from Source.Utility.multirun import run_multiprocess_single
from Source.Utility.special_classes import Objectless
from Source.Utility.sprite_data import SpriteData, AnimationData, SKIP_ANIM_NAMES_LIST
from Source.Utility.timer import Timeit
from Source.Utility.unityparser2 import UnityDoc
from Source.Utility.utility import normalize_str
from Utility.constants import CARD_DATABASE
from Utility.special_classes import Singleton


def _get_meta_guid(path: Path) -> tuple[str, Path] | None:
    if not path or not path.exists():
        return None

    with open(path, 'r', encoding="UTF-8") as f:
        for i, line in enumerate(f.readlines()):
            if "guid" in line:
                key, val = line.split(":")

                if key.strip() == "guid":
                    return val.strip(), path

            if i > 3:
                return None
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

            print(f"Generated sprites for {self.real_name} {timeit!r}")

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

                anim_data = AnimationData(name,
                                          sprite_name_list,
                                          rect_list,
                                          [s.sprite for s in sprite_list])

                if len(anim_data) > 1:
                    for sprite_name in sprite_name_list:
                        self.data_name[sprite_name].animation = anim_data

            self.__added_animations = True

            print(f"Generated animations for {self.real_name} {timeit!r}")

    def get_animations(self) -> set[AnimationData]:
        self.init_animations()
        return set(sprite.animation for sprite in self.data_name.values() if sprite.animation is not None)

    def __getitem__(self, item):
        # SHOULD NOT BE USED NORMALLY
        return self.__getattribute__(item)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name} ({self.real_name}) at {hex(id(self)).upper()}>"


def _get_meta(meta_path: Path) -> MetaData:
    timeit = Timeit()

    meta_path_name = meta_path.name
    print(f"Started parsing {meta_path_name}")
    image_path = meta_path.with_suffix("")
    image = image_open(image_path)

    doc = UnityDoc.yaml_parse_file(meta_path)
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

    print(f"Finished parsing {meta_path_name} [{guid=}] {timeit!r}")

    return MetaData(name, meta_path_name, guid, image, prepared_data_name, prepared_data_id)


class MetaDataHandler(Objectless):
    _found_files: list[Path] = []

    _assets_name_path: dict[str, Path] = {}
    _assets_guid_path: dict[str, Path] = {}

    loaded_game: Game = None
    loaded_assets_meta: dict[str, MetaData] = {}

    @classmethod
    def load(cls, game: Game):
        if game != cls.loaded_game:
            if cls.loaded_game is not None:
                cls.unload()
            cls.loaded_game = game

        cls._load_assets_meta_file_paths()
        cls._load_assets_meta_files_guids()

    @classmethod
    def unload(cls):
        cls._found_files.clear()
        cls._assets_name_path.clear()
        cls._assets_guid_path.clear()
        cls.loaded_assets_meta.clear()
        print(f"MetaData unloaded ({cls.loaded_game.name})")

    @classmethod
    def assert_game(cls, game: Game):
        assert cls.loaded_game == game

    @classmethod
    def assert_loaded_game(cls):
        assert cls.loaded_game is not None, f"Game assets not loaded! ({cls.loaded_game})"

    @classmethod
    def _load_assets_meta_file_paths(cls) -> None:
        if cls._assets_name_path:
            return

        timeit = Timeit()

        path_roots = [
            (RESOURCES, ""),
            (TEXTURE_2D, ""),
            (TEXT_ASSET, ""),
            (GAME_OBJECT, ""),
            (PREFAB_INSTANCE, ""),
            (AUDIO_CLIP, ""),
        ]

        match cls.loaded_game:
            case Game.VS:
                path_roots.extend([
                    (MONO_BEHAVIOUR, DATA_MANAGER_SETTINGS),
                    (MONO_BEHAVIOUR, BUNDLE_MANIFEST_DATA),
                ])
            case Game.VC:
                path_roots.extend([
                    (MONO_BEHAVIOUR, ""),
                ])

        for dlc in DLCType.get_all_types_by_game(cls.loaded_game):
            for root, file_name in path_roots:
                path = Config.get_assets_dir(dlc) and Config.get_assets_dir(dlc).joinpath(root)
                if path and path.exists():
                    cls._found_files.extend(path.rglob(f"{file_name}*.meta"))

        ### deduplication
        files_by_stem = {}
        for f in cls._found_files:
            name_norm = normalize_str(f)
            if name_norm not in files_by_stem:
                files_by_stem[name_norm] = []
            files_by_stem[name_norm].append(f)

        biggest_files = []
        for f_list in files_by_stem.values():
            if len(f_list) > 1:
                biggest_files.append(
                    list(sorted(f_list, key=lambda x: 1e10 * int("png" in x.name) + x.stat().st_size, reverse=True))[0])
            else:
                biggest_files.append(f_list[0])
        ###

        cls._assets_name_path.update({normalize_str(f): f for f in biggest_files})
        print(f"Loaded {len(cls._found_files)} meta paths ({timeit:.2f} sec)")

    @classmethod
    def _load_assets_meta_files_guids(cls) -> None:
        cls._load_assets_meta_file_paths()

        if not cls._assets_guid_path:
            print("Started collecting guid of every asset")
            timeit = Timeit()
            # guid_path = run_concurrent_sync(_get_meta_guid, self._found_files)
            guid_path = run_multiprocess_single(_get_meta_guid, cls._found_files)
            cls._assets_guid_path.update(guid_path)
            print(f"Finished collecting guid of every asset ({timeit:.2f} sec)")

    @classmethod
    def add_meta_data_by_path(cls, path: Path) -> None:
        norm = normalize_str(path)
        cls._assets_name_path.update({norm: path})
        guid_path = _get_meta_guid(path)
        cls._assets_guid_path.update([guid_path])

    @classmethod
    def has_meta_by_path(cls, path: Path) -> bool:
        cls.assert_loaded_game()
        norm = normalize_str(path)
        return norm in cls._assets_name_path

    @classmethod
    def add_meta_data_by_meta(cls, name: str, _meta_data: MetaData) -> None:
        cls.loaded_assets_meta.update({
            normalize_str(name): _meta_data,
            name: _meta_data
        })

    @classmethod
    def has_meta_by_name(cls, name: str) -> bool:
        return normalize_str(name) in cls.loaded_assets_meta

    @classmethod
    def get_path_by_name(cls, name: str) -> Path | None:
        cls.assert_loaded_game()
        return cls._assets_name_path.get(normalize_str(name))

    @classmethod
    def get_path_by_name_no_meta(cls, name: str) -> Path | None:
        cls.assert_loaded_game()
        path = cls.get_path_by_name(name)
        return path.with_suffix("") if path else None

    @classmethod
    def get_path_by_guid(cls, guid: str) -> Path | None:
        cls.assert_loaded_game()
        return cls._assets_guid_path.get(normalize_str(guid))

    @classmethod
    def get_path_by_guid_no_meta(cls, guid: str) -> Path | None:
        cls.assert_loaded_game()
        path = cls.get_path_by_guid(guid)
        return path.with_suffix("") if path else None

    @classmethod
    def filter_paths(cls, f_filter: Callable[[tuple[str, Path]], bool]) -> set[tuple[str, Path]]:
        cls.assert_loaded_game()
        return set(filter(f_filter, cls._assets_name_path.items()))

    @classmethod
    def get_meta_by_name_set(cls, name_set: set, is_multiprocess=True) -> set[MetaData]:
        cls.assert_loaded_game()

        normalized_set = {normalize_str(name) for name in name_set}
        not_loaded_name_set = {name for name in normalized_set if name not in cls.loaded_assets_meta}

        if not_loaded_name_set:
            paths = [cls.get_path_by_name(name) for name in not_loaded_name_set]
            loaded_data: list[MetaData] = run_multiprocess_single(_get_meta, paths, is_multiprocess=is_multiprocess)

            for data_file in loaded_data:
                cls.loaded_assets_meta.update({
                    data_file.name: data_file,
                    data_file.guid: data_file,
                })

        return {cls.loaded_assets_meta.get(name) for name in normalized_set}

    @classmethod
    def get_meta_dict_by_name_set(cls, name_set: set, is_multiprocess=True) -> dict[str, MetaData]:
        datas = cls.get_meta_by_name_set(name_set, is_multiprocess)
        meta_dict = {
            data.real_name.replace(".png", "").replace(".meta", ""): data for data in datas
        }
        meta_dict.update({
            data.name: data for data in datas
        })
        return meta_dict

    @classmethod
    def get_meta_by_guid_set(cls, guid_set: set, is_multiprocess=True) -> set[MetaData]:
        cls.assert_loaded_game()

        not_loaded_guid_set = {guid for guid in guid_set if guid not in cls.loaded_assets_meta}

        if not_loaded_guid_set:
            paths = [cls.get_path_by_guid(guid) for guid in not_loaded_guid_set]
            loaded_data: list[MetaData] = run_multiprocess_single(_get_meta, paths, is_multiprocess=is_multiprocess)

            for data_file in loaded_data:
                cls.loaded_assets_meta.update({
                    data_file.name: data_file,
                    data_file.guid: data_file,
                })

        return {cls.loaded_assets_meta.get(guid) for guid in guid_set}

    @classmethod
    def get_meta_dict_by_guid_set(cls, guid_set: set, is_multiprocess=True) -> dict[str, MetaData]:
        meta_datas = cls.get_meta_by_guid_set(guid_set, is_multiprocess)
        return {
            meta_data.guid: meta_data for meta_data in meta_datas
        }

    @classmethod
    def get_meta_by_name(cls, name: str, is_multiprocess=True) -> MetaData:
        meta_data = cls.get_meta_by_name_set({name}, is_multiprocess)
        return meta_data.pop() if meta_data else None

    @classmethod
    def get_meta_by_guid(cls, guid: str, is_multiprocess=True) -> MetaData:
        meta_data = cls.get_meta_by_guid_set({guid}, is_multiprocess)
        return meta_data.pop() if meta_data else None

    @classmethod
    def get_meta_dict_by_name_set_fullest(cls, name_set: set, is_multiprocess=True) -> dict[str, MetaData]:
        fullest_set = {}

        for name in name_set:
            norm_name = normalize_str(name)
            filtered = cls.filter_paths(
                lambda name_path: name_path[0].startswith(norm_name+"_") or name_path[0] == norm_name
            )
            fullest = list(sorted(filtered, key=lambda name_path: name_path[-1].stat().st_size, reverse=True))[0]
            fullest_set[fullest[0]] = name

        datas = cls.get_meta_by_name_set(set(fullest_set.keys()), is_multiprocess)

        meta_dict = {
            data.real_name.replace(".png", "").replace(".meta", ""): data
            for data in datas
        }
        meta_dict.update({
            fullest_set[data.name]: data
            for data in datas
        })
        meta_dict.update({
            normalize_str(fullest_set[data.name]): data
            for data in datas
        })
        return meta_dict

    @classmethod
    def get_meta_by_name_fullest(cls, name: str, is_multiprocess=True) -> MetaData:
        meta_data = cls.get_meta_dict_by_name_set_fullest({name}, is_multiprocess)
        return list(meta_data.values())[0] if meta_data else None


if __name__ == "__main__":
    # a = MetaDataHandler.get_meta_by_name_fullest("character_chulareh")
    a = MetaDataHandler.get_meta_by_name_fullest("ThosePeople")
    # a = MetaDataHandler.get_meta_by_name("enemies")
    # a = MetaDataHandler.get_meta_by_guid('f2e351beec1ed57408f2e8aab0db8951')

    a.init_sprites()

    pass
