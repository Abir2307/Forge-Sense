import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRY_POINT = ROOT / "safetwin" / "app.py"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_FILE = ROOT / "safetwin.spec"


def ensure_pyinstaller():
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller is not installed. Installing it now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build():
    ensure_pyinstaller()

    additional_assets = []

    for source, dest in [
        (ROOT / "safetwin" / "auth" / "assets", "./safetwin/auth/assets"),
        (ROOT / "assets", "./assets"),
        (ROOT / "config", "./config"),
        (ROOT / "data", "./data"),
    ]:
        if source.exists():
            additional_assets.append(f"{source};{dest}")

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "ForgeSense",
        "--icon",
        str(ROOT / "assets" / "logo.ico"),
        "--onedir",
        "--windowed",
    ]

    for asset in additional_assets:
        command.extend(["--add-data", asset])

    command.append(str(ENTRY_POINT))

    print("Building desktop app with:")
    print(" ".join(command))
    subprocess.check_call(command, cwd=str(ROOT))

    print(f"Build completed. Output directory: {DIST_DIR / 'ForgeSense'}")


if __name__ == "__main__":
    build()
