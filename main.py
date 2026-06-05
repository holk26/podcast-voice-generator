import sys
import os

# Fix CUDA 13.0 library path for PyTorch 2.11+ (RTX 50-series support)
_venv_lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv311", "lib", "python3.11", "site-packages", "nvidia", "cu13", "lib")
if os.path.isdir(_venv_lib):
    _ld = os.environ.get("LD_LIBRARY_PATH", "")
    if _venv_lib not in _ld:
        os.environ["LD_LIBRARY_PATH"] = f"{_venv_lib}{':' + _ld if _ld else ''}"

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from utils.file_utils import ensure_dir


def main():
    ensure_dir("projects")
    ensure_dir("output")
    ensure_dir("voices/clones")
    ensure_dir("music")
    
    app = QApplication(sys.argv)
    app.setApplicationName("Podcast Voice Generator")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
