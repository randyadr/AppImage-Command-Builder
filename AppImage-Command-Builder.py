#!/usr/bin/env python3
"""
Simple AppImage Command Builder

Paste an apt install command such as:
  sudo apt install filelight

This version is intentionally simple:
- Downloads only the package you typed by default.
- Has one optional checkbox to add direct dependencies.
- Keeps the sudo password button and saves it.
"""

import base64
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, simpledialog

APP_TITLE = "AppImage Command Builder"
HOME = Path.home()
DEFAULT_BUILD_ROOT = Path("/mnt/Apps & Files") if Path("/mnt/Apps & Files").exists() else HOME
APPIMAGETOOL_URL = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
CONFIG_DIR = HOME / ".config" / "appimage-command-builder"
CONFIG_FILE = CONFIG_DIR / "config.json"


def safe_name(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[^A-Za-z0-9._+-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-._")
    return value or "portable-app"


def load_config() -> dict:
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(errors="ignore"))
    except Exception:
        pass
    return {}


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))
    try:
        CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def run_cmd(cmd, cwd=None, env=None, log=None, sudo_password=""):
    if log:
        log(f"\n$ {cmd}\n")

    full_cmd = cmd
    if sudo_password:
        quoted_pw = shlex.quote(sudo_password)
        full_cmd = (
            "sudo() {\n"
            f"  printf '%s\\n' {quoted_pw} | command sudo -S -p '' \"$@\"\n"
            "}\n"
            "export -f sudo\n"
            f"{cmd}\n"
        )

    proc = subprocess.Popen(
        ["bash", "-lc", full_cmd],
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    output = []
    for line in proc.stdout:
        output.append(line)
        if log:
            log(line)
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"Command failed with exit code {code}: {cmd}")
    return "".join(output)


def parse_apt_install_command(command: str):
    parts = shlex.split(command)
    packages = []
    skip_next = False
    for part in parts:
        if skip_next:
            skip_next = False
            continue
        if part in {"sudo", "apt", "apt-get", "install", "download"}:
            continue
        if part in {"-y", "--yes", "--no-install-recommends", "--install-recommends"}:
            continue
        if part in {"-o", "--option"}:
            skip_next = True
            continue
        if part.startswith("-"):
            continue
        if any(ch in part for ch in ";&|><`(){}[]"):
            continue
        packages.append(part)
    if not packages:
        raise ValueError("I could not find package names. Try: sudo apt install filelight")
    return packages


def direct_dependencies(packages, log):
    package_args = " ".join(shlex.quote(p) for p in packages)
    cmd = (
        "apt-cache depends --no-suggests --no-conflicts --no-breaks --no-replaces --no-enhances "
        f"{package_args} | awk '/^[[:space:]]*(PreDepends|Depends):/ {{print $2}}' | "
        "sed 's/[<>]//g' | grep -E '^[A-Za-z0-9][A-Za-z0-9.+:-]+$' | sort -u"
    )
    try:
        output = run_cmd(cmd, log=log)
    except Exception:
        return []
    deps = []
    for line in output.splitlines():
        name = line.strip()
        if name and name not in packages and name not in deps:
            deps.append(name)
    return deps


def package_has_candidate(pkg: str) -> bool:
    proc = subprocess.run(
        ["bash", "-lc", f"apt-cache policy {shlex.quote(pkg)} | awk '/Candidate:/ {{print $2; exit}}'"],
        capture_output=True,
        text=True,
    )
    candidate = proc.stdout.strip()
    return bool(candidate and candidate != "(none)")


def download_packages(packages, debs: Path, include_deps: bool, log):
    wanted = list(packages)
    if include_deps:
        wanted.extend(direct_dependencies(packages, log))

    final = []
    seen = set()
    for pkg in wanted:
        if pkg in seen:
            continue
        seen.add(pkg)
        if package_has_candidate(pkg):
            final.append(pkg)
        else:
            log(f"Skipping {pkg}: no apt candidate\n")

    if not final:
        raise RuntimeError("No downloadable apt packages were found.")

    log(f">>> Downloading {len(final)} package(s): {' '.join(final)}\n")
    cmd = f"cd {shlex.quote(str(debs))} && apt-get download {' '.join(shlex.quote(p) for p in final)}"
    run_cmd(cmd, log=log)


def is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def detect_executable(appdir: Path, packages, log):
    bin_dirs = [appdir / "usr/bin", appdir / "bin", appdir / "usr/sbin", appdir / "sbin"]
    names = [p.split(":", 1)[0] for p in packages]

    for name in names:
        for bdir in bin_dirs:
            p = bdir / name
            if is_executable(p):
                return str(p.relative_to(appdir))

    for desktop in sorted((appdir / "usr/share/applications").glob("*.desktop")):
        text = desktop.read_text(errors="ignore")
        for line in text.splitlines():
            if line.startswith("Exec="):
                exe = line.split("=", 1)[1].strip()
                exe = re.sub(r"\s+%[A-Za-z]", "", exe)
                try:
                    exe_name = Path(shlex.split(exe)[0]).name
                except Exception:
                    exe_name = Path(exe.replace('"', '').split()[0]).name
                for bdir in bin_dirs:
                    p = bdir / exe_name
                    if is_executable(p):
                        log(f"Detected executable from desktop file: {exe_name}\n")
                        return str(p.relative_to(appdir))

    for bdir in bin_dirs:
        if bdir.exists():
            for item in sorted(bdir.iterdir()):
                if is_executable(item):
                    log(f"Using first executable found: {item.name}\n")
                    return str(item.relative_to(appdir))

    raise RuntimeError("Could not detect an executable. This package may not install a GUI launcher.")


