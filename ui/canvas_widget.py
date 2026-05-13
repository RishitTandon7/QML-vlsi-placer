"""
Canvas Widget: Placement visualization with Sky130 row grid
"""

import logging
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPointF
from pyqtgraph import PlotWidget, ScatterPlotItem, mkPen, mkBrush

logger = logging.getLogger(__name__)


class PlacementCanvasWidget(PlotWidget):
    """Interactive placement visualization canvas."""
    
    def __init__(self):
        super().__init__()
        self.setLabel('left', 'Y (µm)')
        self.setLabel('bottom', 'X (µm)')
        self.setTitle("CA234  |  Sky130 HD  |  Density: 55%")
        
        self.scatter = ScatterPlotItem(size=5, pen=mkPen(color=(0, 200, 255), width=1),
                                      brush=mkBrush(color=(0, 200, 255)))
        self.addItem(self.scatter)
        
        self.die_area = (0, 0, 1000, 1000)  # µm
        self.placements = None
        
        # Draw die boundary
        self._draw_die_boundary()
        
        # Draw Sky130 row grid
        self._draw_row_grid()
        
        self.setMinimumHeight(400)
    
    def _draw_die_boundary(self):
        """Draw die area boundary."""
        x0, y0, x1, y1 = self.die_area
        
        # Draw rectangle outline
        from pyqtgraph import LineROI
        self.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], 
                 pen=mkPen(color=(255, 255, 255), width=2))
    
    def _draw_row_grid(self):
        """Draw Sky130 row grid (2.72 µm row height)."""
        x0, y0, x1, y1 = self.die_area
        row_height = 2.72  # µm for Sky130
        
        y = y0
        while y < y1:
            self.plot([x0, x1], [y, y], pen=mkPen(color=(100, 100, 100), width=0.5, style=Qt.PenStyle.DashLine))
            y += row_height
    
    def set_placements(self, placements: np.ndarray):
        """
        Update placement visualization.
        
        Args:
            placements: [N, 2] array with (x, y) in DBU
        """
        # Convert DBU to µm
        placements_um = placements / 1000.0
        
        # Update scatter plot
        if len(placements_um) > 0:
            self.scatter.setData(x=placements_um[:, 0], y=placements_um[:, 1])
        
        self.placements = placements_um
        logger.info(f"[CANVAS] Updated with {len(placements_um)} cells")
    
    def set_die_area(self, x0: int, y0: int, x1: int, y1: int):
        """Set die area (in DBU)."""
        self.die_area = (x0/1000, y0/1000, x1/1000, y1/1000)
        self.setXRange(self.die_area[0], self.die_area[2])
        self.setYRange(self.die_area[1], self.die_area[3])
