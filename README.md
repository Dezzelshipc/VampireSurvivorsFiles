# Vampire Survivors Files

Some data files of Vampire Survivors game.

Ripped from v1.10 + Moonspell + Foscari + Meeting + Guns

[Vampire Survivors](https://store.steampowered.com/app/1794680/Vampire_Survivors/) by [poncle](https://poncle.games)

## Unpacker (v0.9)

Run [unpacker.py](unpacker.py). It can unpack images, get language strings and split them to different files and
languages, unpack images based on data files and make them with unifed names, making (almost correct) animations
of characters and enemies.

### Getting started

Use [Python 3.12](https://www.python.org/downloads/) and install dependencies `pip install -r requirements.txt`

Using [AssetRipper](https://github.com/AssetRipper/AssetRipper) with setting "_Sprite Export Format_" set to
_**Texture**_. Main game and each DLC must be ripped separately (You have to own DLCs). 
In `...\steamapps\common\Vampire Survivors` select `VampireSurvivors_Data` or numbered folders.

In _**project's root folder**_ create _**.env**_ file with structure as _**[.env_example](.env_example)**_, where each path leads
to respective DLCs' assets folders (`...\ExportedProject\Assets`).