import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import LoudlyApp
from services.logging_setup import setup_logging

# Límite de reintentos ante el bug conocido de Tkinter/customtkinter en el
# que una excepción durante la restauración de foco (p. ej. al cerrar un
# CTkToplevel) escapa de report_callback_exception y hace que mainloop()
# la propague, matando el proceso entero. El intérprete de Tcl no se ve
# afectado por esto, así que reentrar en mainloop() basta para recuperarse.
_MAX_MAINLOOP_RESTARTS = 5

if __name__ == "__main__":
    setup_logging()
    app = LoudlyApp()
    for attempt in range(1, _MAX_MAINLOOP_RESTARTS + 1):
        try:
            app.mainloop()
            break
        except Exception:
            logging.getLogger("uncaught").exception(
                "mainloop() interrumpido por una excepción, reintentando (%d/%d)",
                attempt,
                _MAX_MAINLOOP_RESTARTS,
            )
