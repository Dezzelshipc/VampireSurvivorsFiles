import os, json

names = [f.name.split("_")[0].split('.')[0].lower().replace("data", "") for f in os.scandir("../Vampire Survivors/")]

vs = [f.path for f in os.scandir("../Vampire Survivors/")]
ms = [f.path for f in os.scandir("../Moonspell/")]
tf = [f.path for f in os.scandir("../Foscari/")]
em = [f.path for f in os.scandir("../Meeting/")]

for name in names:
    vspath = ([i for i in vs if name in i.lower()] + [""])[0]
    mspath = ([i for i in ms if name in i.lower()] + [""])[0]
    tfpath = ([i for i in tf if name in i.lower()] + [""])[0]
    empath = ([i for i in em if name in i.lower()] + [""])[0]

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

    if empath:
        with open(tfpath, "r", encoding="UTF-8") as emfile:
            outdata.update(json.loads(emfile.read()))
        em.remove(empath)

    with open(name + "Data_Full.json", "w", encoding="UTF-8") as outfile:
        outfile.write(json.dumps(outdata, ensure_ascii=False, indent=2))

