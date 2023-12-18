import os
import json


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
        vspath = ([i for i in vs if name in i.lower()] + [""])[0]
        mspath = ([i for i in ms if name in i.lower()] + [""])[0]
        tfpath = ([i for i in tf if name in i.lower()] + [""])[0]
        chpath = ([i for i in ch if name in i.lower()] + [""])[0]

        with open(vspath, "r", encoding="UTF-8") as vsfile:
            outdata = json.loads(vsfile.read())
        vs.remove(vspath)

        if mspath:
            with open(mspath, "r", encoding="UTF-8") as msfile:
                outdata.update(json.loads(msfile.read()))
            ms.remove(mspath)

        if tfpath:
            with open(tfpath, "r", encoding="UTF-8") as tffile:
                outdata.update(json.loads(tffile.read()))
            tf.remove(tfpath)

        if chpath:
            with open(chpath, "r", encoding="UTF-8") as chfile:
                outdata.update(json.loads(chfile.read()))
            ch.remove(chpath)

        with open(f"{folder_to_save}/{name}Data_Full.json", "w", encoding="UTF-8") as outfile:
            outfile.write(json.dumps(outdata, ensure_ascii=False, indent=2))

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
