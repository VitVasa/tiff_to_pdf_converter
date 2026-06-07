"""
drawer.py — боковая шторка (меню)

Класс Drawer — панель которая выезжает поверх главного окна
при нажатии на кнопку ☰.

Важный момент: шторка создаётся как отдельное окно без рамки
(FramelessWindowHint + Tool), а не как дочерний виджет главного окна.
Это сделано специально — иначе глобальный stylesheet главного окна
перекрашивал бы шторку и делал её прозрачной.

Шторка общается с главным окном через callbacks (не сигналы):
  set_close_callback(fn)    — что вызвать когда пользователь закрывает шторку
  set_settings_callback(fn) — что вызвать когда нажимают "Настройки"

Позиционирование — снаружи, в MainWindow:
  drawer.setGeometry(pos.x(), pos.y(), 220, window.height())
"""

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)


class Drawer(QWidget):
    def __init__(self, theme: dict, recent_files: list, parent=None):
        super().__init__(parent)
        t = theme

        # отдельное окно без рамки — не наследует стили главного окна
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setStyleSheet(f"background: {t['bg2']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(0)

        # верхняя полоса — той же высоты что topbar главного окна (44px)
        # чтобы кнопка ☰ была на одном уровне с той что открывает шторку
        topbar = QWidget()
        topbar.setFixedHeight(44)
        topbar.setStyleSheet(
            f"background: {t['topbar_bg']}; border-bottom: 1px solid {t['border']};"
        )
        tl = QHBoxLayout(topbar)
        tl.setContentsMargins(8, 4, 8, 4)

        btn_toggle = QPushButton("☰")
        btn_toggle.setFixedSize(36, 36)
        btn_toggle.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {t['text3']};"
            f"font-size: 18px; padding: 2px 4px; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {t['bg3']}; }}"
        )
        btn_toggle.clicked.connect(self._on_close)
        tl.addWidget(btn_toggle)
        tl.addStretch()
        layout.addWidget(topbar)

        # кнопка настроек
        btn_settings = QPushButton("⚙️  Настройки")
        btn_settings.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {t['text2']};"
            f"padding: 8px 14px; text-align: left; font-size: 13px; }}"
            f"QPushButton:hover {{ background: {t['bg3']}; border-radius: 6px; }}"
        )
        btn_settings.clicked.connect(self._open_settings)
        layout.addWidget(btn_settings)

        # разделитель
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {t['border']}; margin: 0 14px;")
        layout.addWidget(sep)

        # заголовок секции
        lbl_files = QLabel("ПОСЛЕДНИЕ ФАЙЛЫ")
        lbl_files.setStyleSheet(
            f"font-size: 10px; color: {t['text3']}; padding: 6px 14px 2px;"
        )
        layout.addWidget(lbl_files)

        # список последних файлов — показываем последние 5 в обратном порядке
        # (самый свежий сверху)
        if recent_files:
            for p in list(reversed(recent_files))[:5]:
                name = Path(p).name
                b = QPushButton(f"  {name}")
                b.setStyleSheet(
                    f"QPushButton {{ background: transparent; border: none; color: {t['text2']};"
                    f"padding: 6px 14px; text-align: left; font-size: 12px; }}"
                    f"QPushButton:hover {{ background: {t['bg3']}; }}"
                )
                b.setToolTip(p)  # полный путь при наведении
                b.clicked.connect(lambda checked, path=p: self._open_file(path))
                layout.addWidget(b)
        else:
            lbl_e = QLabel("  Нет файлов")
            lbl_e.setStyleSheet(
                f"font-size: 12px; color: {t['text3']}; padding: 4px 14px;"
            )
            layout.addWidget(lbl_e)

        layout.addStretch()

    # ── callbacks ─────────────────────────────────────────────────────────
    # Шторка не знает о главном окне напрямую.
    # Вместо этого главное окно передаёт функции которые надо вызвать.

    def set_close_callback(self, cb):
        """Запоминаем функцию закрытия от главного окна."""
        self._on_close_cb = cb

    def _on_close(self):
        """Скрываем шторку и сообщаем главному окну."""
        self.hide()
        self._on_close_cb()

    def set_settings_callback(self, cb):
        """Запоминаем функцию открытия настроек от главного окна."""
        self._settings_cb = cb

    def _open_settings(self):
        """Вызываем функцию настроек если она была передана."""
        if hasattr(self, '_settings_cb'):
            self._settings_cb()

    # ── открытие файла ────────────────────────────────────────────────────

    def _open_file(self, path: str):
        """Открывает папку с файлом в проводнике."""
        folder = str(Path(path).parent)
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            import subprocess; subprocess.Popen(["open", folder])
        else:
            import subprocess; subprocess.Popen(["xdg-open", folder])