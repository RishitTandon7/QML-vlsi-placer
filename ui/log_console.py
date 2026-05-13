"""
Log Console: Real-time logging with syntax highlighting
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QFont, QTextCursor, QColor, QTextCharFormat

logger = logging.getLogger(__name__)


class LogConsole(QWidget):
    """Real-time log display with color-coded messages."""
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # Text edit
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier New", 9))
        self.text_edit.setMaximumHeight(120)
        layout.addWidget(self.text_edit)
        
        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear)
        layout.addWidget(clear_btn)
        
        # Format definitions
        self.formats = {
            'OPENROAD': self._make_format((249, 115, 22)),  # Orange
            'SKY130': self._make_format((56, 189, 248)),    # Light Blue
            'TCL': self._make_format((250, 204, 21)),       # Yellow
            'DRC': self._make_format((239, 68, 68)),        # Red
            'QML': self._make_format((168, 85, 247)),       # Purple
            'ERROR': self._make_format((239, 68, 68), bold=True),  # Red Bold
            'INFO': self._make_format((34, 197, 94)),       # Green
            'WARN': self._make_format((245, 158, 11)),      # Amber
        }
    
    def _make_format(self, rgb: tuple, bold: bool = False) -> QTextCharFormat:
        """Create text format with color."""
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(*rgb))
        if bold:
            fmt.setFontWeight(700)
        return fmt
    
    def log(self, message: str):
        """Log a message with syntax highlighting."""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
        
        # Determine format based on message prefix
        fmt = self.formats.get('INFO')
        
        for prefix, prefix_fmt in [('[OPENROAD]', 'OPENROAD'),
                                   ('[SKY130]', 'SKY130'),
                                   ('[TCL]', 'TCL'),
                                   ('[DRC]', 'DRC'),
                                   ('[QML]', 'QML'),
                                   ('[ERROR]', 'ERROR'),
                                   ('[WARN]', 'WARN')]:
            if message.startswith(prefix):
                fmt = self.formats[prefix_fmt]
                break
        
        self.text_edit.setCurrentCharFormat(fmt)
        self.text_edit.append(message)
        
        # Auto-scroll to bottom
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
    
    def clear(self):
        """Clear log."""
        self.text_edit.clear()
        self.log("[INFO] Log cleared")
