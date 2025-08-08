import asyncio
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal, Callable

from pydub import AudioSegment

import Data.data as data_module
import Translations.language as lang_handler
from Config.config import Config, DLCType
from Data.data import COMPOUND_DATA
from Utility.constants import GENERATED
from Utility.meta_data import MetaDataHandler
from Utility.multirun import run_concurrent_sync, run_gather
from Utility.timer import Timeit
from Utility.unityparser2 import UnityDoc
from Utility.utility import normalize_str


class AudioSaveType(Enum):
    CODE_NAME = "Code names"
    TITLE_NAME = "Audio titles"
    RELATIVE_NAME = "Relative object names"

    @classmethod
    def get(cls):
        return [*cls]

    def __str__(self):
        return self.value


def _get_music_playlists() -> list[dict]:
    handler = MetaDataHandler()

    search_list = ["MasterAudio", "DynamicSoundGroup", "ProjectContext"]

    def flt(tuple_s_p: tuple[str, Path]):
        s, _ = tuple_s_p
        return any(normalize_str(search) in normalize_str(s) for search in search_list)

    audio_prefabs = handler.filter_paths(flt)
    audio_prefabs = set(dict(audio_prefabs).values())

    timeit = Timeit()
    print(f"Parsing audio prefabs ({len(audio_prefabs)})... ", end=" ")

    args_load = (audio_prefab.with_suffix("") for audio_prefab in audio_prefabs)
    uds = run_concurrent_sync(UnityDoc.yaml_parse_file_smart, args_load)

    print(f"Finished parsing audio prefabs ({timeit:.2f} sec)")

    music_playlists = [
        item
        for ud in uds
        for pl in ud.filter(class_names=('MonoBehaviour',), attributes=("musicPlaylists",))
        for item in pl.get("musicPlaylists")
    ]

    return music_playlists


def _get_audio_clips_paths() -> set[Path]:
    handler = MetaDataHandler()

    def flt(tuple_s_p: tuple[str, Path]):
        _, p = tuple_s_p
        return p.match("*/AudioClip/*")

    audio_clips = handler.filter_paths(flt)
    return set(map(lambda x: x.with_suffix(""), dict(audio_clips).values()))


def _get_audio_clip(path: Path) -> tuple[Path, AudioSegment]:
    return path, AudioSegment.from_file(path, format=path.suffix.replace(".", ""))


@dataclass
class MusicTrack:
    audio: AudioSegment | None
    audio_clips_paths: list[Path]
    tags: dict[Literal["artist", "album", "title", "source"], str]
    code_name: str
    ext: str
    content_group: str
    has_same_name: bool

    def get_code_name_ext(self):
        return f"{self.code_name}.{self.ext}"

    async def init_audio(self):
        if not self.ext:
            return
        clips: list[tuple[Path, AudioSegment]] = await asyncio.gather(
            *[asyncio.to_thread(_get_audio_clip, path) for path in self.audio_clips_paths])
        self.audio = sum(dict(clips).values()) if clips else None


def _get_music_track(audio_clips, music_data, playlist_data) -> MusicTrack:
    code_name = playlist_data['playlistName']

    cur_data = music_data.get(code_name) or {}

    tags = {
        "artist": cur_data.get("author"),
        "album": cur_data.get("source"),
        "source": cur_data.get("source"),
        "title": cur_data.get("title")
    }
    if None in tags.values():
        tags = {}

    has_same_name = (sngn := playlist_data['MusicSettings'][0]['songName'].lower()) and bool(
        tags.get("source")) and audio_clips.get(sngn + "_0")

    clips = []
    ext = ""
    for setting in playlist_data['MusicSettings']:
        song_name = normalize_str(setting['songName'])
        if has_same_name:
            song_name += "_0"

        clip_data = audio_clips.get(song_name)
        if not clip_data:
            print(f"Music track not found by song name ({song_name=} ;; {setting['songName']=})")
        else:
            ext = clip_data.suffix.replace(".", "")

        clips.append(clip_data)

    content_group = cur_data and cur_data.get("contentGroup", "BASE_GAME") or "UNCATEGORIZED"

    return MusicTrack(None, clips, tags, code_name, ext, content_group, has_same_name)


def _save_track(music_track: MusicTrack, save_path: Path):
    music_track.audio.export(save_path, music_track.ext, tags=music_track.tags)


