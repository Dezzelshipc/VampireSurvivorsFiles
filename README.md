# Vampire Survivors Files

Some data files of Vampire Survivors game.

Ripped from v1.10 + Moonspell + Foscari + Meeting + Guns

[Vampire Survivors](https://store.steampowered.com/app/1794680/Vampire_Survivors/) by [poncle](https://poncle.games)

## Unpacker (v0.10)

Run [unpacker.py](unpacker.py). It can unpack images, get language strings and split them to different files and
languages, unpack images based on data files and make them with unifed names, making (almost correct) animations
of characters and enemies.

### Getting started

Use [Python 3.12](https://www.python.org/downloads/) and install dependencies `pip install -r requirements.txt`

Using [AssetRipper](https://github.com/AssetRipper/AssetRipper) **Export Unity Project** with settings:

* Turn off "_Skip StreamingAssets Folder_",
* "_Script Content Level_" to _**Level 0**_,
* "_Sprite Export Format_" set to _**Texture**_.

Main game and each DLC must be ripped separately (You have to own DLCs).
In `...\steamapps\common\Vampire Survivors` select `VampireSurvivors_Data` or numbered folders to open in AssetRipper.

Enter paths to ripped assets with _**Change config**_, where each path leads to respective DLCs' assets
folders (`...\ExportedProject\Assets`).

### Functions

**Select image to unpack**: select png sprite sheet from assets to split it into separate
sprites. ([Images/Generated/By meta](Images) folder)

* **.. from spritesheets**: opens _spritesheets_ folder to unpack. (works when entered path in config)

**Open last loaded folder**: opens folder that contains data from previous action.

**Get language strings file**: copies and converts to yaml file with translations language stings. (needs
config; [Translations](Translations) folder)

* **Convert language strings to json**: converts yaml file to json file.
* **Split language strings**: splits yaml file into different json files by type of string (general, weapon, character,
  etc.) with ability to select multiple languages.

**Get data from assets**: copies data files from each dlc separately. (needs config; [Data](Data) folder)

* **Merge dlc data into same files**: merges data files from different dlc into files by type (weapon, character, etc.)
* **Get images with unified names by data**: by selecting data file (merged or not) produces main image every object in
  file. ([Images](Images) folder)
    * Having split lang files with english strings, it uses names from it. (Correct names of objects rather than names
      of images)
    * Some of datas can produce images with frames or animations. (Selecting that datas will have corresponding
      checkboxes)
