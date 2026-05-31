from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl


class AudioPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self._select_file)
        layout.addWidget(QLabel("Archivos generados:"))
        layout.addWidget(self.file_list)
        
        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("Reproducir")
        self.play_btn.clicked.connect(self._play)
        btn_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("Detener")
        self.stop_btn.clicked.connect(self._stop)
        btn_layout.addWidget(self.stop_btn)
        
        self.load_btn = QPushButton("Cargar archivo")
        self.load_btn.clicked.connect(self._load_file)
        btn_layout.addWidget(self.load_btn)
        
        layout.addLayout(btn_layout)
        self.status_label = QLabel("Sin archivo")
        layout.addWidget(self.status_label)
    
    def _select_file(self, item: QListWidgetItem):
        path = item.data(0)
        self.player.setSource(QUrl.fromLocalFile(path))
        self.status_label.setText(f"Seleccionado: {path}")
    
    def _play(self):
        if self.player.source().isEmpty():
            return
        self.player.play()
    
    def _stop(self):
        self.player.stop()
    
    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir audio", "output", "Audio (*.mp3 *.wav *.flac)")
        if path:
            item = QListWidgetItem(path)
            item.setData(0, path)
            self.file_list.addItem(item)
            self.player.setSource(QUrl.fromLocalFile(path))
            self.status_label.setText(f"Cargado: {path}")
    
    def add_file(self, path: str):
        if not path:
            return
        item = QListWidgetItem(path)
        item.setData(0, path)
        self.file_list.addItem(item)
