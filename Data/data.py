import os
import json
import re


def clean_json(string):
    string = re.sub(",[ \t\r\n]+}", "}", string)
    string = re.sub(",[ \t\r\n]+]", "]", string)

    return string


def open_f(path):
    return open(path, "r", errors='ignore')


def gen_path(paths, name):
    return ([i for i in paths if f"{name}_data" in i.lower()] + [i for i in paths if name in i.lower()] + [""])[0]


def __generator_concatenate():
    path = os.path.split(__file__)[0]
    folder_to_save = path + "/Generated"
    if not os.path.exists(folder_to_save):
        os.makedirs(folder_to_save)

    names = [f.name.split("_")[0].split('.')[0].lower().replace("data", "") for f in os.scandir(path + "/Vampire Survivors")]

    vs = [f.path for f in os.scandir(path + "/Vampire Survivors")]
    ms = [f.path for f in os.scandir(path + "/Moonspell")]
    tf = [f.path for f in os.scandir(path + "/Foscari")]
    ch = [f.path for f in os.scandir(path + "/Chalcedony")]

    total_len = len(names)

    for i, name in enumerate(names):
        print(name)
        vspath = gen_path(vs, name)
        mspath = gen_path(ms, name)
        tfpath = gen_path(tf, name)
        chpath = gen_path(ch, name)

        try:
            with open_f(vspath) as vsfile:
                vsfile = vsfile.read()
                vsfile = clean_json(vsfile)
                outdata = json.loads(vsfile)
            vs.remove(vspath)

            if mspath:
                with open_f(mspath) as msfile:
                    outdata.update(json.loads(msfile.read()))
                ms.remove(mspath)

            if tfpath:
                with open_f(tfpath) as tffile:
                    outdata.update(json.loads(tffile.read()))
                tf.remove(tfpath)

            if chpath:
                with open_f(chpath) as chfile:
                    outdata.update(json.loads(chfile.read()))
                ch.remove(chpath)

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
