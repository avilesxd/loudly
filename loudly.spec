from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import sys

block_cipher = None

datas = []
datas += collect_data_files("matchering")
datas += collect_data_files("customtkinter")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=collect_dynamic_libs("sounddevice"),
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "pedalboard",
        "matchering",
        "pyloudnorm",
        "sounddevice",
        "soundfile",
        "matplotlib",
        "matplotlib.backends.backend_tkagg",
        "miniaudio",
        "scipy",
        "scipy.signal",
        "scipy.ndimage",
        "numba",
        "numba.core",
        "llvmlite",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="Loudly",
    debug=False,
    console=False,
    icon=None,
    onefile=True,
)
