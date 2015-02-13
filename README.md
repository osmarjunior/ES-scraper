ES-scraper
=====================
```
usage: scraper.py [-h] [-w value] [-noimg] [-v] [-f] [-crc] [-p]

ES-scraper, a scraper for EmulationStation

optional arguments:
  -h, --help  show this help message and exit
  -w value    defines a maximum width (in pixels) for boxarts (anything above
              that will be resized to that value)
  -noimg      disables boxart downloading
  -v          verbose output
  -f          force re-scraping (ignores and overwrites the current gamelist)
  -crc        CRC scraping
  -p          partial scraping (per console)
  -m          manual mode (choose from multiple results)
  -newpath    gamelist.xml & boxart are written in $HOME/.emulationstation/%NAME%/
  -fix        temporary thegamesdb missing platform fix
```

Quick script written in Python that uses various online sources to scrape artwork and game info and saves it as XML files to be read by EmulationStation.

If you haven't done so, please update ES before running this script.

For image resizing to work, you need to install Pillow:
```
sudo pip install Pillow
```

Usage
=====================
* Open your systems config file ($HOME/.emulationstation/es_systems.cfg) and append the corresponding [platform ID](#platform-list) to each system:

```
<systemList>
    <!-- Here's an example system to get you started. -->
    <system>
        <!-- A short name, used internally. -->
        <name>snes</name>

        <!-- A "pretty" name, displayed in the menus and such. This one is optional. -->
        <fullname>Super Nintendo Entertainment System</fullname>

        <!-- The path to start searching for ROMs in. '~' will be expanded to $HOME or %HOMEPATH%, depending on platform.
        All subdirectories (and non-recursive links) will be included. -->
        <path>~/ROMS/SNES</path>

        <!-- A list of extensions to search for, delimited by any of the whitespace characters (", \r\n\t").
        You MUST include the period at the start of the extension! It's also case sensitive. -->
        <extension>.smc .sfc .SMC .SFC</extension>

        <!-- The shell command executed when a game is selected. A few special tags are replaced if found in a command, like %ROM% (see below). -->
        <command>snesemulator %ROM%</command>
        <!-- This example would run the bash command "snesemulator /home/user/roms/snes/Super\ Mario\ World.sfc". -->

        <!-- The platform(s) to use when scraping. You can see the full list of accepted platforms in src/PlatformIds.cpp.
        It's case sensitive, but everything is lowercase. This tag is optional.
        You can use multiple platforms too, delimited with any of the whitespace characters (", \r\n\t"), eg: "genesis, megadrive" -->
        <platform>snes</platform>

        <!-- The theme to load from the current theme set. See THEMES.md for more information.
        This tag is optional; if not set, it will use the value of <name>. -->
        <theme>snes</theme>
        <platformid>6</platformid>
    </system>
</systemList>
```

* Run the script.

Platform List
=====================
Below is a list of all available platforms in the database and their IDs.

```
[25] 3DO
[4911] Amiga
[23] Arcade
[22] Atari 2600
[26] Atari 5200
[27] Atari 7800
[28] Atari Jaguar
[29] Atari Jaguar CD
[30] Atari XE
[31] Colecovision
[40] Commodore 64
[32] Intellivision
[37] Mac OS
[14] Microsoft Xbox
[15] Microsoft Xbox 360
[24] NeoGeo
[4912] Nintendo 3DS
[3] Nintendo 64
[8] Nintendo DS
[7] Nintendo Entertainment System (NES)
[4] Nintendo Game Boy
[5] Nintendo Game Boy Advance
[41] Nintendo Game Boy Color
[2] Nintendo GameCube
[9] Nintendo Wii
[38] Nintendo Wii U
[1] PC
[33] Sega 32X
[21] Sega CD
[16] Sega Dreamcast
[20] Sega Game Gear
[18] Sega Genesis
[35] Sega Master System
[36] Sega Mega Drive
[17] Sega Saturn
[10] Sony Playstation
[11] Sony Playstation 2
[12] Sony Playstation 3
[39] Sony Playstation Vita
[13] Sony PSP
[6] Super Nintendo (SNES)
[34] TurboGrafx 16
```
