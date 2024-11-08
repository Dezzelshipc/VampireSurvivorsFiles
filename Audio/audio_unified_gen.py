from enum import Enum

from Config.config import Config
import Data.data as data_handler
import Translations.language as lang_handler
from unityparser import UnityDocument
import soundfile as sf

import os
import shutil


class AudioSaveType(Enum):
    CODE_NAME = "Code names"
    TITLE_NAME = "Audio titles"
    RELATIVE_NAME = "Relative object names (its unlocks)"

    @classmethod
    def get(cls):
        return [*cls]

    def __str__(self):
        return self.value


def __get_musicPlaylists() -> list[dict]:
    config = Config()

    prefab_dirs = []
    for f in filter(lambda x: "ASSETS" in x, config.data):
        p = os.path.join(config[f], "PrefabInstance")
        if os.path.exists(p):
            prefab_dirs.append(p)

    audio_prefabs = []

    def filt(x: os.DirEntry):
        search_list = ["MasterAudio", "DynamicSoundGroup "]
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

    return music_playlists


def __get_audioClips() -> list[os.DirEntry]:
    config = Config()

    audio_clips_dirs = []
    for f in filter(lambda x: "ASSETS" in x, config.data):
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


def gen_audio(music_json_path: os.PathLike, save_name_types: list[AudioSaveType]) -> (str | None, None | str):
    f_path, f_name = os.path.split(__file__)

    save_path = os.path.join(f_path, "Generated")

    music_data = data_handler.get_data_file(music_json_path)

    lang_datas = dict()
    if AudioSaveType.RELATIVE_NAME in save_name_types:
        not_found = []
        lang_files = {
            "unlockedByStage": ("stageLang.json", "stageName", "Stage"),
            "unlockedByCharacter": ("characterLang.json", "charName", "Character"),
            "unlockedByItem": ("itemLang.json", "name", "Item"),
        }
        for k, items in lang_files.items():
            file_name = items[0]
            lang = lang_handler.get_lang_file(lang_handler.get_lang_path(file_name))
            if lang and (eng := lang.get("en")):
                lang_datas.update({k: {"lang": eng, "key": items[1], "type": items[2]}})
            else:
                not_found.append(file_name)

        if len(lang_datas) < len(lang_files):
            return None, f"! Not found split lang files for relative generator: {not_found}"

    music_playlists = __get_musicPlaylists()

    audio_clips = __get_audioClips()

    for music in music_playlists:
        code_name = music['playlistName']

        cur_data = music_data.get(code_name) or {}
        content_group = cur_data.get("contentGroup", "BASE_GAME")

        for save_type in save_name_types:
            sp = os.path.join(save_path, str(save_type), content_group)
            if not os.path.exists(sp):
                os.makedirs(sp)

            if save_type == AudioSaveType.RELATIVE_NAME:
                for ld in lang_datas.values():
                    sp = os.path.join(save_path, str(save_type), content_group, ld["type"])
                    if not os.path.exists(sp):
                        os.makedirs(sp)


        def path_dest(s_type: AudioSaveType, s_name):
            return os.path.join(save_path, str(s_type), content_group, s_name)

        # audios = []
        for setting in music['MusicSettings']:
            song_name = setting['songName'].lower()

            postfix = ""
            if "intro" in song_name:
                postfix = "-intro"

            def pst(ii):
                if ii > 0:
                    return f"{ii + 1}{postfix}"
                return postfix

            audio_files = list(filter(lambda x: song_name == os.path.splitext(x.name)[0].lower(), audio_clips))

            # ssff, rate = sf.read(audio_files[0])

            for i, audio_file in enumerate(audio_files):
                ext = os.path.splitext(audio_file)[-1]

                if AudioSaveType.CODE_NAME in save_name_types:
                    save_name = f"{code_name}{pst(i)}{ext}"
                    shutil.copy(audio_file, path_dest(AudioSaveType.CODE_NAME, save_name))

                if AudioSaveType.TITLE_NAME in save_name_types and (title := cur_data.get("title")):
                    save_name = f"{title}{pst(i)}{ext}"
                    shutil.copy(audio_file, path_dest(AudioSaveType.TITLE_NAME, save_name))

                if AudioSaveType.RELATIVE_NAME in save_name_types:

                    keys_not_none = []
                    for k in lang_datas.keys():
                        if v := cur_data.get(k):
                            keys_not_none.append((k, v))

                    if len(keys_not_none) > 0:
                        if len(keys_not_none) > 1:
                            print(code_name, keys_not_none)

                        k, v = keys_not_none[0]
                        key_name = lang_datas[k]["key"]
                        cur_type = lang_datas[k]["type"]
                        cur_obj = lang_datas[k]["lang"].get(v)
                        name = cur_obj.get(key_name)

                        if prefix := cur_obj.get('prefix'):
                            flt = lambda x: not x.get("prefix") and x.get("charName") == name

                            main_object = list(filter(flt, lang_datas["unlockedByCharacter"]["lang"].values()))
                            if main_object or "megalo" in prefix.lower():
                                name = f"{prefix} {name}"

                        if v == "TP_CASTLE":
                            pass

                        j = i
                        save_name = f"Audio-{name}{pst(j)}{ext}"
                        while os.path.exists(path_dest(AudioSaveType.RELATIVE_NAME, cur_type + "\\" + save_name)):
                            j += 1
                            save_name = f"Audio-{name}{pst(j)}{ext}"


                        shutil.copy(audio_file, path_dest(AudioSaveType.RELATIVE_NAME, cur_type + "\\" + save_name))


    return save_path, None


if __name__ == "__main__":
    gen_audio(data_handler.get_data_path("musicData_Full.json"), [])
