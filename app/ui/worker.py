"""
worker.py — фоновый поток обработки книг.

Запускает все три этапа для каждой папки:
    1. run_pipeline  — TIFF → PDF
    2. run_ocr       — PDF → JSON (Chandra OCR)
    3. process_book  — PDF + JSON → PDF/A с текстовым слоем

Сигналы:
    book_started(folder, total)              — начали книгу
    step_progress(folder, step, done, total) — прогресс этапа (step=1/2/3, done=%, total=100)
    book_done(folder)                        — книга готова
    book_error(folder, msg)                  — ошибка ("__stopped__" если остановлена)
    all_done()                               — все книги обработаны
    status_msg(text)                         — текст для статусной строки
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

# Порядок важен: stage_3 (EasyOCR) импортируется до stage_2 (Chandra)
# чтобы избежать конфликта версий torch
_STAGE3_DIR = str(Path(__file__).parent.parent / "stage_3")
_STAGE2_DIR = str(Path(__file__).parent.parent / "stage_2")
_STAGE1_DIR = str(Path(__file__).parent.parent / "stage_1")

for _dir in [_STAGE3_DIR, _STAGE2_DIR, _STAGE1_DIR]:
    if _dir not in sys.path:
        sys.path.insert(0, _dir)


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

    def _is_stopped(self, folder: str) -> bool:
        return self._stop_all or folder in self._stop_folders

    def run(self):
        try:
            from pipeline3 import process_book
            from ocr_chandra import run_ocr
            from pipeline import run_pipeline
        except ImportError as e:
            for folder in self.folders:
                self.book_error.emit(folder, f"Ошибка импорта: {e}")
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

            self.book_started.emit(folder, 100)

            intermediate_pdf  = Path(self.output_dir) / f"{name}.pdf"
            intermediate_json = Path(self.output_dir) / f"{name}.json"
            final_pdf         = Path(self.output_dir) / f"{name}_full.pdf"

            try:
                # --- ЭТАП 1: TIFF → PDF ---
                if self._is_stopped(folder):
                    self.book_error.emit(folder, "__stopped__")
                    continue

                self.status_msg.emit(f"{name}: этап 1 — предобработка…")

                def on_progress_1(pct: int, _folder=folder):
                    if self._is_stopped(_folder):
                        return
                    self.step_progress.emit(_folder, 1, pct, 100)

                run_pipeline(
                    input_folder=Path(folder),
                    output_pdf=intermediate_pdf,
                    dpi=150,
                    has_cover=False,
                    on_progress=on_progress_1,
                )

                # --- ЭТАП 2: PDF → JSON ---
                if self._is_stopped(folder):
                    self.book_error.emit(folder, "__stopped__")
                    continue

                self.status_msg.emit(f"{name}: этап 2 — распознавание текста…")

                def on_progress_2(pct: int, _folder=folder):
                    if self._is_stopped(_folder):
                        return
                    self.step_progress.emit(_folder, 2, pct, 100)

                run_ocr(
                    pdf_path=intermediate_pdf,
                    output_json=intermediate_json,
                    dpi=150,
                    on_progress=on_progress_2,
                )

                # --- ЭТАП 3: PDF + JSON → PDF/A ---
                if self._is_stopped(folder):
                    self.book_error.emit(folder, "__stopped__")
                    continue

                self.status_msg.emit(f"{name}: этап 3 — текстовый слой…")

                def on_progress_3(pct: int, _folder=folder):
                    if self._is_stopped(_folder):
                        return
                    self.step_progress.emit(_folder, 3, pct, 100)

                process_book(
                    pdf_path=intermediate_pdf,
                    json_path=intermediate_json,
                    output_path=final_pdf,
                    starts_on_right=True,
                    has_cover=False,
                    on_progress=on_progress_3,
                )

                # Удаляем промежуточные файлы
                intermediate_pdf.unlink(missing_ok=True)
                intermediate_json.unlink(missing_ok=True)

                if self._is_stopped(folder):
                    self.book_error.emit(folder, "__stopped__")
                else:
                    self.status_msg.emit(f"{name}: готово")
                    self.book_done.emit(folder)

            except Exception as e:
                intermediate_pdf.unlink(missing_ok=True)
                intermediate_json.unlink(missing_ok=True)
                self.book_error.emit(folder, str(e))

        self.all_done.emit()