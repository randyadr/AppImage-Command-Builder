<img width="920" height="675" alt="image" src="https://github.com/user-attachments/assets/4ba85437-c2d5-4673-b774-fddad651157f" />

# AppImage Command Builder

A simple Linux GUI tool that builds an AppImage from an `apt install` command.

Paste a command such as:

```bash
sudo apt install filelight
```

Then choose an AppImage name and output folder, click **Build AppImage**, and the tool will download the package, extract the `.deb` contents into an AppDir, create the AppRun and desktop files, download `appimagetool`, and build an `.AppImage`.

## Features

- Simple Tkinter GUI
- Accepts normal `apt install` style commands
- Downloads the selected package with `apt-get download`
- Optional checkbox to include direct package dependencies
- Automatically tries to detect the executable
- Automatically picks an icon when one is available
- Saves your last command, app name, output folder, dependency option, and sudo password
- Builds x86_64 AppImages using AppImageKit's `appimagetool`

## Screenshot

Add a screenshot here after you upload one to your repository.

```markdown
![AppImage Command Builder screenshot](screenshot.png)
```

## Requirements

This project is intended for Debian, Ubuntu, Linux Mint, and other `apt`-based Linux distributions.

You need:

- Python 3
- Tkinter for Python
- `apt`
- `apt-get`
- `apt-cache`
- `dpkg-deb`
- `wget`
- `sudo`
- `bash`
- `awk`, `sed`, and `grep`
- Optional: `glib-compile-schemas`, provided by `libglib2.0-bin`, for apps that include GSettings schemas

## Install dependencies

On Ubuntu, Debian, or Linux Mint:

```bash
sudo apt update
sudo apt install python3 python3-tk wget dpkg apt libglib2.0-bin
```

Most systems already include `bash`, `sudo`, `awk`, `sed`, and `grep`.

## Python dependencies

There are no external Python package dependencies.

The script only uses Python standard-library modules:

- `base64`
- `json`
- `os`
- `re`
- `shlex`
- `shutil`
- `stat`
- `subprocess`
- `threading`
- `tkinter`
- `pathlib`

Because of that, you do **not** need a `requirements.txt` file for pip packages. If you still want one, it can be empty or contain this comment:

```txt
# No pip dependencies required.
# Uses Python standard library only.
```

## How to run

Clone the repository:

```bash
git clone https://github.com/YOUR-USERNAME/appimage-command-builder.git
cd appimage-command-builder
```

Run the app:

```bash
python3 "AppImage Command Builder.py"
```

Or rename the file to a simpler command-friendly name:

```bash
mv "AppImage Command Builder.py" appimage_command_builder.py
python3 appimage_command_builder.py
```

## How to use

1. Open the program.
2. Paste an install command, for example:

   ```bash
   sudo apt install filelight
   ```

3. Enter an AppImage name.
4. Choose a build/output folder.
5. Optional: enable **Add direct dependencies** if the AppImage does not run correctly with only the main package.
6. Optional: click **Set sudo password** if you want the tool to run `sudo apt update` automatically.
7. Click **Build AppImage**.

When the build finishes, the AppImage will be created inside a folder named like this:

```text
YourAppName-appimage-build/
```

The final file will look like:

```text
YourAppName-x86_64.AppImage
```

## Notes and limitations

- This tool is intentionally simple.
- By default, it downloads only the package you typed.
- The dependency option only adds direct dependencies, not a full recursive dependency tree.
- Some applications may need extra libraries, plugins, environment variables, or manual fixes before they work well as an AppImage.
- Packages that do not install a GUI executable may fail automatic executable detection.
- This tool is designed for x86_64 systems.
- The generated AppImage is not guaranteed to be portable across every Linux distribution.

## Security note

The app can save your sudo password in:

```text
~/.config/appimage-command-builder/config.json
```

The script tries to restrict that config file to user-only permissions, but storing a sudo password on disk is still risky. For public GitHub releases, consider warning users clearly or changing the script to ask for the password each time instead of saving it.

## License

Choose a license before publishing. MIT is a common option for small open-source tools.

Example:

```text
MIT License
```

Then add a `LICENSE` file to your repository.


