"""
QML·PLACE — OpenROAD Sky130 CA234 Placement UI
Main application entry point
"""

import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('placement_ui.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for QML·PLACE application."""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("QML·PLACE")
    app.setApplicationVersion("1.0.0")
    app.setStyle('Fusion')
    
    logger.info("[MAIN] Starting QML·PLACE application")
    
    # Import after QApplication creation (Qt dependency)
    from ui.main_window import MainWindow
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    logger.info("[MAIN] Main window displayed")
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
