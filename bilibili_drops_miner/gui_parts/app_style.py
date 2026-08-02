from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication


APP_STYLE_SHEET = """
        QWidget { background: #09090b; color: #fafafa; }
        QWidget#appRoot, QMainWindow { background: #09090b; }
        QLabel { background: transparent; color: #fafafa; }
        QLabel#appTitle { font-size: 22px; font-weight: 700; }
        QLabel#sectionTitle { font-size: 15px; font-weight: 600; }
        QLabel#fieldLabel { color: #a1a1aa; font-size: 13px; }
        QToolTip { background: #fafafa; color: #09090b; border: 1px solid #d4d4d8;
                   padding: 5px 8px; border-radius: 4px; }

        QLineEdit {
            background: #18181b; color: #fafafa;
            border: 1px solid #3f3f46; border-radius: 6px;
            padding: 6px 10px; min-height: 18px;
            selection-background-color: #fafafa;
            selection-color: #09090b;
            placeholder-text-color: #71717a;
        }
        QLineEdit:hover { border-color: #52525b; }
        QLineEdit:focus { border: 1px solid #fafafa; }
        QLineEdit:disabled { color: #52525b; background: #111113; }

        QPlainTextEdit {
            background: #09090b; color: #e4e4e7;
            border: 1px solid #27272a; border-radius: 6px;
            padding: 10px; selection-background-color: #fafafa;
            selection-color: #09090b;
        }
        QPlainTextEdit:focus { border-color: #52525b; }

        QCheckBox { background: transparent; spacing: 8px; color: #e4e4e7; }
        QCheckBox::indicator {
            width: 16px; height: 16px; border: 1px solid #52525b;
            border-radius: 4px; background: #09090b;
        }
        QCheckBox::indicator:hover { border-color: #a1a1aa; }
        QCheckBox::indicator:checked {
            background: #fafafa; border-color: #fafafa;
            image: none;
        }
        QCheckBox:focus { color: #ffffff; }

        QProgressBar {
            background: #27272a; border: 0; border-radius: 2px;
            min-height: 4px; max-height: 4px;
        }
        QProgressBar::chunk {
            background: #fafafa;
            border-radius: 2px;
        }

        QScrollBar:vertical {
            background: transparent; width: 10px; margin: 2px 1px;
        }
        QScrollBar::handle:vertical {
            background: #3f3f46; border-radius: 4px; min-height: 28px;
        }
        QScrollBar::handle:vertical:hover { background: #71717a; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: transparent; height: 0; border: 0;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: transparent;
        }
        QScrollBar:horizontal {
            background: transparent; height: 10px; margin: 2px;
        }
        QScrollBar::handle:horizontal {
            background: #3f3f46; border-radius: 4px; min-width: 28px;
        }
        QScrollBar::handle:horizontal:hover { background: #71717a; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            background: transparent; width: 0; border: 0;
        }

        QMenu {
            background: #111113; color: #fafafa;
            border: 1px solid #27272a; border-radius: 6px; padding: 4px;
        }
        QMenu::item { padding: 6px 18px; border-radius: 4px; }
        QMenu::item:selected { background: #fafafa; color: #09090b; }
        """


def configure_qt_app(app: QApplication) -> None:
    app.setApplicationName("Bilibili 直播掉宝助手")
    app.setOrganizationName("BiliBiliDropsMiner")
    app.setStyle("Fusion")
    if sys.platform == "darwin":
        default_font = QFont(".AppleSystemUIFont", 10)
    elif sys.platform == "win32":
        default_font = QFont("Segoe UI", 10)
    else:
        default_font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
        default_font.setPointSize(10)
    default_font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(default_font)
    app.setStyleSheet(APP_STYLE_SHEET)
