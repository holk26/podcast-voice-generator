from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QComboBox, QSpinBox, QGroupBox,
    QMessageBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import pyqtSignal

from core.project import Project, Section


class ScriptEditor(QWidget):
    project_updated = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.project = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.section_list = QListWidget()
        self.section_list.itemClicked.connect(self._load_section)
        layout.addWidget(QLabel("Secciones:"))
        layout.addWidget(self.section_list)
        
        group = QGroupBox("Editar Sección")
        form = QVBoxLayout(group)
        
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Título:"))
        self.title_input = QLineEdit()
        title_layout.addWidget(self.title_input)
        form.addLayout(title_layout)
        
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(QLabel("Voz:"))
        self.voice_combo = QComboBox()
        voice_layout.addWidget(self.voice_combo)
        form.addLayout(voice_layout)
        
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Velocidad:"))
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(50, 200)
        self.speed_spin.setValue(100)
        self.speed_spin.setSuffix("%")
        speed_layout.addWidget(self.speed_spin)
        form.addLayout(speed_layout)
        
        form.addWidget(QLabel("Texto:"))
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Escribe el guion aquí...")
        form.addWidget(self.text_edit)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Agregar Sección")
        self.add_btn.clicked.connect(self._add_section)
        btn_layout.addWidget(self.add_btn)
        
        self.update_btn = QPushButton("Actualizar")
        self.update_btn.clicked.connect(self._update_section)
        btn_layout.addWidget(self.update_btn)
        
        self.delete_btn = QPushButton("Eliminar")
        self.delete_btn.clicked.connect(self._delete_section)
        btn_layout.addWidget(self.delete_btn)
        
        form.addLayout(btn_layout)
        layout.addWidget(group)
    
    def set_project(self, project: Project):
        self.project = project
        self._refresh_list()
        self.voice_combo.clear()
        for voice in project.voices:
            self.voice_combo.addItem(voice.name, voice.id)
    
    def _refresh_list(self):
        self.section_list.clear()
        if self.project:
            for section in self.project.sections:
                item = QListWidgetItem(f"{section.id}: {section.title}")
                item.setData(0, section.id)
                self.section_list.addItem(item)
    
    def _load_section(self, item: QListWidgetItem):
        section_id = item.data(0)
        for section in self.project.sections:
            if section.id == section_id:
                self.title_input.setText(section.title)
                self.text_edit.setPlainText(section.text)
                self.speed_spin.setValue(int(section.speed * 100))
                idx = self.voice_combo.findData(section.voice_id)
                if idx >= 0:
                    self.voice_combo.setCurrentIndex(idx)
                break
    
    def _add_section(self):
        if self.project is None:
            QMessageBox.warning(self, "Atención", "Abre o crea un proyecto primero")
            return
        title = self.title_input.text().strip() or "Sin título"
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Atención", "El texto no puede estar vacío")
            return
        voice_id = self.voice_combo.currentData()
        speed = self.speed_spin.value() / 100.0
        self.project.add_section(title, text, voice_id, speed=speed)
        self._refresh_list()
        self.project_updated.emit(self.project)
    
    def _update_section(self):
        item = self.section_list.currentItem()
        if not item or self.project is None:
            return
        section_id = item.data(0)
        for section in self.project.sections:
            if section.id == section_id:
                section.title = self.title_input.text().strip()
                section.text = self.text_edit.toPlainText().strip()
                section.voice_id = self.voice_combo.currentData()
                section.speed = self.speed_spin.value() / 100.0
                self._refresh_list()
                self.project_updated.emit(self.project)
                break
    
    def _delete_section(self):
        item = self.section_list.currentItem()
        if not item or self.project is None:
            return
        section_id = item.data(0)
        self.project.remove_section(section_id)
        self._refresh_list()
        self.project_updated.emit(self.project)
