import sys
import os
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
