from enum import Enum

from select import select

from Config.config import Config
import Data.data as data_handler
import Translations.language as lang_handler

from unityparser import UnityDocument
from pydub import AudioSegment
from unpacker import Unpacker

import os
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
            p = os.path.join(config[f], b_dir)
            if os.path.exists(p):
                prefab_dirs.append(p)

    audio_prefabs = []

    def filt(x: os.DirEntry):
        search_list = ["MasterAudio", "DynamicSoundGroup ", "ProjectContext"]
        for s in search_list:
            if s in x.name and ".meta" not in x.name:
                return True
        return False

    for pref_dir in prefab_dirs:
        all_prefs = os.scandir(pref_dir)
        audio_prefabs.extend(list(filter(filt, all_prefs)))

    music_playlists = []
    print("Parsing audio prefabs:", end=" ")
    for audio_prefab in audio_prefabs:
        print(audio_prefab, end=" ")
        ud = UnityDocument.load_yaml(audio_prefab)
        music_playlists.extend(
            *[x.musicPlaylists for x in ud.filter(class_names=('MonoBehaviour',), attributes=("musicPlaylists",))])
    print()

    return music_playlists


def __get_audioClips() -> list[os.DirEntry]:
    config = Config()

    audio_clips_dirs = []
    for f in filter(lambda x: "ASSETS" in x.value, config.data):
        p = os.path.join(config[f], "AudioClip")
        if os.path.exists(p):
            audio_clips_dirs.append(p)

    audio_clips = []

    def filt(x: os.DirEntry):
        return ".meta" not in x.name

    for ac_dir in audio_clips_dirs:
        all_prefs = os.scandir(ac_dir)
        audio_clips.extend(list(filter(filt, all_prefs)))

    return audio_clips


def gen_audio(music_json_path: os.PathLike, save_name_types: set[AudioSaveType], unpacker: Unpacker = None) -> (str | None, None | str):

    save_name_types.add(AudioSaveType.CODE_NAME)

    f_path, f_name = os.path.split(__file__)

    save_path = os.path.join(f_path, "Generated")

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
        for k, items in data_files.items():
            file_name = items[0]
            lang = lang_handler.get_lang_file(lang_handler.get_lang_path(file_name))
            dat: dict = data_handler.get_data_file(data_handler.get_data_path(items[3]))
            if dat:
                for kk, vv in dat.items():
                    bgm = vv[0].get("bgm") or vv[0].get("BGM")
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

    audio_clips = __get_audioClips()

    total_len = len(music_playlists)

    print(f"Generating music {total_len}:")

    already_generated = dict()
    for kk, music in enumerate(music_playlists):
        print(f"\r{kk+1}", end="")
        code_name = music['playlistName']

        cur_data = music_data.get(code_name) or {}
        content_group = cur_data.get("contentGroup", "BASE_GAME")

        for save_type in save_name_types:
            sp = os.path.join(save_path, str(save_type), content_group)
            os.makedirs(sp, exist_ok=True)

            if save_type == AudioSaveType.TITLE_NAME:
                os.makedirs(sp+"\\prefix", exist_ok=True)

            if save_type == AudioSaveType.RELATIVE_NAME:
                for ld in datas.values():
                    sp = os.path.join(save_path, str(save_type), content_group, ld["type"])
                    os.makedirs(sp, exist_ok=True)

        tags = {
            "artist": cur_data.get("author"),
            "album": cur_data.get("source"),
            "title": cur_data.get("title")
        }
        has_multiple = bool(cur_data.get("source")) # first check

        def path_dest(s_type: AudioSaveType, s_name):
            return os.path.join(save_path, str(s_type), content_group, s_name)

        audio: AudioSegment = None
        audio_file_only = None
        ext = ""
        for setting in music['MusicSettings']:
            song_name = setting['songName'].lower()

            found_audio_files = list(filter(lambda x: song_name in os.path.splitext(x.name)[0].lower(), audio_clips))
            if has_multiple and len(found_audio_files) > 1:
                song_name += "_0"
            else:
                has_multiple = False

            audio_files = list(filter(lambda x: song_name == os.path.splitext(x.name)[0].lower(), found_audio_files))
            ext = os.path.splitext(audio_files[0])[-1].replace(".", "")

            if len(music['MusicSettings']) > 1:
                for audio_file in audio_files:
                    if audio is None:
                        audio = AudioSegment.from_file(audio_file, format=ext)
                    else:
                        audio += AudioSegment.from_file(audio_file, format=ext)
            else:
                audio_file_only = audio_files[0]



        save_name = f"{code_name}.{ext}"
        code_name_path = path_dest(AudioSaveType.CODE_NAME, save_name)
        if audio_file_only:
            shutil.copy(audio_file_only, code_name_path)
        else:
            audio.export(code_name_path, ext, tags=tags)


        if AudioSaveType.TITLE_NAME in save_name_types and (title := cur_data.get("title")):
            title_add = ""
            if (source := cur_data.get("source")) and ("Castlevania" in source):
                title_add = " - " + source.replace("Castlevania", "").strip()

            save_name = f"{title}{title_add}.{ext}"

            shutil.copy(code_name_path, path_dest(AudioSaveType.TITLE_NAME, save_name))
            shutil.copy(code_name_path, path_dest(AudioSaveType.TITLE_NAME, "prefix\\Audio-"+save_name))

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

                if has_multiple:
                    name += " B"

                j = 0
                save_name = f"Audio-{name}{pst(j)}.{ext}"
                while save_name in already_generated:
                    j += 1
                    save_name = f"Audio-{name}{pst(j)}.{ext}"

                already_generated.update({save_name: 1})

                shutil.copy(code_name_path, path_dest(AudioSaveType.RELATIVE_NAME, cur_type + "\\" + save_name))

        if unpacker:
            unpacker.progress_bar_set(kk+1, total_len)

    return save_path, None


if __name__ == "__main__":
    gen_audio(data_handler.get_data_path("musicData_Full.json"), set())
