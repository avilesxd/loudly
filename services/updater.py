from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request

from version import APP_VERSION

GITHUB_REPO = "avilesxd/loudly"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"
_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(tag: str) -> tuple[int, ...]:
    return tuple(int(x) for x in tag.lstrip("v").split("."))


def fetch_latest() -> tuple[str, str] | None:
    """Consulta la API de GitHub. Devuelve (tag, download_url) o None si falla."""
    req = urllib.request.Request(_API_URL, headers={"User-Agent": "Loudly-Updater/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        tag = data["tag_name"]
        url = next(
            (
                a["browser_download_url"]
                for a in data.get("assets", [])
                if a["name"].endswith(".exe")
            ),
            None,
        )
        return (tag, url) if url else None
    except Exception:
        return None


def is_newer(remote_tag: str) -> bool:
    return _parse_version(remote_tag) > _parse_version(APP_VERSION)


def download_update(url: str, on_progress: callable | None = None) -> str:
    """Descarga el exe a un archivo temporal. Devuelve la ruta del archivo."""
    tmp_exe = os.path.join(tempfile.gettempdir(), "Loudly_update.exe")
    req = urllib.request.Request(url, headers={"User-Agent": "Loudly-Updater/1.0"})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(tmp_exe, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if on_progress and total:
                    on_progress(int(downloaded * 100 / total))
    return tmp_exe


def apply_update(tmp_exe: str) -> bool:
    """Lanza el updater y señala si la app debe cerrarse.

    En modo desarrollo abre el navegador y devuelve False.
    En el exe compilado crea el bat, lo lanza y devuelve True.
    """
    if not getattr(sys, "frozen", False):
        import webbrowser

        webbrowser.open(RELEASES_PAGE)
        return False

    current_exe = sys.executable
    bat = os.path.join(tempfile.gettempdir(), "loudly_updater.bat")
    with open(bat, "w", encoding="ascii") as f:
        f.write(
            "@echo off\n"
            "timeout /t 2 /nobreak >nul\n"
            f'copy /y "{tmp_exe}" "{current_exe}"\n'
            f'start "" "{current_exe}"\n'
            f'del "{tmp_exe}"\n'
            'del "%~f0"\n'
        )
    subprocess.Popen(
        ["cmd.exe", "/c", bat],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return True
