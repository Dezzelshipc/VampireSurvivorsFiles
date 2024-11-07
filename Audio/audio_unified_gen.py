from enum import Enum

from Config.config import Config
import Data.data as data_handler
from unityparser import UnityDocument

import os
import shutil


class AudioSaveType(Enum):
    CODE_NAME = "Code names"
    TITLE_NAME = "Audio titles"  # change for lang file?

    # RELATIVE_NAME = "Relative object names"

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


def gen_audio(music_json_path: os.PathLike, save_name_types: list[AudioSaveType]) -> str:
    f_path, f_name = os.path.split(__file__)
    if len(save_name_types) <= 0:
        return f_path

    save_path = os.path.join(f_path, "Generated")
    config = Config()

    music_data = data_handler.get_data_file(music_json_path)

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

            for setting in music['MusicSettings']:
                song_name = setting['songName'].lower()

                postfix = ""
                if "intro" in song_name:
                    postfix = "-intro"

                audio_files = list(filter(lambda x: song_name == os.path.splitext(x.name)[0].lower(), audio_clips))

                for i, audio_file in enumerate(audio_files):
                    if i > 0:
                        postfix = f"{i + 1}{postfix}"
                        print(audio_file)

                    if save_type == AudioSaveType.CODE_NAME:
                        save_name = f"{code_name}{postfix}{os.path.splitext(audio_file)[-1]}"
                        shutil.copy(audio_file, os.path.join(sp, save_name))
                    elif save_type == AudioSaveType.TITLE_NAME and (title := cur_data.get("title")):
                        save_name = f"{title}{postfix}{os.path.splitext(audio_file)[-1]}"
                        shutil.copy(audio_file, os.path.join(sp, save_name))

    return save_path


if __name__ == "__main__":
    gen_audio(data_handler.get_data_path("musicData_Full.json"), [])
