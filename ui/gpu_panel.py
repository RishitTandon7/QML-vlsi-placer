"""
GPU Panel: GPU metrics display + VQC circuit visualizer
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGroupBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from core.gpu_monitor import GPUMonitor

logger = logging.getLogger(__name__)


class GPUPanel(QWidget):
    """GPU monitoring and VQC visualization panel."""
    
    def __init__(self, qml_model=None, pytorch_device="CPU"):
        super().__init__()
        self.setMaximumWidth(250)
        self.qml_model = qml_model
        self.pytorch_device = pytorch_device
        layout = QVBoxLayout(self)
        
        # GPU Monitor
        self.gpu_monitor = GPUMonitor()
        self.gpu_monitor.start_monitoring(interval=0.5)
        
        # GPU Info section
        gpu_box = QGroupBox("GPU RTX 4060")
        gpu_layout = QVBoxLayout(gpu_box)
        
        # Device name
        self.device_label = QLabel(self.gpu_monitor.current_metrics['device_name'])
        self.device_label.setFont(QFont("monospace", 9))
        gpu_layout.addWidget(self.device_label)
        
        # GPU Utilization
        gpu_layout.addWidget(QLabel("GPU Utilization:"))
        self.gpu_util_bar = QProgressBar()
        self.gpu_util_bar.setRange(0, 100)
        gpu_layout.addWidget(self.gpu_util_bar)
        self.gpu_util_label = QLabel("0%")
        gpu_layout.addWidget(self.gpu_util_label)
        
        # VRAM
        gpu_layout.addWidget(QLabel("VRAM Usage:"))
        self.vram_bar = QProgressBar()
        self.vram_bar.setRange(0, 100)
        gpu_layout.addWidget(self.vram_bar)
        self.vram_label = QLabel("0 / 0 MB")
        gpu_layout.addWidget(self.vram_label)
        
        # Temperature
        self.temp_label = QLabel("Temp: — °C")
        gpu_layout.addWidget(self.temp_label)
        
        # Power
        self.power_label = QLabel("Power: — W")
        gpu_layout.addWidget(self.power_label)
        
        layout.addWidget(gpu_box)
        
        # VQC Visualizer
        vqc_box = QGroupBox("VQC State")
        vqc_layout = QVBoxLayout(vqc_box)
        
        self.vqc_label = QLabel("8 Qubits | 4 Layers")
        self.vqc_label.setFont(QFont("monospace", 9))
        vqc_layout.addWidget(self.vqc_label)
        
        # Qubit state visualization
        self.qubit_states = []
        for i in range(8):
            label = QLabel(f"Q{i}: |0⟩")
            label.setFont(QFont("monospace", 8))
            vqc_layout.addWidget(label)
            self.qubit_states.append(label)
        
        layout.addWidget(vqc_box)
        
        # Status
        status_box = QGroupBox("Status")
        status_layout = QVBoxLayout(status_box)
        
        self.or_status = QLabel("● OpenROAD: Ready")
        self.or_status.setFont(QFont("monospace", 9))
        status_layout.addWidget(self.or_status)
        
        self.ep_status = QLabel("● Global Placement: Idle")
        self.ep_status.setFont(QFont("monospace", 9))
        status_layout.addWidget(self.ep_status)
        
        # Determine device from QML model
        qml_device_str = "CPU"
        if qml_model and hasattr(qml_model, 'device_name'):
            qml_device_str = qml_model.device_name
            if "gpu" in qml_device_str.lower():
                qml_device_str = "GPU (lightning.gpu)"
        
        # Show both quantum circuit device and PyTorch optimization device
        self.qml_status = QLabel(f"● Circuit: {qml_device_str}")
        self.qml_status.setFont(QFont("monospace", 9))
        status_layout.addWidget(self.qml_status)
        
        self.opt_status = QLabel(f"● Optimize: {pytorch_device}")
        self.opt_status.setFont(QFont("monospace", 9))
        status_layout.addWidget(self.opt_status)
        
        layout.addWidget(status_box)
        layout.addStretch()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_metrics)
        self.update_timer.start(500)
    
    def _update_metrics(self):
        """Update GPU metrics display."""
        metrics = self.gpu_monitor.get_metrics()
        
        self.gpu_util_bar.setValue(int(metrics['utilization']))
        self.gpu_util_label.setText(f"{metrics['utilization']:.1f}%")
        
        vram_percent = metrics['vram_percent']
        self.vram_bar.setValue(int(vram_percent))
        self.vram_label.setText(f"{metrics['vram_used_mb']} / {metrics['vram_total_mb']} MB ({vram_percent:.1f}%)")
        
        self.temp_label.setText(f"Temp: {metrics['temperature_c']:.1f} °C")
        self.power_label.setText(f"Power: {metrics['power_w']:.1f} W")
    
    def closeEvent(self, event):
        """Cleanup on close."""
        self.gpu_monitor.stop_monitoring()
        super().closeEvent(event)
