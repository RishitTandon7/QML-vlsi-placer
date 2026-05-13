"""
Progress Widget: Real-time progress bar with ETA
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)


class ProgressPanel(QWidget):
    """Real-time progress visualization with ETA."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        
        # Top row: Stage info
        top_row = QHBoxLayout()
        self.stage_label = QLabel("Ready")
        self.stage_label.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        self.stage_label.setStyleSheet("color: #0ea5e9;")
        top_row.addWidget(self.stage_label)
        top_row.addStretch()
        layout.addLayout(top_row)
        
        # Progress bar
        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setValue(0)
        self.overall_bar.setMaximumHeight(22)
        self.overall_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3d3d5c;
                border-radius: 3px;
                background-color: #2d2d44;
                text-align: center;
                color: white;
                font-weight: bold;
                font-size: 9px;
            }
            QProgressBar::chunk {
                background-color: #0ea5e9;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.overall_bar)
        
        # Metrics row
        metrics_layout = QHBoxLayout()
        
        self.iter_label = QLabel("Iter: 0/2000")
        self.iter_label.setFont(QFont("Courier New", 8))
        metrics_layout.addWidget(self.iter_label)
        
        metrics_layout.addSpacing(20)
        
        self.hpwl_label = QLabel("HPWL: — µm")
        self.hpwl_label.setFont(QFont("Courier New", 8))
        metrics_layout.addWidget(self.hpwl_label)
        
        metrics_layout.addSpacing(20)
        
        self.eta_label = QLabel("ETA: —")
        self.eta_label.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self.eta_label.setStyleSheet("color: #f97316;")
        metrics_layout.addWidget(self.eta_label)
        
        metrics_layout.addStretch()
        layout.addLayout(metrics_layout)
        
        self.setMaximumHeight(80)
    
    def set_stage(self, stage_name: str, percentage: int):
        """Update progress bar."""
        self.overall_bar.setValue(percentage)
        self.stage_label.setText(stage_name)
    
    def update_iteration(self, current: int, total: int, hpwl: float, overflow: float, eta_seconds: int):
        """Update iteration progress and metrics."""
        # Update progress bar
        progress = int(35 + 45 * current / total)
        self.overall_bar.setValue(progress)
        
        # Format iteration counter
        self.iter_label.setText(f"Iter: {current:,}/{total:,}")
        
        # Format HPWL (convert from DBU to µm: divide by 1000)
        hpwl_um = hpwl / 1000.0
        self.hpwl_label.setText(f"HPWL: {hpwl_um:,.0f} µm")
        
        # Format ETA
        if eta_seconds <= 0:
            eta_text = "ETA: Computing..."
        elif eta_seconds < 60:
            eta_text = f"ETA: {eta_seconds}s"
        elif eta_seconds < 3600:
            minutes = eta_seconds // 60
            seconds = eta_seconds % 60
            eta_text = f"ETA: {minutes}m {seconds}s"
        else:
            hours = eta_seconds // 3600
            minutes = (eta_seconds % 3600) // 60
            eta_text = f"ETA: {hours}h {minutes}m"
        
        self.eta_label.setText(eta_text)
        self.eta_label.setStyleSheet("color: #f97316;" if eta_seconds > 60 else "color: #10b981;")
    
    def reset(self):
        """Reset progress."""
        self.overall_bar.setValue(0)
        self.stage_label.setText("Ready")
        self.iter_label.setText("Iter: 0/0")
        self.hpwl_label.setText("HPWL: — µm")
        self.eta_label.setText("ETA: —")

