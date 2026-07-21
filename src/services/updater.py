from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

from version import APP_VERSION

GITHUB_REPO = "avilesxd/loudly"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"
_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

_log = logging.getLogger(__name__)


def _parse_version(tag: str) -> tuple[int, ...]:
    """Extrae los componentes numéricos de un tag tipo 'v1.9.0' o
    'v1.9.0-rc1'. Los sufijos no numéricos se ignoran en lugar de lanzar
    ValueError, para no tumbar la comparación por un tag inesperado."""
    numeric = re.match(r"^\d+(\.\d+)*", tag.lstrip("v"))
    if not numeric:
        raise ValueError(f"tag de versión no reconocido: {tag!r}")
    return tuple(int(x) for x in numeric.group(0).split("."))


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
        _log.exception("fetch_latest falló")
        return None


def consume_update_log() -> None:
    """Si el bat de la última actualización dejó un log, lo vuelca al log
    de la app y lo borra. Permite diagnosticar un fallo de auto-update
    aunque el usuario no tenga consola."""
    log_file = os.path.join(tempfile.gettempdir(), "loudly_updater.log")
    if not os.path.isfile(log_file):
        return
    try:
        with open(log_file, encoding="ascii", errors="replace") as f:
            content = f.read()
        _log.info("Resultado de la última actualización:\n%s", content)
    except OSError:
        _log.exception("no se pudo leer loudly_updater.log")
    finally:
        try:
            os.remove(log_file)
        except OSError:
            pass


def is_newer(remote_tag: str) -> bool:
    try:
        return _parse_version(remote_tag) > _parse_version(APP_VERSION)
    except ValueError:
        _log.exception("is_newer no pudo comparar versiones")
        return False


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
    log_file = os.path.join(tempfile.gettempdir(), "loudly_updater.log")
    # El exe es onefile: mientras el proceso no termine del todo, Windows
    # mantiene el archivo bloqueado y "copy" falla con sharing violation.
    # Se reintenta con backoff en vez de un sleep fijo, que en máquinas
    # lentas no bastaba y dejaba la actualización sin aplicar.
    with open(bat, "w", encoding="ascii") as f:
        f.write(
            "@echo off\n"
            f'> "{log_file}" echo actualizando desde "{tmp_exe}" a "{current_exe}"\n'
            "set attempts=0\n"
            ":retry\n"
            "set /a attempts+=1\n"
            "timeout /t 1 /nobreak >nul\n"
            f'copy /y "{tmp_exe}" "{current_exe}" >> "{log_file}" 2>&1\n'
            "if errorlevel 1 (\n"
            "  if %attempts% lss 15 goto retry\n"
            f'  >> "{log_file}" echo copy fallo tras %attempts% intentos, '
            "se conserva la version anterior\n"
            ") else (\n"
            f'  >> "{log_file}" echo copy ok tras %attempts% intentos\n'
            f'  del "{tmp_exe}"\n'
            ")\n"
            f'start "" "{current_exe}"\n'
            'del "%~f0"\n'
        )
    subprocess.Popen(
        ["cmd.exe", "/c", bat],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return True
