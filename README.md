# Vampire Survivors Files

Some data files of Vampire Survivors game.

Ripped from v1.14 + Moonspell + Foscari + Meeting + Guns + Ode + Diorama + Ante

[Vampire Survivors](https://store.steampowered.com/app/1794680/Vampire_Survivors/) by [poncle](https://poncle.games)

## Data Files

Game data files and DLC data files located in [Data](Data) folder.

## Unpacker (v0.16.5) - Data manager and Image generator

Run [unpacker.py](unpacker.py) with [run.bat](run.bat). It can unpack images, get language strings and split them to
different files and
languages, unpack images based on data files and make them with unified names, making (almost correct) animations
of characters and enemies.

### Getting started

Use [Python 3.12](https://www.python.org/downloads/) with _**tkinter**_ and install dependencies
`pip install -r requirements.txt`

Enter paths to folders where ripped assets for respective DLCs will be located with _**Change config**_.
(_OR_ enter paths where folders `...\ExportedProject\Assets` are located after ripping).

* ! ***NOTE*** that ripping will **<u>REMOVE EVERYTHING</u>** in selected folders!

Using [AssetRipper](https://github.com/AssetRipper/AssetRipper)

* **<u>Automatically</u>** (Recommended) - Enter path to AssetRipper.exe and Steam folder for Vampire Survivors in
  config. Press _**Magic button**_ and select DLCs to rip. Your previous settings for AssetRipper will be saved.


* **Manually** - Export with **Export Unity Project** with settings:

    * Turn off "_Skip StreamingAssets Folder_",
    * "_Bundled Assets Export Mode_" set to _**Group By Asset Type**_,
    * "_Script Content Level_" set to _**Level 2**_ (**Warning**: Levels 1,2 could crash ripper for some reason (in old
      versions), but only from Level 1 you can rip I2Languages. If it crashes try level 0),
    * "_Sprite Export Format_" set to _**Texture**_,
    * Tick "_Save Settings to Disk_" checkbox and click "Save" button to save settings.
        * Main game and each DLC must be ripped separately (You have to own DLCs).
          In `...\steamapps\common\Vampire Survivors` select `VampireSurvivors_Data` or numbered folders (DLCs) to open
          in AssetRipper.

_**Enable multiprocessing**_ can increase speed in some cases in exchange for "heavily" loading CPU (and possibility of
overflowing memory for very big files).

* Currently for: _Get stage tilemap_, _Get unified audio_, _Some necessary data processing
  (Parsing data, lang, metadata, etc.)_.

### Functions

| Button / Function                         | Action                                                                                                                                                                                                                             |
|-------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Change config                             | Opens config where you can select paths and toggle settings.                                                                                                                                                                       |
| Magic button to<br>rip data automatically | You can select which DLCs' files to rip.<br>(Requires _VS steam_, _AssetRipper_ and _DLC_ folders)                                                                                                                                 |
| Open last loaded folder                   | Opens folder that contains data from previous action.                                                                                                                                                                              |
| Select image to unpack images             | Select png spritesheet (png atlas) from assets to split it into separate sprites.                                                                                                                                                  |
| Select image to unpack animations         | Select png spritesheet (png atlas) from assets to split it into separate.<br>animations. (Animations are defined by sorting names of sprites)                                                                                      |
| .. from spritesheets                      | For corresponding action opens _spritesheets_ folder of VS data.                                                                                                                                                                   |
| Get language strings file                 | Copies and loads file with translations language stings. (I2Languages)<br>(Manually needs ripping with "_Script Content Level_" set to _**Level 2**_)                                                                              |
| Convert language strings to json          | Converts I2Languages yaml to json.                                                                                                                                                                                                 |
| Split language strings                    | Splits I2Languages file into different json files by type (general, weapon, character, etc.)<br>with ability to select multiple languages.                                                                                         |
| Get data from assets                      | Copies and loads data files from each DLC separately.                                                                                                                                                                              |
| Merge DLC data into same files            | Merges and loads data files from different DLC into files by type.                                                                                                                                                                 |
| Get unified images                        | By selecting data file (merged or not) produces main image for every object in file.<br>Tries to use english names from lang files.<br>Has some additional options to produce images with frames, animations or other.             |
| Get unified audio                         | Copies, makes and renames music files with ability to select change of names: <br>"Code names", "Audio titles", "Relative object names".<br>(Requires **[ffmpeg](https://ffmpeg.org)**)                                            |
| Get stage tilemap                         | Generate stage tile map from prefab file. Big prefabs (> 5 MB) may have slow parse. <br>Big one-block maps (i.e. from DLC) most likely will have file size higher 10 MB. <br>Recommended to use **Enable multiprocessing** option. |
| Create inv tilemap                        | Selecting generated tilemap you can enter tint value in base 10.<br>(See "tint" value in _Stage_ data files)<br>Creates images with tint and rotation (180 deg) and only with tint.                                                |

### Viewing code

* Vampire Survivors uses unity with il2cpp and can't be fully decompiled. However, there are tools to view some .dll
  files. Here are some of them:
    * [Il2CppDumper](https://github.com/Perfare/Il2CppDumper)
    * [dnSpy](https://github.com/dnSpy/dnSpy)
    * [ILSpy](https://github.com/icsharpcode/ILSpy)

## Future plans

* Keep support for new content updates and DLC.
* Rewrite Image gen to better pipeline.