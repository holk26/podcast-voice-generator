import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QMessageBox, QGroupBox,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import pyqtSignal

from core.project import Project, Voice
from utils.file_utils import ensure_dir


class VoiceManager(QWidget):
    voices_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.project = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.voice_list = QListWidget()
        layout.addWidget(QLabel("Voces del proyecto:"))
        layout.addWidget(self.voice_list)
        
        group = QGroupBox("Agregar Voz")
        form = QVBoxLayout(group)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nombre:"))
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_input)
        form.addLayout(name_layout)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("Pre-entrenada", "pretrained")
        self.type_combo.addItem("Clonada", "cloned")
        type_layout.addWidget(self.type_combo)
        form.addLayout(type_layout)
        
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("Motor:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("XTTS v2", "xtts")
        self.engine_combo.addItem("Bark", "bark")
        engine_layout.addWidget(self.engine_combo)
        form.addLayout(engine_layout)
        
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Idioma:"))
        self.lang_combo = QComboBox()
        for code in ["es", "en", "fr", "de", "it", "pt"]:
            self.lang_combo.addItem(code.upper(), code)
        lang_layout.addWidget(self.lang_combo)
        form.addLayout(lang_layout)
        
        self.ref_btn = QPushButton("Seleccionar audio de referencia (para clonación)")
        self.ref_btn.clicked.connect(self._select_reference)
        form.addWidget(self.ref_btn)
        self.ref_path = ""
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Agregar Voz")
        self.add_btn.clicked.connect(self._add_voice)
        btn_layout.addWidget(self.add_btn)
        
        self.delete_btn = QPushButton("Eliminar")
        self.delete_btn.clicked.connect(self._delete_voice)
        btn_layout.addWidget(self.delete_btn)
        
        form.addLayout(btn_layout)
        layout.addWidget(group)
        layout.addStretch()
    
    def set_project(self, project: Project):
        self.project = project
        self._refresh_list()
    
    def _refresh_list(self):
        self.voice_list.clear()
        if self.project:
            for voice in self.project.voices:
                item = QListWidgetItem(f"{voice.name} ({voice.type}, {voice.engine})")
                item.setData(0, voice.id)
                self.voice_list.addItem(item)
    
    def _select_reference(self):
        path, _ = QFileDialog.getOpenFileName(self, "Audio de referencia", "", "Audio (*.wav *.mp3 *.flac)")
        if path:
            self.ref_path = path
            self.ref_btn.setText(f"Referencia: {os.path.basename(path)}")
    
    def _add_voice(self):
        if self.project is None:
            QMessageBox.warning(self, "Atención", "Abre un proyecto primero")
            return
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Atención", "Ingresa un nombre")
            return
        voice_type = self.type_combo.currentData()
        engine = self.engine_combo.currentData()
        lang = self.lang_combo.currentData()
        
        vid = f"voice_{len(self.project.voices) + 1}"
        voice = Voice(
            id=vid,
            name=name,
            type=voice_type,
            engine=engine,
            language=lang,
            reference_path=self.ref_path if voice_type == "cloned" else None
        )
        self.project.add_voice(voice)
        self._refresh_list()
        self.voices_changed.emit()
    
    def _delete_voice(self):
        item = self.voice_list.currentItem()
        if not item or self.project is None:
            return
        voice_id = item.data(0)
        self.project.voices = [v for v in self.project.voices if v.id != voice_id]
        self._refresh_list()
        self.voices_changed.emit()
