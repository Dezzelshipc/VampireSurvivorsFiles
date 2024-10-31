# Vampire Survivors Files

Some data files of Vampire Survivors game.

Ripped from v1.12 + Moonspell + Foscari + Meeting + Guns + Ode

[Vampire Survivors](https://store.steampowered.com/app/1794680/Vampire_Survivors/) by [poncle](https://poncle.games)

## Unpacker (v0.12)

Run [unpacker.py](unpacker.py) with [run.bat](run.bat). It can unpack images, get language strings and split them to
different files and
languages, unpack images based on data files and make them with unified names, making (almost correct) animations
of characters and enemies.

### Getting started

Use [Python 3.12](https://www.python.org/downloads/) and install dependencies `pip install -r requirements.txt`

Using [AssetRipper](https://github.com/AssetRipper/AssetRipper) **Export Unity Project** with settings:

* Turn off "_Skip StreamingAssets Folder_",
* "_Script Content Level_" set to _**Level 0**_ (Higher level could crash ripper for some reason, but only from Level 1
  you can rip I2Languages),
* "_Sprite Export Format_" set to _**Texture**_.

Main game and each DLC must be ripped separately (You have to own DLCs).
In `...\steamapps\common\Vampire Survivors` select `VampireSurvivors_Data` or numbered folders (DLCs) to open in
AssetRipper.

Enter paths to ripped assets with _**Change config**_, where each path leads to respective DLCs' assets
folders (`...\ExportedProject\Assets`).

* _**Enable multiprocessing**_ can increase speed in some cases in exchange for "fully" loading CPU (and possibility of
  overflowing memory for very big files).
    * Currently only for: _Get stage tilemap_.

### Functions

**Select image to unpack**: select png sprite sheet from assets to split it into separate
sprites. ([Images/Generated/_By meta](Images) folder)

* **.. from spritesheets**: opens _spritesheets_ folder to unpack. (works when entered path in config)

**Open last loaded folder**: opens folder that contains data from previous action.

**Get language strings file**: copies and converts to yaml file with translations language stings. (needs
config; [Translations](Translations) folder) (If it is laking strings then try ripping with "_Script Content Level_" set
to _**Level 1**_. If it crashes when ripping then manually copy data from resources.assets > I2Languages > Yaml)

* **Convert language strings to json**: converts yaml file to json file.
* **Split language strings**: splits yaml file into different json files by type of string (general, weapon, character,
  etc.) with ability to select multiple languages.

**Get data from assets**: copies data files from each dlc separately. (needs config; [Data](Data) folder)

* **Merge dlc data into same files**: merges data files from different dlc into files by type (weapon, character, etc.)
* **Get images with unified names by data**: by selecting data file (merged or not) produces main image for every object
  in file. ([Images](Images) folder)
    * Having split lang files with english strings, it uses names from it. (Correct names of objects rather than names
      from data file)
    * Some of datas can produce images with frames or animations. (Selecting that datas will have corresponding
      checkboxes)

* **Get stage tilemap**: Generate stage tile map from prefab file. Big prefabs (> 5 MB) have slow parse. One-block maps
  most likely will have file size higher 10 MB.
