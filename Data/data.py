import json
import os
import re


def clean_json(string):
    string = re.sub(",[ \t\r\n]+}", "}", string)
    string = re.sub(",[ \t\r\n]+]", "]", string)
    return string


def open_f(path):
    return open(path, "r", errors='ignore', encoding="UTF-8-SIG")


def gen_path(paths, name):
    return ([i for i in paths if f"{name}_data" in i.lower()] + [i for i in paths if name in i.lower()] + [""])[0]


def __generator_concatenate():
    path = os.path.split(__file__)[0]
    folder_to_save = path + "/Generated"
    if not os.path.exists(folder_to_save):
        os.makedirs(folder_to_save)

    names = [f.name.split("_")[0].split('.')[0].lower().replace("data", "") for f in
             os.scandir(path + "/Vampire Survivors")]
    dlcs = ["Vampire Survivors", "Moonspell", "Foscari", "Meeting", "Guns"]

    dlc_paths = [[f.path for f in os.scandir(f"{path}/{dlc}")] for dlc in dlcs if os.path.exists(f"{path}/{dlc}")]

    total_len = len(names)

    for i, name in enumerate(names):
        paths = list(filter(lambda x: x, [gen_path(p, name) for p in dlc_paths]))

        try:
            outdata = {}
            for p in paths:
                with open_f(p) as file:
                    outdata.update(json.loads(clean_json(file.read())))

            with open(f"{folder_to_save}/{name}Data_Full.json", "w", encoding="UTF-8") as outfile:
                outfile.write(json.dumps(outdata, ensure_ascii=False, indent=2))

        except json.decoder.JSONDecodeError as e:
            print(f"{name} skipped: error {e}")

        yield i, total_len


def concatenate(is_gen=False):
    gen = __generator_concatenate()

    if is_gen:
        return gen
    else:
        for _ in gen:
            pass


if __name__ == "__main__":
    concatenate()
