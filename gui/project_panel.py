import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal

from core.project import Project
from utils.file_utils import ensure_dir


class ProjectPanel(QWidget):
    project_changed = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.project = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        group = QGroupBox("Proyecto")
        group_layout = QVBoxLayout(group)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nombre:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Mi Podcast #1")
        name_layout.addWidget(self.name_input)
        group_layout.addLayout(name_layout)
        
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("Nuevo")
        self.new_btn.clicked.connect(self._new_project)
        btn_layout.addWidget(self.new_btn)
        
        self.open_btn = QPushButton("Abrir")
        self.open_btn.clicked.connect(self._open_project)
        btn_layout.addWidget(self.open_btn)
        
        self.save_btn = QPushButton("Guardar")
        self.save_btn.clicked.connect(self._save_project)
        btn_layout.addWidget(self.save_btn)
        
        group_layout.addLayout(btn_layout)
        layout.addWidget(group)
        layout.addStretch()
    
    def _new_project(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Atención", "Ingresa un nombre para el proyecto")
            return
        self.project = Project(name=name)
        ensure_dir("projects")
        self.project.save(f"projects/{name}.json")
        self.project_changed.emit(self.project)
        QMessageBox.information(self, "Listo", f"Proyecto '{name}' creado")
    
    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir Proyecto", "projects", "JSON (*.json)")
        if path:
            self.project = Project.load(path)
            self.name_input.setText(self.project.name)
            self.project_changed.emit(self.project)
    
    def _save_project(self):
        if self.project is None:
            QMessageBox.warning(self, "Atención", "No hay proyecto activo")
            return
        ensure_dir("projects")
        self.project.save(f"projects/{self.project.name}.json")
        QMessageBox.information(self, "Listo", "Proyecto guardado")
