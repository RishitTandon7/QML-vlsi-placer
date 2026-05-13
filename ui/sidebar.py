"""
Sidebar Panel: Design config, QML settings, placement parameters (Compact)
"""

import logging
from typing import Dict
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QLabel, QSpinBox,
                             QDoubleSpinBox, QSlider, QCheckBox, QPushButton,
                             QComboBox, QLineEdit, QFileDialog, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)


class SidebarPanel(QWidget):
    """Compact configuration sidebar panel."""
    
    run_placement = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setMaximumWidth(220)
        self.setStyleSheet("QGroupBox { padding-top: 6px; margin-top: 4px; } QLabel { font-size: 9px; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Design section (compact)
        design_box = QGroupBox("Design")
        design_layout = QFormLayout(design_box)
        design_layout.setContentsMargins(4, 4, 4, 4)
        design_layout.setSpacing(3)
        design_layout.addRow("Name:", QLabel("CA234"))
        design_layout.addRow("PDK:", QLabel("Sky130 HD"))
        design_layout.addRow("Cells:", QLabel("—"))
        design_layout.addRow("Die:", QLabel("— µm"))
        btn_design = QPushButton("📂 Load DEF")
        btn_design.setMaximumHeight(20)
        design_layout.addRow(btn_design)
        layout.addWidget(design_box)
        
        # Placement config (compact)
        place_box = QGroupBox("Placement")
        place_layout = QFormLayout(place_box)
        place_layout.setContentsMargins(4, 4, 4, 4)
        place_layout.setSpacing(3)
        
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.1, 0.9)
        self.density_spin.setValue(0.55)
        self.density_spin.setSingleStep(0.05)
        self.density_spin.setMaximumHeight(20)
        place_layout.addRow("Density:", self.density_spin)
        
        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(500, 5000)
        self.iterations_spin.setValue(2000)
        self.iterations_spin.setSingleStep(100)
        self.iterations_spin.setMaximumHeight(20)
        place_layout.addRow("Iterations:", self.iterations_spin)
        
        self.optimizer_combo = QComboBox()
        self.optimizer_combo.addItems(["Nesterov", "Adam", "SGD"])
        self.optimizer_combo.setMaximumHeight(20)
        place_layout.addRow("Optimizer:", self.optimizer_combo)
        
        layout.addWidget(place_box)
        
        # QML config (compact)
        qml_box = QGroupBox("QML Config")
        qml_layout = QFormLayout(qml_box)
        qml_layout.setContentsMargins(4, 4, 4, 4)
        qml_layout.setSpacing(3)
        
        self.qubits_spin = QSpinBox()
        self.qubits_spin.setRange(4, 16)
        self.qubits_spin.setValue(8)
        self.qubits_spin.setMaximumHeight(20)
        qml_layout.addRow("Qubits:", self.qubits_spin)
        
        self.layers_spin = QSpinBox()
        self.layers_spin.setRange(1, 8)
        self.layers_spin.setValue(4)
        self.layers_spin.setMaximumHeight(20)
        qml_layout.addRow("Layers:", self.layers_spin)
        
        self.qml_enable = QCheckBox("Enable QML")
        self.qml_enable.setChecked(True)
        qml_layout.addRow(self.qml_enable)
        
        layout.addWidget(qml_box)
        
        # Action buttons
        layout.addSpacing(8)
        
        self.run_button = QPushButton("▶ RUN QML")
        self.run_button.setStyleSheet(
            "background-color: #0ea5e9; color: white; font-weight: bold; "
            "padding: 8px; border-radius: 3px;"
        )
        self.run_button.setMaximumHeight(28)
        self.run_button.clicked.connect(self.run_placement.emit)
        layout.addWidget(self.run_button)
        
        self.stop_button = QPushButton("■ STOP")
        self.stop_button.setStyleSheet(
            "background-color: #ef4444; color: white; font-weight: bold; "
            "padding: 6px; border-radius: 3px;"
        )
        self.stop_button.setMaximumHeight(24)
        layout.addWidget(self.stop_button)
        
        layout.addStretch()
    
    def get_placement_config(self) -> Dict:
        """Get current placement configuration."""
        return {
            'target_density': self.density_spin.value(),
            'utilization': int(self.density_spin.value() * 100),
            'optimizer': self.optimizer_combo.currentText().lower(),
            'iterations': self.iterations_spin.value(),
            'qml_enabled': self.qml_enable.isChecked(),
            'qml_n_qubits': self.qubits_spin.value(),
            'qml_n_layers': self.layers_spin.value(),
            'learning_rate': 0.01,
            'config_path': 'configs/ca234_sky130.json'
        }