def pick_icon(appdir: Path, app_name: str):
    icons = []
    for root in [appdir / "usr/share/icons", appdir / "usr/share/pixmaps"]:
        if root.exists():
            for ext in ("*.png", "*.svg", "*.xpm"):
                icons.extend(root.rglob(ext))
    preferred = [safe_name(app_name).lower(), app_name.lower()]
    for icon in icons:
        if any(p in icon.name.lower() for p in preferred):
            return icon
    if icons:
        icons.sort(key=lambda p: (p.suffix.lower() == ".png", len(str(p))), reverse=True)
        return icons[0]
    return None


def build_appimage(command, app_name, build_root, include_deps, arch, log, sudo_password=""):
    packages = parse_apt_install_command(command)
    if not app_name.strip():
        app_name = packages[0]
    clean_app_name = safe_name(app_name)
    build_root = Path(build_root).expanduser()
    workdir = build_root / f"{clean_app_name}-appimage-build"
    debs = workdir / "debs"
    appdir = workdir / "AppDir"
    appimagetool = workdir / "appimagetool-x86_64.AppImage"
    output = workdir / f"{clean_app_name}-x86_64.AppImage"

    log(f">>> Package(s): {' '.join(packages)}\n")
    log(f">>> Build folder: {workdir}\n")

    shutil.rmtree(appdir, ignore_errors=True)
    shutil.rmtree(debs, ignore_errors=True)
    debs.mkdir(parents=True, exist_ok=True)
    appdir.mkdir(parents=True, exist_ok=True)

    run_cmd("sudo apt update", log=log, sudo_password=sudo_password)
    download_packages(packages, debs, include_deps, log)

    log("\n>>> Extracting .deb package(s) into AppDir\n")
    for deb in sorted(debs.glob("*.deb")):
        run_cmd(f"dpkg-deb -x {shlex.quote(str(deb))} {shlex.quote(str(appdir))}", log=log)

    schema_dir = appdir / "usr/share/glib-2.0/schemas"
    if schema_dir.exists() and shutil.which("glib-compile-schemas"):
        run_cmd(f"glib-compile-schemas {shlex.quote(str(schema_dir))}", log=log)

    exe_rel = detect_executable(appdir, packages, log)

    apprun = appdir / "AppRun"
    apprun.write_text(f'''#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:$HERE/bin:$HERE/usr/sbin:$HERE/sbin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib:$HERE/usr/lib/{arch}-linux-gnu:$HERE/lib:$HERE/lib/{arch}-linux-gnu:$HERE/usr/lib64:$HERE/lib64:${{LD_LIBRARY_PATH:-}}"
export XDG_DATA_DIRS="$HERE/usr/share:${{XDG_DATA_DIRS:-/usr/local/share:/usr/share}}"
export GSETTINGS_SCHEMA_DIR="$HERE/usr/share/glib-2.0/schemas"
exec "$HERE/{exe_rel}" "$@"
''')
    apprun.chmod(0o755)

    desktop = appdir / f"org.portable.{safe_name(clean_app_name).replace('-', '')}.desktop"
    desktop.write_text(f'''[Desktop Entry]
Type=Application
Name={app_name}
Exec=AppRun %U
Icon={clean_app_name}
Categories=Utility;
Terminal=false
''')

    icon = pick_icon(appdir, app_name)
    if icon:
        shutil.copy2(icon, appdir / f"{clean_app_name}{icon.suffix.lower()}")
    else:
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
        (appdir / f"{clean_app_name}.png").write_bytes(png)

    if not appimagetool.exists():
        run_cmd(f"wget -O {shlex.quote(str(appimagetool))} {shlex.quote(APPIMAGETOOL_URL)}", log=log)
        appimagetool.chmod(0o755)

    env = os.environ.copy()
    env["ARCH"] = "x86_64"
    log("\n>>> Building AppImage\n")
    run_cmd(f"{shlex.quote(str(appimagetool))} {shlex.quote(str(appdir))} {shlex.quote(str(output))}", cwd=workdir, env=env, log=log)
    output.chmod(0o755)
    log(f"\n>>> DONE\nCreated: {output}\n")
    return output


class BuilderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("920x650")
        self.minsize(760, 520)
        self.running = False
        self.config_data = load_config()

        self.command_var = tk.StringVar(value=self.config_data.get("command", "sudo apt install filelight"))
        self.name_var = tk.StringVar(value=self.config_data.get("app_name", "Filelight-Portable"))
        self.root_var = tk.StringVar(value=self.config_data.get("build_root", str(DEFAULT_BUILD_ROOT)))
        self.include_deps_var = tk.BooleanVar(value=self.config_data.get("include_deps", False))
        self.sudo_password = self.config_data.get("sudo_password", "")
        self.sudo_status_var = tk.StringVar(value="Sudo password: saved" if self.sudo_password else "Sudo password: not set")

        self.create_widgets()

    def persist_settings(self):
        self.config_data.update({
            "command": self.command_var.get(),
            "app_name": self.name_var.get(),
            "build_root": self.root_var.get(),
            "include_deps": bool(self.include_deps_var.get()),
            "sudo_password": self.sudo_password,
        })
        save_config(self.config_data)

    def create_widgets(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, text="Install command:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(root, textvariable=self.command_var).grid(row=0, column=1, sticky=tk.EW, padx=(8, 0))

        ttk.Label(root, text="AppImage name:").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Entry(root, textvariable=self.name_var).grid(row=1, column=1, sticky=tk.EW, padx=(8, 0), pady=(8, 0))

        ttk.Label(root, text="Build/output folder:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        folder_row = ttk.Frame(root)
        folder_row.grid(row=2, column=1, sticky=tk.EW, padx=(8, 0), pady=(8, 0))
        ttk.Entry(folder_row, textvariable=self.root_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(folder_row, text="Browse", command=self.browse).pack(side=tk.LEFT, padx=(8, 0))

        opts = ttk.Frame(root)
        opts.grid(row=3, column=1, sticky=tk.W, padx=(8, 0), pady=(8, 0))
        ttk.Checkbutton(opts, text="Add direct dependencies", variable=self.include_deps_var, command=self.persist_settings).pack(side=tk.LEFT)
        ttk.Button(opts, text="Set sudo password", command=self.set_sudo_password).pack(side=tk.LEFT, padx=(18, 0))
        ttk.Label(opts, textvariable=self.sudo_status_var).pack(side=tk.LEFT, padx=(8, 0))

        buttons = ttk.Frame(root)
        buttons.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(12, 8))
        self.build_button = ttk.Button(buttons, text="Build AppImage", command=self.start_build)
        self.build_button.pack(side=tk.LEFT)
        ttk.Button(buttons, text="Clear Log", command=lambda: self.log_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(buttons, text="Quit", command=self.destroy).pack(side=tk.RIGHT)

        ttk.Label(root, text="Log:").grid(row=5, column=0, columnspan=2, sticky=tk.W)
        self.log_text = tk.Text(root, wrap=tk.WORD)
        self.log_text.grid(row=6, column=0, columnspan=2, sticky=tk.NSEW)
        scroll = ttk.Scrollbar(root, orient=tk.VERTICAL, command=self.log_text.yview)
        scroll.grid(row=6, column=2, sticky=tk.NS)
        self.log_text.configure(yscrollcommand=scroll.set)

        root.columnconfigure(1, weight=1)
        root.rowconfigure(6, weight=1)

        self.log("Simple mode: downloads only the package you typed.\n")
        self.log("Turn on 'Add direct dependencies' only if the AppImage will not run.\n")

    def set_sudo_password(self):
        password = simpledialog.askstring("Sudo password", "Enter your sudo password. It will be saved:", show="*", parent=self)
        if password is None:
            return
        self.sudo_password = password
        self.persist_settings()
        self.sudo_status_var.set("Sudo password: saved" if password else "Sudo password: not set")

    def browse(self):
        chosen = filedialog.askdirectory(initialdir=self.root_var.get() or str(HOME))
        if chosen:
            self.root_var.set(chosen)
            self.persist_settings()

    def log(self, text):
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.update_idletasks()

    def start_build(self):
        if self.running:
            messagebox.showinfo("Already running", "A build is already running.")
            return
        command = self.command_var.get().strip()
        if not command:
            messagebox.showerror("Missing command", "Enter an apt install command first.")
            return
        self.persist_settings()
        self.running = True
        self.build_button.configure(state=tk.DISABLED)
        self.log("\n=== Starting build ===\n")

        def worker():
            try:
                output = build_appimage(
                    command=command,
                    app_name=self.name_var.get().strip(),
                    build_root=self.root_var.get().strip(),
                    include_deps=self.include_deps_var.get(),
                    arch="x86_64",
                    log=lambda s: self.after(0, self.log, s),
                    sudo_password=self.sudo_password,
                )
                self.after(0, messagebox.showinfo, "Done", f"Created AppImage:\n{output}")
            except Exception as exc:
                self.after(0, self.log, f"\nERROR: {exc}\n")
                self.after(0, messagebox.showerror, "Build failed", str(exc))
            finally:
                self.running = False
                self.after(0, self.build_button.configure, {"state": tk.NORMAL})

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    app = BuilderApp()
    app.mainloop()
