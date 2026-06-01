from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QComboBox, QCheckBox, QMessageBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, QThread

from core.project import Project
from core.batch_generator import BatchGenerator
from utils.config_manager import ConfigManager


class GenerationWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished_generation = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, project, generator):
        super().__init__()
        self.project = project
        self.generator = generator
    
    def run(self):
        try:
            self.generator.set_progress_callback(
                lambda current, total, msg: self.progress.emit(current, total, msg)
            )
            results = self.generator.run(self.project)
            self.finished_generation.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class GenerationPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.project = None
        self.generator = BatchGenerator()
        self.worker = None
        self._setup_ui()
        self._setup_engines()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        group = QGroupBox("Configuración de generación")
        form = QVBoxLayout(group)
        
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Formato:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("MP3", "mp3")
        self.format_combo.addItem("WAV", "wav")
        self.format_combo.addItem("FLAC", "flac")
        format_layout.addWidget(self.format_combo)
        form.addLayout(format_layout)
        
        self.normalize_check = QCheckBox("Normalizar audio")
        self.normalize_check.setChecked(True)
        form.addWidget(self.normalize_check)
        
        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Generar Audio")
        self.generate_btn.clicked.connect(self._start_generation)
        btn_layout.addWidget(self.generate_btn)
        
        self.stop_btn = QPushButton("Detener")
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        form.addLayout(btn_layout)
        layout.addWidget(group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Listo")
        layout.addWidget(self.status_label)
        layout.addStretch()
    
    def _setup_engines(self):
        cm = ConfigManager()
        try:
            from core.xtts_engine import XTTSEngine
            xtts = XTTSEngine(device=cm.get("gpu.device"))
            self.generator.register_engine("xtts", xtts)
        except Exception as e:
            print(f"XTTS no disponible: {e}")
        try:
            from core.bark_engine import BarkEngine
            bark = BarkEngine(device=cm.get("gpu.device"))
            self.generator.register_engine("bark", bark)
        except Exception as e:
            print(f"Bark no disponible: {e}")
    
    def set_project(self, project: Project):
        self.project = project
        if project:
            fmt = self.format_combo.currentData()
            project.settings.output_format = fmt
            project.settings.normalize_audio = self.normalize_check.isChecked()
    
    def _start_generation(self):
        if self.project is None or len(self.project.sections) == 0:
            QMessageBox.warning(self, "Atención", "No hay secciones para generar")
            return
        self.generator.reset()
        self.generator.add_project(self.project)
        
        self.generate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        self.worker = GenerationWorker(self.project, self.generator)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished_generation.connect(self._generation_finished)
        self.worker.error.connect(self._generation_error)
        self.worker.start()
    
    def _update_progress(self, current, total, msg):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"{current}/{total}: {msg}")
    
    def _generation_finished(self, results):
        self.generate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        completed = sum(1 for r in results if r.status == "completed")
        QMessageBox.information(self, "Listo", f"Generación completada: {completed}/{len(results)} secciones")
        self.status_label.setText(f"Completado: {completed}/{len(results)}")
    
    def _generation_error(self, error_msg):
        self.generate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Error", f"Error durante generación: {error_msg}")
