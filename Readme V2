# AppImage Command Builder v4 CMake GUI

A Tkinter-based Linux GUI for building AppImages from several kinds of inputs, including apt packages, Flatpak apps, local `.deb` bundles, source-code folders, archives, existing AppImages, and runnable launcher files.

## What it does

AppImage Command Builder helps turn install commands or local app sources into portable `.AppImage` files. It can:

- Build from apt commands such as `sudo apt install kodi` or `sudo apt install filelight`
- Build from Flatpak app IDs and commands such as `org.videolan.VLC`, `flatpak run org.videolan.VLC`, or `flatpak install flathub org.videolan.VLC`
- Build from local `.flatpak` and `.flatpakref` files
- Scan folders for `.deb` files, archives, AppDirs, AppImages, runnable scripts, and source projects
- Attempt to build CMake, Meson, Make, configure-script, and prebuilt Node/Electron-style folders
- Copy built executables into the AppDir when a CMake install target succeeds but does not install a launcher
- Let you choose an executable override when auto-detection picks the wrong launcher
- Let you choose a custom icon
- Optionally launch the generated AppImage in its own terminal window

## Supported inputs

Paste or select any of these in the command/source box:

```bash
sudo apt install kodi
sudo apt install filelight
flatpak install flathub org.videolan.VLC
flatpak run org.videolan.VLC
org.videolan.VLC
/path/to/app.flatpak
/path/to/app.flatpakref
/path/to/package.deb
/path/to/archive.tar.xz
/path/to/archive.zip
/path/to/folder
/path/to/existing.AppImage
/path/to/launcher.sh
```

## Requirements

This is a Linux-only tool. It expects an apt-based system for apt package building, such as Debian, Ubuntu, Linux Mint, KDE neon, Pop!_OS, or a compatible distro.

Python dependencies are standard-library only. There is no `requirements.txt` needed for pip packages.

Install common system dependencies:

```bash
sudo apt update
sudo apt install python3 python3-tk wget dpkg apt flatpak file tar unzip xz-utils zstd libglib2.0-bin
```

For source-code builds, install extra build tools:

```bash
sudo apt install build-essential cmake ninja-build meson pkg-config git
```

Optional terminal launch support:

```bash
sudo apt install konsole
```

Other supported terminal emulators include `gnome-terminal`, `xfce4-terminal`, `mate-terminal`, `lxterminal`, `kitty`, `alacritty`, and `xterm`.

See [`DEPENDENCIES.md`](DEPENDENCIES.md) for the full dependency list.

## How to run

Clone or download the project, then run:

```bash
python3 "AppImage Command Builder v4 CMAKE GUI.py"
```

## Basic usage

1. Enter an apt command, Flatpak app ID, local file, archive, or folder path.
2. Enter the AppImage name you want.
3. Choose a build/output folder.
4. Use **Executable override** if the app builds but launches the wrong executable.
5. Use **Icon override** if you want a custom `.png`, `.svg`, or `.xpm` icon.
6. Click **Build AppImage**.

The output is created inside a folder named like:

```text
<AppName>-appimage-build/<AppName>-x86_64.AppImage
```

## Notes about Flatpak builds

Flatpaks are designed to run inside Flatpak's sandbox/runtime system. This project makes a best-effort AppImage by copying the Flatpak app files and runtime files into an AppDir and setting runtime paths manually.

Simple GTK, Qt, and Electron apps may work. Apps that require portals, sandbox permissions, D-Bus services, GPU extensions, or Flatpak extension points may need manual fixes.

## Notes about source builds

When a source folder is selected, the builder looks for common build markers such as:

- `CMakeLists.txt`
- `meson.build`
- `configure`
- `Makefile`
- `package.json`

For CMake projects, the builder uses a temporary space-free build directory and tries to install into the AppDir. If install succeeds but no launcher appears, it copies built executables and libraries into the AppDir as a fallback.

## Configuration

Settings are saved here:

```text
~/.config/appimage-command-builder/config.json
```

This may include the saved sudo password if you use the built-in sudo password button. Be careful when sharing your config file.

## Security warning

Only build apps from sources you trust. This tool can run package managers, build tools, scripts, and selected local executables. Review unknown source folders and install commands before building.

## License

Add your preferred license here, such as MIT, GPL-3.0, or another license before publishing publicly.