def gen_music_tracks(music_dlc: DLCType | Literal[COMPOUND_DATA], save_name_types: set[AudioSaveType],
                     func_progress_bar_set_percent: Callable[[int | float, int | float], None] = lambda c, t: 0) -> (
        str | None, None | str):
    save_name_types.add(AudioSaveType.CODE_NAME)

    full_file_path = Path(__file__)
    f_path = full_file_path.parent

    save_path = f_path / GENERATED

    music_data = data_module.DataHandler.get_data(music_dlc, data_module.DataType.MUSIC).data()

    datas = {}
    convert: dict[str: set[str, str, bool]] = {}
    bgm_keys = ["bgm", "BGM", "sideBBGM"]
    if AudioSaveType.RELATIVE_NAME in save_name_types:
        not_found = []
        data_files = {
            "unlockedByStage": ("stageLang.json", "stageName", "Stage", data_module.DataType.STAGE),
            "unlockedByCharacter": ("characterLang.json", "charName", "Character",  data_module.DataType.CHARACTER),
            "unlockedByItem": ("itemLang.json", "name", "Item", None),
        }

        for data_key, items in data_files.items():
            file_name = items[0]
            lang = lang_handler.get_lang_file(lang_handler.get_lang_path(file_name))
            dat = data_module.DataHandler.get_data(COMPOUND_DATA, items[3])
            if dat:
                dat = dat.data()
                for data_entry_id, vv in dat.items():
                    for bgm_key in bgm_keys:
                        if bgm := vv[0].get(bgm_key):
                            if bgm not in convert:
                                convert[bgm] = set()

                            is_b_side = (bgm_key == bgm_keys[-1]) and (
                                        convert[bgm] not in (data_key, data_entry_id, False))

                            convert[bgm].add((data_key, data_entry_id, is_b_side))

            if lang and (eng := lang.get("en")):
                datas.update({data_key: {
                    "lang": eng,
                    "key": items[1],
                    "type": items[2]
                }})
            else:
                not_found.append(file_name)

        if len(datas) < len(data_files):
            return None, f"! Not found split lang files for relative generator: {not_found}"

    music_playlists_raw = _get_music_playlists()

    music_ids_with_authors = dict(filter(lambda x: bool(x[-1].get("author")), music_data.items())).keys()

    music_playlists = list(filter(lambda x: x.get("playlistName") in music_ids_with_authors, music_playlists_raw))
    music_playlists.extend(filter(lambda x: x.get("playlistName") not in music_ids_with_authors, music_playlists_raw))

    audio_clips = _get_audio_clips_paths()
    audio_clips = {normalize_str(ac): ac for ac in audio_clips}

    total_len = len(music_playlists)

    print(f"Multiprocessing: {Config().get_multiprocessing()}")
    print(f"Generating {total_len} tacks")

    args_gen_tracks = (
        (audio_clips, music_data, playlist_data)
        for playlist_data in music_playlists
    )
    timeit = Timeit()

    audio_tracks: list[MusicTrack] = run_concurrent_sync(_get_music_track, args_gen_tracks)
    run_gather(*[track.init_audio() for track in audio_tracks])
    audio_tracks = list(filter(lambda x: x.audio, audio_tracks))

    total_len = len(audio_tracks)

    print(f"Generated tacks ({timeit:.2f} sec)")

    content_group_set = {track.content_group for track in audio_tracks}
    for content_group in content_group_set:
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

    def path_dest(s_type: AudioSaveType, m_track: MusicTrack, *other):
        return save_path.joinpath(str(s_type), m_track.content_group, *other)

    timeit = Timeit()
    print("Saving tracks with code names")

    args_save_tracks = [
        (music_tack, path_dest(AudioSaveType.CODE_NAME, music_tack) / music_tack.get_code_name_ext())
        for music_tack in audio_tracks
    ]
    run_concurrent_sync(_save_track, args_save_tracks)

    print(f"Saved tracks with code names ({timeit:.2f} sec)")

    if not save_name_types.difference({AudioSaveType.CODE_NAME}):
        return save_path, None

    timeit = Timeit()
    print("Saving tracks with other names:")

    already_generated = dict()
    for kk, (music_track, code_name_path) in enumerate(args_save_tracks):
        code_name = music_track.code_name
        tags = music_track.tags
        has_same_name = music_track.has_same_name
        ext = music_track.ext

        cur_data = music_data.get(code_name) or {}

        if AudioSaveType.TITLE_NAME in save_name_types and (title := tags.get("title")):
            title_add = ""
            if (source := tags.get("source")) and ("Castlevania" in source):
                title_add = " - " + source.replace("Castlevania", "").strip()

            save_name = f"{title}{title_add}.{ext}"

            shutil.copy(code_name_path, path_dest(AudioSaveType.TITLE_NAME, music_track, save_name))
            shutil.copy(code_name_path,
                        path_dest(AudioSaveType.TITLE_NAME, music_track, "prefix", "Audio-" + save_name))

        if AudioSaveType.RELATIVE_NAME in save_name_types:

            related_objects: set = convert.get(code_name) or set()
            for data_key in ["unlockedByItem"]:
                if data_entry_id := cur_data.get(data_key):
                    related_objects.add((data_key, data_entry_id, ""))

            for data_key, data_entry_id, is_b_side in related_objects:
                key_name = datas[data_key]["key"]
                cur_type = datas[data_key]["type"]
                cur_obj = datas[data_key]["lang"].get(data_entry_id) or {}
                name = cur_obj.get(key_name) or code_name

                surname = cur_obj.get('surname') or " "
                space2 = surname[0] not in [":", ","] and " " or ""
                name = f"{cur_obj.get('prefix') or ""} {name}{space2}{surname}".strip()

                # if prefix := cur_obj.get('prefix'):
                #     flt = lambda x: x and not x.get("prefix") and x.get("charName") == name
                #
                #     main_object = list(filter(flt, datas["unlockedByCharacter"]["lang"].values()))
                #     if main_object or "megalo" in prefix.lower():
                #         name = f"{prefix} {name}"

                if has_same_name or is_b_side:
                    name += " B"

                def pst(ii):
                    return ii if ii > 0 else ""

                j = 0
                save_name = f"{name}{pst(j)}.{ext}"
                while save_name in already_generated:
                    j += 1
                    save_name = f"{name}{pst(j)}.{ext}"

                already_generated.update({save_name: True})

                shutil.copy(code_name_path, path_dest(AudioSaveType.RELATIVE_NAME, music_track, cur_type, save_name))
                shutil.copy(code_name_path, path_dest(AudioSaveType.RELATIVE_NAME, music_track, cur_type, "prefix",
                                                      "Audio-" + save_name))

        print(f"\r{kk + 1}", end="")
        func_progress_bar_set_percent(kk + 1, total_len)

    print(f"\nFinished saving tracks with other names ({timeit:.2f} sec)")
    return save_path, None


if __name__ == "__main__":
    gen_music_tracks(COMPOUND_DATA, set())
