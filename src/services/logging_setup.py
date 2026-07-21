from __future__ import annotations

import logging
import os
import sys
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_NAME = "loudly.log"


def _log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    path = Path(base) / "Loudly" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging() -> None:
    """Configura logging a archivo y evita que sys.stdout/stderr sean None.

    En el build de PyInstaller (console=False) sys.stdout y sys.stderr son
    None. Cualquier código que escriba ahí directamente (incluido el
    report_callback_exception por defecto de Tkinter) lanza un
    AttributeError no capturado dentro del propio manejador de errores,
    lo que puede terminar el proceso sin dejar ningún rastro. Por eso se
    reemplazan por streams que redirigen a logging antes de crear la app.
    """
    log_file = _log_dir() / _LOG_NAME
    handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    if sys.stdout is None:
        sys.stdout = _LoggerWriter(logging.getLogger("stdout"), logging.INFO)
    if sys.stderr is None:
        sys.stderr = _LoggerWriter(logging.getLogger("stderr"), logging.ERROR)

    sys.excepthook = _log_uncaught_exception


class _LoggerWriter:
    def __init__(self, logger: logging.Logger, level: int):
        self._logger = logger
        self._level = level

    def write(self, message: str) -> None:
        message = message.strip()
        if message:
            self._logger.log(self._level, message)

    def flush(self) -> None:
        pass


def _log_uncaught_exception(exc_type, exc_value, exc_tb) -> None:
    logging.getLogger("uncaught").critical(
        "Excepción no capturada", exc_info=(exc_type, exc_value, exc_tb)
    )
