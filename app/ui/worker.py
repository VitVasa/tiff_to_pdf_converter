"""
worker.py — фоновый поток обработки книг

Запускает run_pipeline из pipeline.py для каждой папки.
Прогресс получает через callback on_progress(percent).

Сигналы:
  book_started(folder, total)              — начали книгу
  step_progress(folder, step, done, total) — прогресс (step=1, done=%, total=100)
  book_done(folder)                        — книга готова
  book_error(folder, msg)                  — ошибка ("__stopped__" если остановлена)
  all_done()                               — все книги обработаны
  status_msg(text)                         — текст для статусной строки
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

# добавляем папку stage_1 чтобы Python нашёл pipeline.py
_STAGE1_DIR = str(Path(__file__).parent.parent / "stage_1")
if _STAGE1_DIR not in sys.path:
    sys.path.insert(0, _STAGE1_DIR)


class Worker(QThread):
    book_started  = pyqtSignal(str, int)
    step_progress = pyqtSignal(str, int, int, int)  # folder, step, done, total
    book_done     = pyqtSignal(str)
    book_error    = pyqtSignal(str, str)
    all_done      = pyqtSignal()
    status_msg    = pyqtSignal(str)

    def __init__(self, folders: list, output_dir: str):
        super().__init__()
        self.folders       = list(folders)
        self.output_dir    = output_dir
        self._stop_all     = False
        self._stop_folders = set()

    def cancel_all(self):
        self._stop_all = True

    def cancel_folder(self, folder: str):
        self._stop_folders.add(folder)

    def run(self):
        try:
            from pipeline import run_pipeline
        except ImportError as e:
            for folder in self.folders:
                self.book_error.emit(folder, f"Не найден pipeline.py: {e}")
            self.all_done.emit()
            return

        for folder in self.folders:
            if self._stop_all:
                break
            if folder in self._stop_folders:
                continue

            name = Path(folder).name

            tiff_count = sum(
                1 for f in Path(folder).iterdir()
                if f.suffix.lower() in ('.tif', '.tiff')
            )
            if tiff_count == 0:
                self.book_error.emit(folder, "TIFF файлы не найдены")
                continue

            # total=100 — прогресс в процентах
            self.book_started.emit(folder, 100)
            self.status_msg.emit(f"{name}: обработка…")

            def on_progress(pct: int, _folder=folder):
                if self._stop_all or _folder in self._stop_folders:
                    return
                self.step_progress.emit(_folder, 1, pct, 100)

            try:
                if self._stop_all or folder in self._stop_folders:
                    self.book_error.emit(folder, "__stopped__")
                    continue

                output_pdf = Path(self.output_dir) / f"{name}.pdf"

                run_pipeline(
                    input_folder=Path(folder),
                    output_pdf=output_pdf,
                    dpi=150,
                    has_cover=False,
                    on_progress=on_progress,
                )

                if self._stop_all or folder in self._stop_folders:
                    self.book_error.emit(folder, "__stopped__")
                else:
                    self.book_done.emit(folder)

            except Exception as e:
                self.book_error.emit(folder, str(e))

        self.all_done.emit()