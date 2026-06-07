"""
theme.py — цвета и стили приложения

Здесь два словаря: LIGHT и DARK.
Каждый ключ — это одна "роль" цвета, например:
  "bg"     — основной фон
  "bg2"    — чуть темнее, для панелей и полей
  "bg3"    — ещё темнее, для hover-эффектов
  "border" — цвет рамок и разделителей
  "text"   — основной текст
  "text2"  — вторичный текст (подписи, подсказки)
  "text3"  — третичный текст (совсем бледный)
  "accent" — цвет кнопок
  ...и так далее

Чтобы поменять цвет — просто меняй hex-код рядом с нужным ключом.
Например, чтобы сделать фон светлой темы белее:
  "bg": "#FFFFFF"
"""

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

LIGHT = {
    "bg":            "#F5EFE0",  # ← основной фон светлой темы
    "bg2":           "#EFE4CC",  # ← фон панелей, полей ввода
    "bg3":           "#E5D9B6",  # ← hover-эффекты
    "border":        "#C4A882",  # ← рамки и разделители
    "text":          "#1C1108",  # ← основной текст
    "text2":         "#3D2810",  # ← вторичный текст
    "text3":         "#7A5C30",  # ← подсказки, метки
    "accent":        "#7A4A20",  # ← цвет кнопок
    "accent_text":   "#FBF7F0",  # ← текст на кнопках
    "accent_hover":  "#5A3210",  # ← кнопка при наведении
    "accent_off":    "#C4A882",  # ← неактивная кнопка
    "accent_off_fg": "#F5ECD8",  # ← текст неактивной кнопки
    "topbar_bg":     "#EFE4CC",  # ← фон верхней панели
    "wait_bg":  "#EDE2CF", "wait_fg":  "#5A3E20",  # ← статус "Ожидает"
    "proc_bg":  "#F5DDB0", "proc_fg":  "#7A4A20",  # ← статус "В обработке"
    "done_bg":  "#D0E8B8", "done_fg":  "#2E6010",  # ← статус "Готово"
    "err_bg":   "#FCEBEB", "err_fg":   "#A32D2D",  # ← статус "Ошибка"
    "bar_track": "#D8C8A8",  # ← фон прогресс-бара (незаполненная часть)
    "bar_done":  "#4E9018",  # ← цвет заполненного прогресс-бара
    "bar_proc":  "#C08030",  # ← цвет прогресс-бара во время работы
}

DARK = {
    "bg":            "#221810",
    "bg2":           "#18100A",
    "bg3":           "#2E2010",
    "border":        "#5C4530",
    "text":          "#F0E6D0",
    "text2":         "#C8AA80",
    "text3":         "#A08050",
    "accent":        "#C49060",
    "accent_text":   "#18100A",
    "accent_hover":  "#E0B080",
    "accent_off":    "#4A3018",
    "accent_off_fg": "#7A5C30",
    "topbar_bg":     "#18100A",
    "wait_bg":  "#3A2810", "wait_fg":  "#C8AA80",
    "proc_bg":  "#4A3010", "proc_fg":  "#C49060",
    "done_bg":  "#1A3010", "done_fg":  "#70B030",
    "err_bg":   "#3A1010", "err_fg":   "#E06060",
    "bar_track": "#3A2810",
    "bar_done":  "#4E9018",
    "bar_proc":  "#C08030",
}


def is_dark_mode() -> bool:
    """
    Определяет тёмная или светлая тема включена в системе.

    На Windows читает реестр — это самый надёжный способ.
    На Mac и Linux использует запасной вариант через яркость фона
    (менее точно, но работает на всех системах).
    """
    import sys
    if sys.platform == "win32":
        # Windows: читаем реестр напрямую
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0  # 0 = тёмная тема, 1 = светлая
        except Exception:
            # если реестр недоступен — используем запасной вариант
            pass

    # Mac / Linux / запасной вариант для Windows:
    # смотрим на яркость стандартного фона окна
    bg = QApplication.palette().color(QPalette.ColorRole.Window)
    return bg.lightness() < 128


def make_stylesheet(t: dict) -> str:
    """
    Собирает строку стилей Qt из словаря темы.
    Применяется к главному окну через setStyleSheet().
    """
    return f"""
    QMainWindow, QWidget {{
        background: {t['bg']};
        color: {t['text']};
        font-size: 13px;
    }}
    QLabel {{ background: transparent; color: {t['text']}; }}

    QPushButton {{
        background: {t['accent']};
        color: {t['accent_text']};
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 13px;
        text-align: center;
    }}
    QPushButton:hover   {{ background: {t['accent_hover']}; }}
    QPushButton:pressed {{ background: {t['accent_hover']}; }}
    QPushButton:disabled {{
        background: {t['accent_off']};
        color: {t['accent_off_fg']};
    }}

    QPushButton#btn_menu {{
        background: transparent;
        color: {t['text3']};
        border: none;
        font-size: 18px;
        padding: 2px 4px;
        border-radius: 6px;
    }}
    QPushButton#btn_menu:hover {{ background: {t['bg3']}; }}

    QPushButton#btn_back {{
        background: transparent;
        color: {t['text2']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 5px 14px;
        font-size: 12px;
    }}
    QPushButton#btn_back:hover {{ background: {t['bg2']}; }}

    QWidget#topbar {{
        background: {t['topbar_bg']};
        border-bottom: 1px solid {t['border']};
    }}

    QScrollArea, QScrollArea > QWidget > QWidget {{
        background: transparent; border: none;
    }}
    QScrollBar:vertical {{
        width: 5px; background: transparent; border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {t['border']}; border-radius: 2px; min-height: 20px;
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{ height: 0; }}

    QStatusBar {{
        color: {t['text3']}; font-size: 12px;
        background: {t['topbar_bg']};
        border-top: 1px solid {t['border']};
        padding: 2px 8px;
    }}
    QToolTip {{
        background: {t['text']}; color: {t['bg']};
        border: none; border-radius: 6px;
        padding: 6px 10px; font-size: 12px;
        max-width: 200px;
    }}
    """