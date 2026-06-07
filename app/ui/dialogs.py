"""
dialogs.py — всплывающие диалоговые окна

Здесь два класса:

ConfirmDialog — диалог подтверждения остановки книги.
    Показывается когда пользователь нажимает "Стоп" на карточке книги.
    Блокирует основное окно пока не получит ответ.
    Использование:
        dlg = ConfirmDialog(book_name, theme, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # пользователь нажал "Да, остановить"

SettingsDialog — диалог настроек (выбор темы).
    Не закрывается после каждого выбора — можно переключать несколько раз.
    Сообщает о смене темы через сигнал theme_changed.
    Использование:
        dlg = SettingsDialog(theme, current_theme, parent)
        dlg.theme_changed.connect(main_window._switch_theme)
        dlg.exec()
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton,
)


class ConfirmDialog(QDialog):
    def __init__(self, book_name: str, theme: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Остановить обработку книги?")
        self.setModal(True)
        t = theme
        self.setStyleSheet(f"""
            QDialog {{
                background: {t['bg']};
                color: {t['text']};
            }}
            QLabel {{ color: {t['text']}; background: transparent; }}
            QPushButton {{
                background: {t['accent']};
                color: {t['accent_text']};
                border: none; border-radius: 8px;
                padding: 8px 20px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {t['accent_hover']}; }}
            QPushButton#btn_no {{
                background: transparent;
                color: {t['text2']};
                border: 1px solid {t['border']};
            }}
            QPushButton#btn_no:hover {{ background: {t['bg2']}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 20, 24, 20)

        lbl = QLabel(f"Остановить обработку «{book_name}»?")
        lbl.setStyleSheet(f"font-size: 14px; color: {t['text']};")
        lbl.setWordWrap(False)
        layout.addWidget(lbl)

        lbl2 = QLabel("Уже выполненные этапы будут потеряны.")
        lbl2.setStyleSheet(f"font-size: 12px; color: {t['text3']};")
        layout.addWidget(lbl2)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_yes = QPushButton("Да, остановить")
        btn_no  = QPushButton("Отмена")
        btn_no.setObjectName("btn_no")
        btn_yes.setFixedHeight(36)
        btn_no.setFixedHeight(36)
        btn_yes.setMinimumWidth(140)
        btn_no.setMinimumWidth(140)
        btn_yes.clicked.connect(self.accept)
        btn_no.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_no)
        btn_row.addWidget(btn_yes)
        layout.addLayout(btn_row)


class SettingsDialog(QDialog):
    # сигнал — сообщает главному окну что выбрана новая тема
    # передаёт строку "light" или "dark"
    theme_changed = pyqtSignal(str)

    def __init__(self, theme: dict, current: str, parent=None):
        """
        theme   — словарь текущей темы (LIGHT или DARK)
        current — строка "light" или "dark", чтобы подсветить активную кнопку
        """
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.setFixedWidth(300)
        t = theme
        self.setStyleSheet(f"""
            QDialog {{ background: {t['bg']}; color: {t['text']}; }}
            QLabel {{ background: transparent; color: {t['text']}; }}
            QPushButton {{
                background: {t['accent']}; color: {t['accent_text']};
                border: none; border-radius: 8px;
                padding: 8px 20px; font-size: 13px;
                min-width: 100px;
            }}
            QPushButton:hover {{ background: {t['accent_hover']}; }}
            QPushButton#btn_theme {{
                background: {t['bg2']};
                color: {t['text']};
                border: 1px solid {t['border']};
            }}
            QPushButton#btn_theme:hover {{ background: {t['bg3']}; }}
            QPushButton#btn_theme_active {{
                background: {t['accent']};
                color: {t['accent_text']};
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        lbl = QLabel("Тема оформления")
        lbl.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {t['text']};")
        layout.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(8)
        btn_light = QPushButton("☀️  Светлая")
        btn_dark  = QPushButton("🌙  Тёмная")
        # активная тема выделяется — у неё другой objectName и стиль
        btn_light.setObjectName("btn_theme_active" if current == "light" else "btn_theme")
        btn_dark.setObjectName("btn_theme_active" if current == "dark" else "btn_theme")
        btn_light.setFixedHeight(36)
        btn_dark.setFixedHeight(36)
        btn_light.clicked.connect(lambda: self._pick("light"))
        btn_dark.clicked.connect(lambda: self._pick("dark"))
        row.addWidget(btn_light)
        row.addWidget(btn_dark)
        layout.addLayout(row)

    def _pick(self, theme: str):
        # отправляем сигнал — главное окно его услышит и перекрасится
        # окно не закрываем — пользователь может переключать несколько раз
        self.theme_changed.emit(theme)