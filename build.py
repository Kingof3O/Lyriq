import subprocess
import sys
import os
import shutil

print("=== Compiling Optimized SpotifyLyrics Executable (v2.0) ===")

base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)

cmd = [
    sys.executable,
    "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--noupx",
    "--name", "SpotifyLyrics",
    "--icon", "icon.ico",
    "--add-data", "web;web",
    "--collect-all", "winsdk",
    "--hidden-import", "clr",
    "--hidden-import", "pythonnet",
    "--hidden-import", "webview.platforms.winforms",
    "--clean",
    "main.py"
]

print("Executing PyInstaller command:", " ".join(cmd))
res = subprocess.run(cmd)

if res.returncode == 0:
    exe_path = os.path.join(base_dir, "dist", "SpotifyLyrics.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\nSUCCESS! Optimized Standalone Executable created:")
        print(f"Path: {exe_path}")
        print(f"Size: {size_mb:.2f} MB")
        
        root_exe = os.path.join(base_dir, "SpotifyLyrics.exe")
        shutil.copyfile(exe_path, root_exe)
        print(f"Copied to workspace root: {root_exe}")
    else:
        print("Build finished but dist/SpotifyLyrics.exe was not found.")
else:
    print(f"PyInstaller build failed with return code {res.returncode}")
