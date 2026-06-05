import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QMessageBox, QGroupBox,
    QListWidget, QListWidgetItem, QSplitter
)
from PyQt6.QtCore import pyqtSignal, Qt

from core.project import Project, Voice
from utils.file_utils import ensure_dir
from gui.recorder_dialog import RecorderDialog


class VoiceManager(QWidget):
    voices_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.project = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # ===== TOP: Voice list =====
        list_group = QGroupBox("Voces del proyecto")
        list_layout = QVBoxLayout(list_group)
        
        self.voice_list = QListWidget()
        self.voice_list.setMinimumHeight(120)
        list_layout.addWidget(self.voice_list)
        
        # Quick action buttons above list
        quick_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("🎙️  Grabar mi voz")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #0b5ed7; }
        """)
        self.record_btn.setToolTip("Graba tu voz directamente con un texto guía")
        self.record_btn.clicked.connect(self._open_recorder)
        quick_layout.addWidget(self.record_btn)
        
        self.clone_expressive_btn = QPushButton("✨  Generar Voz Expressiva")
        self.clone_expressive_btn.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #5a359e; }
        """)
        self.clone_expressive_btn.setToolTip("Crea una voz clonada usando una referencia expresiva de Edge-TTS")
        self.clone_expressive_btn.clicked.connect(self._generate_expressive_clone)
        quick_layout.addWidget(self.clone_expressive_btn)
        
        quick_layout.addStretch()
        list_layout.addLayout(quick_layout)
        layout.addWidget(list_group)
        
        # ===== BOTTOM: Add voice form =====
        form_group = QGroupBox("Agregar voz manualmente")
        form = QVBoxLayout(form_group)
        
        # Row 1: Name + Type
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Nombre:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Mi Voz")
        row1.addWidget(self.name_input)
        
        row1.addWidget(QLabel("Tipo:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("Pre-entrenada", "pretrained")
        self.type_combo.addItem("Clonada", "cloned")
        row1.addWidget(self.type_combo)
        form.addLayout(row1)
        
        # Row 2: Engine + Language
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Motor:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("XTTS v2", "xtts")
        self.engine_combo.addItem("Bark", "bark")
        self.engine_combo.addItem("Edge-TTS (Natural)", "edge_tts")
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        row2.addWidget(self.engine_combo)
        
        row2.addWidget(QLabel("Idioma:"))
        self.lang_combo = QComboBox()
        for code in ["es", "en", "fr", "de", "it", "pt"]:
            self.lang_combo.addItem(code.upper(), code)
        row2.addWidget(self.lang_combo)
        form.addLayout(row2)
        
        # Row 3: Edge voice selector (hidden by default)
        self.edge_voice_layout = QHBoxLayout()
        self.edge_voice_layout.addWidget(QLabel("Voz Edge-TTS:"))
        self.edge_voice_combo = QComboBox()
        from core.edge_tts_engine import _EDGE_VOICES
        for vid, info in _EDGE_VOICES.items():
            self.edge_voice_combo.addItem(f"{info['name']}", vid)
        self.edge_voice_layout.addWidget(self.edge_voice_combo)
        form.addLayout(self.edge_voice_layout)
        self._set_edge_voice_visible(False)
        
        # Row 4: Reference file selector
        ref_layout = QHBoxLayout()
        self.ref_btn = QPushButton("📁  Seleccionar audio de referencia")
        self.ref_btn.clicked.connect(self._select_reference)
        ref_layout.addWidget(self.ref_btn)
        self.ref_label = QLabel("(ninguno seleccionado)")
        self.ref_label.setStyleSheet("color: #6c757d;")
        ref_layout.addWidget(self.ref_label)
        ref_layout.addStretch()
        form.addLayout(ref_layout)
        self.ref_path = ""
        
        # Row 5: Action buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕  Agregar Voz")
        self.add_btn.clicked.connect(self._add_voice)
        btn_layout.addWidget(self.add_btn)
        
        self.delete_btn = QPushButton("🗑️  Eliminar seleccionada")
        self.delete_btn.clicked.connect(self._delete_voice)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        form.addLayout(btn_layout)
        
        layout.addWidget(form_group)
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
    
    def _on_engine_changed(self, index):
        engine = self.engine_combo.currentData()
        is_edge = engine == "edge_tts"
        self._set_edge_voice_visible(is_edge)
        self.ref_btn.setEnabled(not is_edge)
        if is_edge:
            self.ref_label.setText("(clonación no disponible en Edge-TTS)")
            self.ref_label.setStyleSheet("color: #dc3545;")
        else:
            self.ref_label.setText("(ninguno seleccionado)" if not self.ref_path else os.path.basename(self.ref_path))
            self.ref_label.setStyleSheet("color: #6c757d;" if not self.ref_path else "color: #198754;")
    
    def _set_edge_voice_visible(self, visible: bool):
        for i in range(self.edge_voice_layout.count()):
            widget = self.edge_voice_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(visible)
    
    def _select_reference(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Audio de referencia", "",
            "Audio (*.wav *.mp3 *.flac)"
        )
        if path:
            self.ref_path = path
            self.ref_label.setText(os.path.basename(path))
            self.ref_label.setStyleSheet("color: #198754;")
    
    def _open_recorder(self):
        """Open the voice recorder dialog."""
        if self.project is None:
            QMessageBox.warning(self, "Atención", "Abre un proyecto primero")
            return
        
        dlg = RecorderDialog(self)
        dlg.audio_saved.connect(self._on_recorded_audio)
        dlg.exec()
    
    def _on_recorded_audio(self, path: str):
        """Called when the recorder saves an audio file."""
        if not os.path.exists(path):
            return
        self.ref_path = path
        self.ref_label.setText(os.path.basename(path))
        self.ref_label.setStyleSheet("color: #198754;")
        
        # Auto-fill form for cloned voice
        self.name_input.setText("Mi Voz")
        self.type_combo.setCurrentIndex(1)  # Clonada
        self.engine_combo.setCurrentIndex(0)  # XTTS v2
        
        QMessageBox.information(
            self, "Audio grabado",
            f"Audio guardado en:\n{path}\n\n"
            "Ahora haz clic en 'Agregar Voz' para registrarla en el proyecto."
        )
    
    def _add_voice(self):
        if self.project is None:
            QMessageBox.warning(self, "Atención", "Abre un proyecto primero")
            return
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Atención", "Ingresa un nombre para la voz")
            return
        voice_type = self.type_combo.currentData()
        engine = self.engine_combo.currentData()
        lang = self.lang_combo.currentData()
        
        if voice_type == "cloned" and not self.ref_path:
            QMessageBox.warning(self, "Atención", "Selecciona un audio de referencia para la voz clonada")
            return
        
        vid = f"voice_{len(self.project.voices) + 1}"
        speaker_id = None
        if engine == "edge_tts":
            speaker_id = self.edge_voice_combo.currentData()
        
        voice = Voice(
            id=vid,
            name=name,
            type=voice_type,
            engine=engine,
            language=lang,
            reference_path=self.ref_path if voice_type == "cloned" else None,
            speaker_id=speaker_id,
            speed=1.0
        )
        self.project.add_voice(voice)
        self._refresh_list()
        self.voices_changed.emit()
        
        # Clear form
        self.name_input.clear()
        self.ref_path = ""
        self.ref_label.setText("(ninguno seleccionado)")
        self.ref_label.setStyleSheet("color: #6c757d;")
    
    def _delete_voice(self):
        item = self.voice_list.currentItem()
        if not item or self.project is None:
            return
        voice_id = item.data(0)
        self.project.voices = [v for v in self.project.voices if v.id != voice_id]
        self._refresh_list()
        self.voices_changed.emit()
    
    def _generate_expressive_clone(self):
        """Genera automáticamente una voz clonada expresiva usando Edge-TTS + XTTS v2."""
        if self.project is None:
            QMessageBox.warning(self, "Atención", "Abre un proyecto primero")
            return
        
        ref_text = (
            "¡Hola! ¿Qué tal? Bienvenidos a nuestro podcast. "
            "Hoy tenemos noticias increíbles que contaros, ¡así que quedaos con nosotros!"
        )
        ref_path = os.path.join("voices", "clones", "ref_expressiva.wav")
        ensure_dir(os.path.dirname(ref_path))
        
        try:
            from core.edge_tts_engine import EdgeTTSEngine
            
            engine = EdgeTTSEngine()
            temp_voice = Voice(
                id="temp", name="Temp", type="pretrained", engine="edge_tts",
                language="es", speaker_id="es-ES-ElviraNeural"
            )
            engine.synthesize(ref_text, temp_voice, ref_path)
            
            vid = f"voice_{len(self.project.voices) + 1}"
            voice = Voice(
                id=vid,
                name="Voz Expressiva Clonada",
                type="cloned",
                engine="xtts",
                language="es",
                reference_path=os.path.abspath(ref_path),
                speed=1.0
            )
            self.project.add_voice(voice)
            self._refresh_list()
            self.voices_changed.emit()
            
            QMessageBox.information(
                self, "Voz Clonada Creada",
                f"Se ha generado la voz expresiva clonada.\n\n"
                f"Referencia: {ref_path}\n\n"
                f"Ahora puedes usar esta voz en las secciones del guion."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la voz clonada:\n{str(e)}")
