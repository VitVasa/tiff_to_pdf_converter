"""
settings.py — пути и сохранение настроек

Здесь три вещи:

1. Константы путей:
   BASE_DIR      — папка где лежит приложение
   UI_PATH       — путь к файлу разметки (.ui)
   SETTINGS_FILE — путь к файлу настроек (settings.json)
   DEFAULT_OUTPUT — папка для сохранения PDF по умолчанию

2. load_settings() — читает settings.json и возвращает словарь.
   Если файл не существует или сломан — возвращает пустой словарь.

3. save_settings() — записывает словарь в settings.json.
   Если что-то пошло не так — молча игнорирует ошибку.

Что хранится в settings.json:
  {
    "output_dir": "C:/Users/.../Documents",   ← последняя выбранная папка
    "recent_files": ["path1.pdf", "path2.pdf"] ← последние обработанные файлы
    "theme": "light"                           ← выбранная тема
  }
"""

import json
from pathlib import Path

BASE_DIR       = Path(__file__).parent
UI_PATH        = str(BASE_DIR / "app_full_v3.ui")
SETTINGS_FILE  = str(BASE_DIR / "settings.json")
DEFAULT_OUTPUT = str(Path.home() / "Documents")


def load_settings() -> dict:
    """Загружает настройки из файла. При ошибке возвращает {}."""
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data: dict):
    """Сохраняет настройки в файл. При ошибке молча продолжает."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass