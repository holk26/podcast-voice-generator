import os
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QMessageBox, QFileDialog
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal


DEFAULT_SCRIPTS = [
    "¡Hola! Esta es mi voz para el podcast. Me llamo... y me encanta contar historias. "
    "Hoy vamos a hablar de tecnología, innovación y todo lo que está cambiando el mundo.",

    "Buenos días y bienvenidos. Soy tu anfitrión y estoy muy emocionado de estar aquí "
    "compartiendo contigo las noticias más interesantes del día.",

    "¡Qué tal! Espero que estés teniendo un gran día. "
    "Me presento: soy la voz detrás de este programa, y tengo muchas ganas de empezar.",
]


class RecorderDialog(QDialog):
    """Dialog to record voice reference audio with a reading script."""
    
    audio_saved = pyqtSignal(str)  # emits path to saved file
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grabar mi voz")
        self.setMinimumSize(700, 500)
        self._recording = False
        self._audio_buffer = []
        self._stream = None
        self._start_time = 0
        self._save_path = ""
        
        self._setup_ui()
        self._setup_timer()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Info label
        info = QLabel(
            "<b>Instrucciones:</b> Lee el texto de abajo en voz alta y natural. "
            "Evita ruidos de fondo. Graba al menos 10 segundos."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Script selector
        script_layout = QHBoxLayout()
        script_layout.addWidget(QLabel("Texto para leer:"))
        self.script_combo = QPushButton("Cambiar texto")
        self.script_combo.clicked.connect(self._rotate_script)
        script_layout.addWidget(self.script_combo)
        script_layout.addStretch()
        layout.addLayout(script_layout)
        
        # Script display
        self.script_edit = QTextEdit()
        self.script_edit.setPlainText(DEFAULT_SCRIPTS[0])
        self.script_edit.setReadOnly(True)
        self.script_edit.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.script_edit)
        self._script_index = 0
        
        # Timer display
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #495057;")
        layout.addWidget(self.time_label)
        
        # Level meter
        self.level_label = QLabel("Nivel de audio: --")
        self.level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.level_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("🔴  Grabar")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 14px 32px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #c82333; }
            QPushButton:disabled { background-color: #6c757d; }
        """)
        self.record_btn.clicked.connect(self._toggle_recording)
        btn_layout.addWidget(self.record_btn)
        
        self.save_btn = QPushButton("💾  Guardar referencia")
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #198754;
                color: white;
                font-size: 16px;
                padding: 14px 24px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #157347; }
            QPushButton:disabled { background-color: #6c757d; }
        """)
        self.save_btn.clicked.connect(self._save_audio)
        btn_layout.addWidget(self.save_btn)
        
        self.play_btn = QPushButton("▶️  Escuchar")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._play_preview)
        btn_layout.addWidget(self.play_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Status
        self.status_label = QLabel("Listo para grabar")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
    
    def _setup_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_ui)
        self._timer.start(100)  # 100ms update
    
    def _rotate_script(self):
        self._script_index = (self._script_index + 1) % len(DEFAULT_SCRIPTS)
        self.script_edit.setPlainText(DEFAULT_SCRIPTS[self._script_index])
    
    def _toggle_recording(self):
        if not self._recording:
            self._start_recording()
        else:
            self._stop_recording()
    
    def _start_recording(self):
        self._audio_buffer = []
        self._recording = True
        self._start_time = time.time()
        self.save_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.record_btn.setText("⏹️  Detener")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                font-size: 18px;
                font-weight: bold;
                padding: 14px 32px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #e0a800; }
        """)
        self.status_label.setText("Grabando... ¡lee el texto en voz alta!")
        
        try:
            self._stream = sd.InputStream(
                samplerate=24000,
                channels=1,
                dtype=np.float32,
                callback=self._audio_callback
            )
            self._stream.start()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo iniciar la grabación:\n{e}")
            self._recording = False
            self.record_btn.setText("🔴  Grabar")
    
    def _stop_recording(self):
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        duration = time.time() - self._start_time
        self.record_btn.setText("🔴  Grabar de nuevo")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 14px 32px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #c82333; }
            QPushButton:disabled { background-color: #6c757d; }
        """)
        
        if duration < 5:
            self.status_label.setText(f"⚠️ Grabación muy corta ({duration:.1f}s). Se necesitan al menos 6 segundos.")
            self.save_btn.setEnabled(False)
            self.play_btn.setEnabled(False)
        else:
            self.status_label.setText(f"✅ Grabación completada: {duration:.1f} segundos")
            self.save_btn.setEnabled(True)
            self.play_btn.setEnabled(True)
    
    def _audio_callback(self, indata, frames, time_info, status):
        if self._recording:
            self._audio_buffer.append(indata.copy())
    
    def _update_ui(self):
        if self._recording:
            elapsed = time.time() - self._start_time
            self.time_label.setText(f"{int(elapsed)//60:02d}:{int(elapsed)%60:02d} / grabando...")
            self.time_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #dc3545;")
            
            # Simple level meter from last buffer chunk
            if self._audio_buffer:
                last = self._audio_buffer[-1]
                level = np.sqrt(np.mean(last**2))
                db = 20 * np.log10(level + 1e-10)
                bar = "█" * int((db + 60) / 3)
                self.level_label.setText(f"Nivel de audio: {bar} ({db:.1f} dB)")
        else:
            self.time_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #495057;")
    
    def _get_audio_array(self):
        if not self._audio_buffer:
            return np.array([], dtype=np.float32)
        return np.concatenate(self._audio_buffer, axis=0).flatten()
    
    def _play_preview(self):
        audio = self._get_audio_array()
        if len(audio) == 0:
            return
        try:
            sd.play(audio, 24000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo reproducir: {e}")
    
    def _save_audio(self):
        audio = self._get_audio_array()
        if len(audio) == 0:
            QMessageBox.warning(self, "Atención", "No hay audio grabado")
            return
        
        default_dir = os.path.join("voices", "clones")
        os.makedirs(default_dir, exist_ok=True)
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar referencia de voz",
            os.path.join(default_dir, "mi_voz.wav"),
            "Audio WAV (*.wav)"
        )
        if not path:
            return
        
        try:
            sf.write(path, audio, 24000, subtype='PCM_16')
            self._save_path = path
            self.audio_saved.emit(path)
            QMessageBox.information(self, "Guardado", f"Referencia guardada en:\n{path}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")
    
    def closeEvent(self, event):
        if self._recording:
            self._stop_recording()
        event.accept()
