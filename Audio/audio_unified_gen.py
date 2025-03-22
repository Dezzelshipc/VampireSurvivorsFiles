from enum import Enum

from pathlib import Path
from typing import Tuple

from Config.config import Config
import Data.data as data_handler
import Translations.language as lang_handler

from unityparser import UnityDocument
from pydub import AudioSegment

from Utility.utility import run_multiprocess
from unpacker import Unpacker

import shutil


class AudioSaveType(Enum):
    CODE_NAME = "Code names"
    TITLE_NAME = "Audio titles"
    RELATIVE_NAME = "Relative object names"

    @classmethod
    def get(cls):
        return [*cls]

    def __str__(self):
        return self.value


def __get_musicPlaylists() -> list[dict]:
    config = Config()

    base_dirs = ["PrefabInstance", "GameObject", "Resources"]

    prefab_dirs = []
    for f in filter(lambda x: "ASSETS" in x.value, config.data):
        for b_dir in base_dirs:
            p = config[f].joinpath(b_dir)
            if p.exists():
                prefab_dirs.append(p)

    audio_prefabs = []

    def filt(x: Path):
        search_list = ["MasterAudio", "DynamicSoundGroup ", "ProjectContext"]
        for s in search_list:
            if x.is_file() and s.lower() in x.stem.lower() and ".meta" not in x.suffixes:
                return True
        return False

    for pref_dir in prefab_dirs:
        all_prefs = pref_dir.iterdir()
        audio_prefabs.extend(list(filter(filt, all_prefs)))

    music_playlists = []
    print("Parsing audio prefabs:", end=" ")
    for audio_prefab in audio_prefabs:
        print(audio_prefab.name, end=" ")
        ud = UnityDocument.load_yaml(audio_prefab)
        music_playlists.extend(
            *[x.musicPlaylists for x in ud.filter(class_names=('MonoBehaviour',), attributes=("musicPlaylists",))])
    print()

    return music_playlists


def __get_audioClipsPaths() -> list[Path]:
    config = Config()

    audio_clips_dirs = []
    for f in filter(lambda x: "ASSETS" in x.value, config.data):
        p = config[f].joinpath("AudioClip")
        if p.exists():
            audio_clips_dirs.append(p)

    audio_clips = []

    def filt(x: Path):
        return ".meta" not in x.suffixes

    for ac_dir in audio_clips_dirs:
        all_prefs = ac_dir.iterdir()
        audio_clips.extend(list(map(Path, filter(filt, all_prefs))))

    return audio_clips


def __get_audioClip(path: Path) -> Tuple[Path, AudioSegment]:
    return path, AudioSegment.from_file(path, format=path.suffix.replace(".", ""))


