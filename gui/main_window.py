from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QStatusBar, QMessageBox
)

from gui.project_panel import ProjectPanel
from gui.script_editor import ScriptEditor
from gui.voice_manager import VoiceManager
from gui.generation_panel import GenerationPanel
from gui.audio_player import AudioPlayer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Podcast Voice Generator")
        self.setMinimumSize(1200, 800)
        self._setup_ui()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.project_panel = ProjectPanel()
        self.script_editor = ScriptEditor()
        self.voice_manager = VoiceManager()
        self.generation_panel = GenerationPanel()
        self.audio_player = AudioPlayer()
        
        self.tabs.addTab(self.project_panel, "Proyecto")
        self.tabs.addTab(self.script_editor, "Guion")
        self.tabs.addTab(self.voice_manager, "Voces")
        self.tabs.addTab(self.generation_panel, "Generar")
        self.tabs.addTab(self.audio_player, "Reproductor")
        
        self.project_panel.project_changed.connect(self._on_project_changed)
        self.script_editor.project_updated.connect(self._on_project_updated)
        self.voice_manager.voices_changed.connect(self._on_voices_changed)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")
    
    def _on_project_changed(self, project):
        self.script_editor.set_project(project)
        self.voice_manager.set_project(project)
        self.generation_panel.set_project(project)
        self.status_bar.showMessage(f"Proyecto: {project.name}")
    
    def _on_project_updated(self, project):
        self.generation_panel.set_project(project)
    
    def _on_voices_changed(self):
        if self.project_panel.project:
            self.script_editor.set_project(self.project_panel.project)
    
    def show_error(self, message: str):
        QMessageBox.critical(self, "Error", message)
    
    def show_info(self, message: str):
        QMessageBox.information(self, "Info", message)
