import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.logging_setup import setup_logging

setup_logging()

from app import LoudlyApp

if __name__ == "__main__":
    app = LoudlyApp()
    app.mainloop()