def gen_audio(music_json_path: Path, save_name_types: set[AudioSaveType], unpacker: Unpacker = None) -> (
        str | None, None | str):
    save_name_types.add(AudioSaveType.CODE_NAME)

    full_file_path = Path(__file__)
    f_path = full_file_path.parent

    save_path = f_path.joinpath("Generated")

    music_data = data_handler.get_data_file(music_json_path)

    datas = {}
    convert: dict[str: set] = {}
    if AudioSaveType.RELATIVE_NAME in save_name_types:
        not_found = []
        data_files = {
            "unlockedByStage": ("stageLang.json", "stageName", "Stage", "stageData_Full.json"),
            "unlockedByCharacter": ("characterLang.json", "charName", "Character", "characterData_Full.json"),
            "unlockedByItem": ("itemLang.json", "name", "Item", None),
        }

        bgm_keys = ["bgm", "BGM", "sideBBGM"]
        for k, items in data_files.items():
            file_name = items[0]
            lang = lang_handler.get_lang_file(lang_handler.get_lang_path(file_name))
            dat: dict = data_handler.get_data_file(data_handler.get_data_path(items[3]))
            if dat:
                for kk, vv in dat.items():
                    for bgm_key in bgm_keys:
                        if bgm := vv[0].get(bgm_key):
                            if bgm not in convert:
                                convert[bgm] = set()
                            convert[bgm].add((k, kk))

            if lang and (eng := lang.get("en")):
                datas.update({k: {
                    "lang": eng,
                    "key": items[1],
                    "type": items[2]
                }})
            else:
                not_found.append(file_name)

        if len(datas) < len(data_files):
            return None, f"! Not found split lang files for relative generator: {not_found}"

    music_playlists_raw = __get_musicPlaylists()

    music_ids_with_authors = dict(filter(lambda x: bool(x[-1].get("author")), music_data.items())).keys()

    music_playlists = list(filter(lambda x: x.get("playlistName") in music_ids_with_authors, music_playlists_raw))
    music_playlists.extend(filter(lambda x: x.get("playlistName") not in music_ids_with_authors, music_playlists_raw))

    audio_clips = __get_audioClipsPaths()
    audio_clips = {ac.stem.lower(): ac for ac in audio_clips}

    total_len = len(music_playlists)

    print(f"Generating music {total_len}:")

    already_generated = dict()
    for kk, music in enumerate(music_playlists):
        print(f"\r{kk + 1}", end="")
        code_name = music['playlistName']

        cur_data = music_data.get(code_name) or {}
        content_group = cur_data.get("contentGroup", "BASE_GAME")

        for save_type in save_name_types:
            sp = save_path.joinpath(str(save_type), content_group)
            sp.mkdir(parents=True, exist_ok=True)

            if save_type == AudioSaveType.TITLE_NAME:
                sp.joinpath("prefix").mkdir(parents=True, exist_ok=True)

            if save_type == AudioSaveType.RELATIVE_NAME:
                for ld in datas.values():
                    sp = save_path.joinpath(str(save_type), content_group, ld["type"])
                    sp.mkdir(parents=True, exist_ok=True)
                    sp.joinpath("prefix").mkdir(parents=True, exist_ok=True)

        tags = {
            "artist": cur_data.get("author"),
            "album": cur_data.get("source"),
            "title": cur_data.get("title")
        }
        if None in tags.values():
            tags = {}

        has_same_name = (sngn := music['MusicSettings'][0]['songName'].lower()) and bool(
            cur_data.get("source")) and audio_clips.get(sngn + "_0")

        clips = []
        ext = ""
        for setting in music['MusicSettings']:
            song_name = setting['songName'].lower()
            if has_same_name:
                song_name += "_0"

            clip_data = audio_clips.get(song_name)
            ext = clip_data.suffix.replace(".", "")

            clips.append(clip_data)

        clips = run_multiprocess(__get_audioClip, clips, is_many_args=False)
        audio: AudioSegment = sum(dict(clips).values())

        def path_dest(s_type: AudioSaveType, *other):
            return save_path.joinpath(str(s_type), content_group, *other)

        save_name = f"{code_name}.{ext}"
        code_name_path = path_dest(AudioSaveType.CODE_NAME, save_name)
        audio.export(code_name_path, ext, tags=tags)

        if AudioSaveType.TITLE_NAME in save_name_types and (title := cur_data.get("title")):
            title_add = ""
            if (source := cur_data.get("source")) and ("Castlevania" in source):
                title_add = " - " + source.replace("Castlevania", "").strip()

            save_name = f"{title}{title_add}.{ext}"

            shutil.copy(code_name_path, path_dest(AudioSaveType.TITLE_NAME, save_name))
            shutil.copy(code_name_path, path_dest(AudioSaveType.TITLE_NAME, "prefix", "Audio-" + save_name))

        if AudioSaveType.RELATIVE_NAME in save_name_types:

            related_objects: set = convert.get(code_name) or set()
            for k in ["unlockedByItem"]:
                if v := cur_data.get(k):
                    related_objects.add((k, v))

            for k, v in related_objects:
                key_name = datas[k]["key"]
                cur_type = datas[k]["type"]
                cur_obj = datas[k]["lang"].get(v) or {}
                name = cur_obj.get(key_name) or code_name

                if prefix := cur_obj.get('prefix'):
                    flt = lambda x: x and not x.get("prefix") and x.get("charName") == name

                    main_object = list(filter(flt, datas["unlockedByCharacter"]["lang"].values()))
                    if main_object or "megalo" in prefix.lower():
                        name = f"{prefix} {name}"

                def pst(ii):
                    return ii if ii > 0 else ""

                if has_same_name:
                    name += " B"

                j = 0
                save_name = f"{name}{pst(j)}.{ext}"
                while save_name in already_generated:
                    j += 1
                    save_name = f"{name}{pst(j)}.{ext}"

                already_generated.update({save_name: True})

                shutil.copy(code_name_path, path_dest(AudioSaveType.RELATIVE_NAME, cur_type, save_name))
                shutil.copy(code_name_path,
                            path_dest(AudioSaveType.RELATIVE_NAME, cur_type, "prefix", "Audio-" + save_name))

        if unpacker:
            unpacker.progress_bar_set(kk + 1, total_len)

    return save_path, None


if __name__ == "__main__":
    gen_audio(data_handler.get_data_path("musicData_Full.json"), set())
