"""
main.py — главное окно и точка входа

Запуск: python main.py

MainWindow — центр всего приложения. Загружает .ui файл,
подключает все виджеты и управляет логикой:

  - Переключение между экраном 1 (выбор папок) и экраном 2 (прогресс)
  - Создание карточек BookCard для каждой книги
  - Запуск и остановка Worker
  - Открытие/закрытие шторки Drawer
  - Смена темы
  - Сохранение настроек

Этот файл — "дирижёр". Он ничего не делает сам,
только связывает все остальные части между собой.
"""

import os
import sys
from pathlib import Path

# добавляем папку ui в путь поиска модулей —
# там лежат theme.py, settings.py, dialogs.py, drawer.py, book_card.py, worker.py
sys.path.insert(0, str(Path(__file__).parent / "ui"))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QMainWindow,
    QVBoxLayout, QWidget,
)
from PyQt6.uic import loadUi

from theme import LIGHT, DARK, make_stylesheet, is_dark_mode
from settings import UI_PATH, DEFAULT_OUTPUT, load_settings, save_settings
from dialogs import SettingsDialog
from drawer import Drawer
from book_card import BookCard
from worker import Worker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi(UI_PATH, self)  # загружаем разметку из .ui файла

        # ── загружаем сохранённые настройки ──────────────────────────────
        settings = load_settings()
        self._output_dir   = settings.get("output_dir", DEFAULT_OUTPUT)
        self._recent_files = settings.get("recent_files", [])

        # тема: сначала из настроек, если нет — определяем по системе
        saved_theme = settings.get("theme", None)
        if saved_theme == "dark":
            self._t = DARK
        elif saved_theme == "light":
            self._t = LIGHT
        else:
            self._t = DARK if is_dark_mode() else LIGHT

        # ── внутреннее состояние ─────────────────────────────────────────
        self._folders: list[str]        = []   # добавленные папки
        self._cards:   dict[str, BookCard] = {} # карточки книг folder→card
        self._drawer = None                     # шторка (None если закрыта)

        # ── инициализация ─────────────────────────────────────────────────
        self._apply_styles()
        self._connect()
        self._update_screen1()

        # scroll layout для карточек на втором экране
        sw = QWidget()
        sw.setStyleSheet("background: transparent;")
        self._scroll_layout = QVBoxLayout(sw)
        self._scroll_layout.setContentsMargins(0, 0, 4, 0)
        self._scroll_layout.setSpacing(6)
        self._scroll_layout.addStretch()
        self.scrollArea.setWidget(sw)

        self.stack.setCurrentIndex(0)  # показываем первый экран

    # ── стили ─────────────────────────────────────────────────────────────

    def _apply_styles(self):
        """Применяет текущую тему ко всему окну."""
        t = self._t
        self.setStyleSheet(make_stylesheet(t))

        self.lbl_topbar_title.setStyleSheet(
            f"font-size: 16px; font-weight: 500; color: {t['text']};"
        )
        self.lbl_welcome_sub.setStyleSheet(
            f"font-size: 13px; color: {t['text2']}; padding: 0 4px;"
        )
        self.lbl_start_hint.setStyleSheet(
            f"font-size: 12px; color: {t['text3']};"
            f"background: {t['bg2']}; border-radius: 8px; padding: 8px 10px;"
        )
        self.lbl_folder_count.setStyleSheet(
            f"font-size: 12px; color: {t['text2']}; padding: 0 4px;"
        )
        self.lbl_processing.setVisible(False)

        # стиль кружочков с вопросом
        q_style = (
            f"QLabel {{"
            f"  background: {t['bg2']}; color: {t['text3']};"
            f"  border: 1px solid {t['border']}; border-radius: 11px;"
            f"  font-size: 11px; font-weight: 500;"
            f"  min-width: 22px; max-width: 22px;"
            f"  min-height: 22px; max-height: 22px;"
            f"  qproperty-alignment: AlignCenter;"
            f"}}"
            f"QLabel:hover {{ background: {t['bg3']}; color: {t['text']}; }}"
        )
        self.label_q1.setStyleSheet(q_style)
        self.label_q2.setStyleSheet(q_style)

        self.page_select.layout().setContentsMargins(20, 20, 20, 20)
        self.page_select.layout().setSpacing(16)
        self.page_progress.layout().setContentsMargins(20, 12, 20, 20)
        self.topbar.layout().setContentsMargins(12, 4, 12, 4)

        self._update_output_btn()
        self._set_window_border_color()

    def _set_window_border_color(self):
        """Красим заголовок окна в цвет темы через pywinstyles.
        Работает на Windows 10 и 11.
        Установка: pip install pywinstyles
        """
        import sys
        if sys.platform != "win32":
            return
        try:
            import pywinstyles
            pywinstyles.change_header_color(self, self._t['topbar_bg'])
            pywinstyles.change_border_color(self, self._t['border'])
        except ImportError:
            pass  # pywinstyles не установлен — просто игнорируем
        except Exception:
            pass

    def _update_output_btn(self):
        """Обновляет текст кнопки выбора папки сохранения."""
        short = Path(self._output_dir).name or self._output_dir
        self.btn_choose_output.setText(f"Сохранить в: …/{short}")
        self.btn_choose_output.setToolTip(
            f"Текущая папка:\n{self._output_dir}\n\n"
            "Нажмите чтобы выбрать другое место.\n"
            "Выбор сохраняется между запусками."
        )

    # ── подключение сигналов ──────────────────────────────────────────────

    def _connect(self):
        """Подключает кнопки к методам."""
        self.btn_menu.clicked.connect(self._open_drawer)
        self.btn_back.clicked.connect(self._go_back)
        self.btn_add_folder.clicked.connect(self._add_folder)
        self.btn_choose_output.clicked.connect(self._choose_output)
        self.btn_start.clicked.connect(self._start)
        self.btn_add_from_progress.clicked.connect(self._add_folder_from_progress)
        self.btn_stop_all.clicked.connect(self._stop_all)
        self.btn_open_output.clicked.connect(self._open_output)

    # ── экран 1: выбор папок ──────────────────────────────────────────────

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку со сканами одной книги"
        )
        if not folder:
            return
        if folder in self._folders:
            self.statusBar().showMessage(f"«{Path(folder).name}» уже добавлена.")
            return
        self._folders.append(folder)
        self._update_screen1()

    def _choose_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Куда сохранить PDF", self._output_dir
        )
        if folder:
            self._output_dir = folder
            self._update_output_btn()
            self._save_settings()

    def _update_screen1(self):
        """Обновляет счётчик папок и видимость подсказки."""
        count = len(self._folders)
        if count == 0:
            self.lbl_folder_count.setText("Папки не добавлены")
            self.lbl_start_hint.setVisible(True)
        elif count == 1:
            name = Path(self._folders[0]).name
            self.lbl_folder_count.setText(f"Добавлена 1 папка: {name}")
            self.lbl_start_hint.setVisible(False)
        else:
            names = ", ".join(Path(f).name for f in self._folders)
            self.lbl_folder_count.setText(f"Добавлено папок: {count} ({names})")
            self.lbl_start_hint.setVisible(False)
        self.btn_start.setEnabled(count > 0)

    # ── запуск обработки ──────────────────────────────────────────────────

    def _start(self):
        """Переходим на экран прогресса и запускаем воркер."""
        self.stack.setCurrentIndex(1)
        self.btn_back.setVisible(True)
        self.btn_open_output.setEnabled(False)
        for folder in self._folders:
            self._add_card(folder)
        self._run_worker(self._folders[:])

    def _add_card(self, folder: str):
        """Создаёт карточку книги и добавляет в scroll layout."""
        if folder not in self._cards:
            card = BookCard(folder, self._t, self)
            card.stop_requested.connect(self._on_stop_book)
            self._cards[folder] = card
            idx = self._scroll_layout.count() - 1  # перед stretch
            self._scroll_layout.insertWidget(idx, card)

    def _run_worker(self, folders: list):
        """Создаёт и запускает воркер для списка папок."""
        self._worker = Worker(folders, self._output_dir)
        self._worker.book_started.connect(self._on_started)
        self._worker.step_progress.connect(self._on_progress)
        self._worker.book_done.connect(self._on_done)
        self._worker.book_error.connect(self._on_error)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.status_msg.connect(self.statusBar().showMessage)
        self._worker.start()

    def _add_folder_from_progress(self):
        """Добавить книгу прямо со второго экрана."""
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку со сканами книги"
        )
        if not folder or folder in self._folders:
            if folder in self._folders:
                self.statusBar().showMessage("Эта папка уже добавлена.")
            return
        self._folders.append(folder)
        self._add_card(folder)
        self._run_worker([folder])

    # ── слоты воркера ─────────────────────────────────────────────────────
    # Эти методы вызываются автоматически когда воркер отправляет сигнал

    def _on_started(self, folder: str, total: int):
        card = self._cards.get(folder)
        if card:
            card.set_started(total)

    def _on_progress(self, folder: str, step: int, done: int, total: int):
        card = self._cards.get(folder)
        if card:
            card.update_step(step, done, total)

    def _on_done(self, folder: str):
        card = self._cards.get(folder)
        if card:
            card.set_done()
            pdf = str(Path(self._output_dir) / f"{card.book_name}.pdf")
            self._recent_files.append(pdf)
            self._save_settings()
        self.btn_open_output.setEnabled(True)

    def _on_error(self, folder: str, msg: str):
        card = self._cards.get(folder)
        if msg == "__stopped__":
            if card: card.set_stopped()
            self.statusBar().showMessage(f"Остановлено: {Path(folder).name}")
        else:
            if card: card.set_error(msg)
            self.statusBar().showMessage(f"Ошибка: {Path(folder).name} — {msg}")

    def _on_all_done(self):
        self.btn_open_output.setEnabled(True)
        self.statusBar().showMessage("Все книги обработаны.")

    def _on_stop_book(self, folder: str):
        if hasattr(self, "_worker") and self._worker.isRunning():
            self._worker.cancel_folder(folder)
            self.statusBar().showMessage(f"Остановка «{Path(folder).name}»…")

    # ── управление ────────────────────────────────────────────────────────

    def _stop_all(self):
        if hasattr(self, "_worker") and self._worker.isRunning():
            self._worker.cancel_all()
            self.statusBar().showMessage("Останавливаем все книги…")

    def _go_back(self):
        """Возврат на первый экран — сбрасываем все карточки."""
        self.stack.setCurrentIndex(0)
        self.btn_back.setVisible(False)
        self._folders = []
        self._cards   = {}
        while self._scroll_layout.count() > 1:
            item = self._scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._update_screen1()

    def _open_output(self):
        if not self._output_dir:
            return
        if sys.platform == "win32":
            os.startfile(self._output_dir)
        elif sys.platform == "darwin":
            import subprocess; subprocess.Popen(["open", self._output_dir])
        else:
            import subprocess; subprocess.Popen(["xdg-open", self._output_dir])

    # ── шторка ────────────────────────────────────────────────────────────

    def _open_drawer(self):
        if self._drawer:
            self._drawer.hide()
            self._drawer = None
            return
        self._drawer = Drawer(self._t, self._recent_files)
        self._drawer.set_close_callback(self._close_drawer)
        self._drawer.set_settings_callback(self._open_settings)
        pos = self.mapToGlobal(self.rect().topLeft())
        self._drawer.setGeometry(pos.x(), pos.y(), 220, self.height())
        self._drawer.show()
        self._drawer.raise_()

    def _close_drawer(self):
        if self._drawer:
            self._drawer.hide()
            self._drawer = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_drawer()

    def moveEvent(self, event):
        super().moveEvent(event)
        self._reposition_drawer()

    def _reposition_drawer(self):
        """Двигает шторку вместе с окном."""
        if self._drawer:
            pos = self.mapToGlobal(self.rect().topLeft())
            self._drawer.setGeometry(pos.x(), pos.y(), 220, self.height())

    # ── настройки и тема ──────────────────────────────────────────────────

    def _open_settings(self):
        current = "dark" if self._t == DARK else "light"
        dlg = SettingsDialog(self._t, current, self)
        dlg.theme_changed.connect(self._switch_theme)
        dlg.exec()

    def _switch_theme(self, theme: str):
        self._t = DARK if theme == "dark" else LIGHT
        self._apply_styles()
        self._set_window_border_color()
        self._close_drawer()
        self._save_settings()
        for card in self._cards.values():
            card.theme = self._t
            card._rebuild_styles()

    def _save_settings(self):
        save_settings({
            "output_dir":   self._output_dir,
            "recent_files": self._recent_files[-5:],
            "theme":        "dark" if self._t == DARK else "light",
        })

# ── точка входа ───────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Цифровая библиотека")
    w = MainWindow()
    w.show()
    # небольшая задержка — DWM принимает цвет только после полной отрисовки окна
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(100, w._set_window_border_color)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()