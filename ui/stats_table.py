"""
Stats Table: Placement run history with detailed metrics
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QHeaderView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QBrush
from core.stats_store import StatsStore
from datetime import datetime

logger = logging.getLogger(__name__)


class StatsTableWidget(QWidget):
    """Statistics table showing placement run history."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("📊 CA234 Placement Run History — Sky130 HD")
        title.setFont(QFont("sans-serif", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(15)
        self.table.setHorizontalHeaderLabels([
            "#", "Timestamp", "Placer", "N Qubits", "N Layers",
            "Optimizer", "Density", "Iterations",
            "HPWL (µm×10⁶)", "HPWL Δ%", "WNS (ns)", "TNS (ns)",
            "Overflow %", "Time (s)", "Speedup", "DRC", "Status"
        ])
        
        self.table.setMinimumHeight(150)
        self.table.setMaximumHeight(300)
        
        # Configure columns
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Insert demo data
        self._insert_demo_data()
        
        # Store
        self.stats_store = StatsStore()
    
    def _insert_demo_data(self):
        """Insert demo CA234 runs."""
        demo_runs = [
            ("QML", 8, 4, "nesterov", 0.55, 2000, 38.42, 12.4, -0.12, -0.34, 0.21, 258, 1.31, 0, "DONE"),
            ("Standard", 0, 0, "replace", 0.55, 2000, 43.87, 0.0, -0.31, -1.12, 0.18, 231, 1.00, 0, "DONE"),
            ("QML", 12, 4, "adam", 0.60, 2000, 36.91, 15.9, -0.08, -0.18, 0.33, 344, 1.19, 0, "DONE"),
            ("QML", 8, 6, "nesterov", 0.55, 2000, 37.54, 14.4, -0.09, -0.25, 0.28, 302, 1.24, 2, "DONE"),
            ("QML", 16, 4, "sgd", 0.50, 2000, 35.83, 18.3, 0.04, 0.10, 0.41, 453, 1.09, 0, "DONE"),
        ]
        
        for row_idx, (placer, qubits, layers, opt, dens, iters, hpwl, delta, wns, tns, overflow, time, speedup, drc, status) in enumerate(demo_runs):
            self.table.insertRow(row_idx)
            
            timestamp = datetime.now().isoformat()
            
            items = [
                str(row_idx + 1),
                timestamp[:19],
                placer,
                str(qubits) if qubits > 0 else "—",
                str(layers) if layers > 0 else "—",
                opt,
                f"{dens:.2f}",
                str(iters),
                f"{hpwl:.2f}",
                f"{delta:+.1f}%" if delta != 0 else "—",
                f"{wns:.2f}",
                f"{tns:.2f}",
                f"{overflow:.2f}",
                f"{time}",
                f"{speedup:.2f}×",
                str(drc),
                status
            ]
            
            for col_idx, item_text in enumerate(items):
                item = QTableWidgetItem(item_text)
                
                # Color coding
                if col_idx == 9 and delta != 0:  # HPWL improvement
                    if delta > 0:
                        item.setForeground(QBrush(QColor(16, 185, 129)))  # Green
                    else:
                        item.setForeground(QBrush(QColor(239, 68, 68)))  # Red
                
                elif col_idx == 10 and wns != 0:  # WNS
                    if wns > 0:
                        item.setForeground(QBrush(QColor(16, 185, 129)))
                    else:
                        item.setForeground(QBrush(QColor(239, 68, 68)))
                
                elif col_idx == 15:  # DRC
                    if drc == 0:
                        item.setForeground(QBrush(QColor(16, 185, 129)))
                    elif drc <= 5:
                        item.setForeground(QBrush(QColor(245, 158, 11)))  # Amber
                    else:
                        item.setForeground(QBrush(QColor(239, 68, 68)))
                
                elif col_idx == 16:  # Status badge
                    if status == "DONE":
                        item.setBackground(QBrush(QColor(34, 197, 94, 80)))
                    elif status == "FAILED":
                        item.setBackground(QBrush(QColor(239, 68, 68, 80)))
                
                self.table.setItem(row_idx, col_idx, item)
    
    def add_run(self, placements, metrics: dict):
        """Add a new run to the table."""
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        
        placer = "QML"
        qubits = 8
        layers = 4
        
        timestamp = datetime.now().isoformat()
        hpwl = metrics.get('final_hpwl', 0)
        time_s = metrics.get('total_time', 0)
        
        items = [
            str(row_idx + 1),
            timestamp[:19],
            placer,
            str(qubits),
            str(layers),
            "nesterov",
            "0.55",
            "2000",
            f"{hpwl:.2f}",
            "0.0",
            "—",
            "—",
            "—",
            f"{time_s:.0f}",
            "1.00×",
            "0",
            "DONE"
        ]
        
        for col_idx, item_text in enumerate(items):
            self.table.setItem(row_idx, col_idx, QTableWidgetItem(item_text))
