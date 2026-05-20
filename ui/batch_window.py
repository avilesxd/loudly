import os
import tempfile
import threading
from dataclasses import dataclass, field
from tkinter import filedialog
from typing import Literal

import customtkinter as ctk
import soundfile as sf

from audio.automaster import apply_automaster
from audio.loader import load_audio

SUPPORTED = (
    ("Audio files", "*.wav *.mp3 *.flac *.aiff *.aif"),
    ("All files", "*.*"),
)


@dataclass
class BatchItem:
    path: str
    status: Literal["pending", "processing", "done", "error"] = "pending"
    message: str = ""


def _remastered_path(source_path: str) -> str:
    stem, _ = os.path.splitext(source_path)
    return stem + "_remastered.wav"
