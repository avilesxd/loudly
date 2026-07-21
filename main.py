import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import LoudlyApp
from services.logging_setup import setup_logging

if __name__ == "__main__":
    setup_logging()
    app = LoudlyApp()
    app.mainloop()
