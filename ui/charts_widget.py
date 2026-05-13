"""
Charts Panel: 2×2 real-time placement metrics visualization
"""

import logging
from PyQt6.QtWidgets import QWidget, QGridLayout
from pyqtgraph import PlotWidget, mkPen

logger = logging.getLogger(__name__)


class ChartsPanel(QWidget):
    """Real-time charts for placement metrics."""
    
    def __init__(self):
        super().__init__()
        layout = QGridLayout(self)
        
        # HPWL chart
        self.hpwl_chart = PlotWidget()
        self.hpwl_chart.setLabel('left', 'HPWL (µm ×10⁶)')
        self.hpwl_chart.setLabel('bottom', 'Iteration')
        self.hpwl_chart.setTitle('Wire Length')
        layout.addWidget(self.hpwl_chart, 0, 0)
        
        # Density overflow chart
        self.density_chart = PlotWidget()
        self.density_chart.setLabel('left', 'Overflow (%)')
        self.density_chart.setLabel('bottom', 'Iteration')
        self.density_chart.setTitle('Density Overflow')
        layout.addWidget(self.density_chart, 0, 1)
        
        # QML loss chart
        self.loss_chart = PlotWidget()
        self.loss_chart.setLabel('left', 'Loss (log scale)')
        self.loss_chart.setLabel('bottom', 'Iteration')
        self.loss_chart.setTitle('QML Loss')
        self.loss_chart.setLogMode(y=True)
        layout.addWidget(self.loss_chart, 1, 0)
        
        # GPU utilization chart
        self.gpu_chart = PlotWidget()
        self.gpu_chart.setLabel('left', 'GPU Util (%)')
        self.gpu_chart.setLabel('bottom', 'Iteration')
        self.gpu_chart.setTitle('GPU Utilization RTX 4060')
        layout.addWidget(self.gpu_chart, 1, 1)
        
        self.setMinimumHeight(300)
        self.setMaximumHeight(400)
    
    def update_metrics(self, iterations: list, hpwl: list, overflow: list, loss: list, gpu: list):
        """Update all charts with new data."""
        self.hpwl_chart.plot(iterations, hpwl, pen=mkPen(color=(0, 255, 0), width=2))
        self.density_chart.plot(iterations, overflow, pen=mkPen(color=(255, 0, 0), width=2))
        self.loss_chart.plot(iterations, loss, pen=mkPen(color=(128, 0, 255), width=2))
        self.gpu_chart.plot(iterations, gpu, pen=mkPen(color=(0, 200, 255), width=2),
                           fillLevel=0, brush=(0, 200, 255, 80))
    
    def clear(self):
        """Clear all charts."""
        for chart in [self.hpwl_chart, self.density_chart, self.loss_chart, self.gpu_chart]:
            chart.clear()
