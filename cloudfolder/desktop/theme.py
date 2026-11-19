"""Класична світла тема: сірі панелі, прямі кути, однаковий вигляд незалежно від системної теми."""
from PySide6.QtGui import QColor, QPalette

STYLE = """
QPushButton, QToolButton, QComboBox {
    border: 1px solid #adadad; border-radius: 0; background: #f3f3f3; padding: 3px 10px;
}
QPushButton:hover, QToolButton:hover, QComboBox:hover { background: #e5f1fb; border-color: #0078d7; }
QPushButton:pressed, QToolButton:pressed { background: #cce4f7; }
QPushButton:disabled, QToolButton:disabled { color: #8a8a8a; background: #f0f0f0; border-color: #cccccc; }
QToolButton::menu-indicator { subcontrol-position: right center; right: 3px; }
QToolButton[popupMode="2"] { padding-right: 18px; }
QLineEdit { border: 1px solid #adadad; border-radius: 0; padding: 3px; background: #ffffff; }
QToolBar { border-bottom: 1px solid #c8c8c8; spacing: 4px; padding: 3px; }
QGroupBox { border: 1px solid #c8c8c8; border-radius: 0; margin-top: 10px; padding-top: 6px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px; }
QHeaderView::section { background: #e8e8e8; border: none; border-right: 1px solid #c8c8c8;
                       border-bottom: 1px solid #c8c8c8; padding: 4px 6px; font-weight: 600; }
QTableView { gridline-color: #dcdcdc; border: 1px solid #c8c8c8; }
QStatusBar { border-top: 1px solid #c8c8c8; }
QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #7a7a7a; background: #ffffff; }
QCheckBox::indicator:checked { background: #0078d7; border-color: #0078d7; }
QCheckBox::indicator:disabled { border-color: #c0c0c0; background: #f0f0f0; }
"""


def apply_theme(app) -> None:
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#f0f0f0"))
    p.setColor(QPalette.WindowText, QColor("#1a1a1a"))
    p.setColor(QPalette.Base, QColor("#ffffff"))
    p.setColor(QPalette.AlternateBase, QColor("#f7f7f7"))
    p.setColor(QPalette.Text, QColor("#1a1a1a"))
    p.setColor(QPalette.Button, QColor("#f3f3f3"))
    p.setColor(QPalette.ButtonText, QColor("#1a1a1a"))
    p.setColor(QPalette.Highlight, QColor("#0078d7"))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    p.setColor(QPalette.ToolTipText, QColor("#1a1a1a"))
    p.setColor(QPalette.PlaceholderText, QColor("#8a8a8a"))
    app.setPalette(p)
    app.setStyleSheet(STYLE)
