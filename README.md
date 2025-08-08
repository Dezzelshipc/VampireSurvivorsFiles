# Vampire Survivors Files

Some data files of Vampire Survivors game.

Ripped from v1.12 + Moonspell + Foscari + Meeting + Guns + Ode + Diorama

[Vampire Survivors](https://store.steampowered.com/app/1794680/Vampire_Survivors/) by [poncle](https://poncle.games)

## Data Files

Game data files and DLC data files located in [Data](Data) folder.

## Unpacker (v0.15.3) - Data manager and Image generator

Run [unpacker.py](unpacker.py) with [run.bat](run.bat). It can unpack images, get language strings and split them to
different files and
languages, unpack images based on data files and make them with unified names, making (almost correct) animations
of characters and enemies.

### Getting started

Use [Python 3.12](https://www.python.org/downloads/) and install dependencies `pip install -r requirements.txt`

Enter paths to ripped assets with _**Change config**_, where each path leads to respective DLCs' assets
folders (`...\ExportedProject\Assets`, can be empty to automatically rip files).

* ***NOTE*** that ripping will **remove
  everything** in selected folders!

Using [AssetRipper](https://github.com/AssetRipper/AssetRipper)

* **Automatically** - Enter path to AssetRipper.exe and Steam folder for Vampire Survivors in config. Press *Magic
  button* and
  select DLCs to rip. Your previous settings for AssetRipper will be saved.

* **Manually** - Export with **Export Unity Project** with settings:

    * Turn off "_Skip StreamingAssets Folder_",
    * "_Bundled Assets Export Mode_" set to _**Group By Asset Type**_,
    * "_Script Content Level_" set to _**Level 2**_ (**Warning**: Levels 1,2 could crash ripper for some reason (in old
      versions), but only from Level 1 you can rip I2Languages. If it crashes try level 0),
    * "_Sprite Export Format_" set to _**Texture**_,
    * Tick "_Save Settings to Disk_" checkbox and click "Save" button to save settings.

        * Main game and each DLC must be ripped separately (You have to own DLCs).
          In `...\steamapps\common\Vampire Survivors` select `VampireSurvivors_Data` or numbered folders (DLCs) to open
          in
          AssetRipper.

_**Enable multiprocessing**_ can increase speed in some cases in exchange for "fully" loading CPU (and possibility of
overflowing memory for very big files).

* Currently for: _Get stage tilemap_, _Get unified audio_.

### Functions

* **Magic button to rip data automatically**: provided paths to _VS steam_ folder, _AssetRipper_ folder and _DLC_
  folders you can select what files to rip.

**Select image to unpack images**: select png sprite sheet from assets to split it into separate
sprites. ([Images/Generated/_By meta](Images) folder)

* **.. from spritesheets**: opens _spritesheets_ folder to unpack. (works when entered path in config)

* **Select image to unpack animations** and **.. from spritesheets**: select png sprite sheet from assets to split it
  into separate
  animations. (Animations are defined by sorting names of sprites)

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

* **Get stage tilemap**: Generate stage tile map from prefab file. Big prefabs (> 5 MB) have slow parse. One-block
  maps (i.e. from DLC) most likely will have file size higher 10 MB.

* **Get unified audio**: Copies audio files from musicData. Ability to select change of names: "Code names", "Audio
  titles", "Relative object names"
    * "Relative object names" requires split eng lang data.
    * Requires **[ffmpeg](https://ffmpeg.org)**.

## Future plans

* Keep support for new content updates and DLC.

* Add JsonDataHandler similar to MetaDataHandler.
* Rewrite Image gen to better pipeline (i.e. cache sprites).