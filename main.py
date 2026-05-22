import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import LoudlyApp

if __name__ == "__main__":
    app = LoudlyApp()
    app.mainloop()
