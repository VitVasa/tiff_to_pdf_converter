"""
book_card.py — карточка одной книги

BookCard — виджет который показывает одну книгу на экране прогресса.

В свёрнутом виде показывает:
  название книги | статус (Ожидает/В обработке/Готово/Ошибка) | стрелка

В раскрытом виде добавляет:
  три прогресс-бара с счётчиками страниц для каждого этапа

Карточка раскрывается автоматически когда книга начинает обрабатываться,
и остаётся раскрытой. Пользователь может также кликнуть на шапку вручную.

Рамка карточки меняет цвет по статусу:
  серая  → ожидает
  жёлтая → в обработке
  зелёная → готово
  красная → ошибка или остановлено

Сигнал stop_requested(folder) — отправляется когда пользователь подтверждает
остановку книги через диалог.
"""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from dialogs import ConfirmDialog

class BookCard(QWidget):
    # сигнал — главное окно слушает его и останавливает воркер
    stop_requested = pyqtSignal(str)  # передаёт путь к папке книги

    def __init__(self, folder: str, theme: dict, parent=None):
        super().__init__(parent)
        self.folder          = folder
        self.book_name       = Path(folder).name
        self.theme           = theme
        self.total           = 0       # количество страниц, узнаём от воркера
        self._expanded       = False
        self._current_status = "wait"  # запоминаем для перекраски при смене темы
        self._build()

    # ── построение интерфейса ─────────────────────────────────────────────

    def _build(self):
        t = self.theme
        self.setObjectName("BookCard")
        self.setStyleSheet(f"""
            QWidget#BookCard {{
                background: {t['bg']};
                border: 2px solid {t['border']};
                border-radius: 10px;
            }}
            QPushButton#btn_stop_book {{
                background: transparent;
                color: {t['text3']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px;
                text-align: center;
            }}
            QPushButton#btn_stop_book:hover {{
                background: {t['err_bg']};
                color: {t['err_fg']};
                border-color: {t['err_fg']};
            }}
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── шапка (всегда видна) ──────────────────────────────────────────
        self._header = QWidget()
        self._header.setStyleSheet("background: transparent;")
        # setCursor убран — вызывал краш на некоторых системах
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(8)
        self._lbl_name = QLabel(self.book_name)
        self._lbl_name.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {t['text']};"
        )

        self._lbl_status = QLabel("Ожидает")
        self._apply_status("wait")

        # кнопка "Стоп" — скрыта пока книга не начала обрабатываться
        self._btn_stop = QPushButton("Стоп")
        self._btn_stop.setObjectName("btn_stop_book")
        self._btn_stop.setFixedHeight(24)
        self._btn_stop.setToolTip("Остановить обработку этой книги")
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_stop.setVisible(False)

        self._lbl_arrow = QLabel("▸")
        self._lbl_arrow.setStyleSheet(f"color: {t['text3']}; font-size: 11px;")

        hl.addWidget(self._lbl_name, stretch=1)
        hl.addWidget(self._lbl_status)
        hl.addWidget(self._btn_stop)
        hl.addWidget(self._lbl_arrow)

        # ── детали (скрыты до раскрытия) ─────────────────────────────────
        self._detail = QWidget()
        self._detail.setStyleSheet(
            f"background: {t['bg2']};"
            f"border-top: 1px solid {t['border']};"
            f"border-radius: 0 0 10px 10px;"
        )
        self._detail.setVisible(False)
        dl = QVBoxLayout(self._detail)
        dl.setContentsMargins(14, 10, 14, 12)
        dl.setSpacing(8)

        # три прогресс-бара — по одному на каждый этап
        # храним в словарях чтобы обращаться по номеру этапа: self._bars[1]
        self._bars:    dict[int, QProgressBar] = {}
        self._clabels: dict[int, QLabel]       = {}
        self._slabels: dict[int, QLabel]       = {}  # лейблы "Этап N — ..."

        for num, label_text in [
            (1, "Этап 1 — выравнивание страниц"),
            (2, "Этап 2 — распознавание текста"),
            (3, "Этап 3 — сборка PDF"),
        ]:
            row = QVBoxLayout()
            row.setSpacing(3)
            top = QHBoxLayout()

            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"font-size: 11px; color: {t['text2']};")
            self._slabels[num] = lbl

            # счётчик страниц: "0 / 312"
            clbl = QLabel("—")
            clbl.setStyleSheet(f"font-size: 11px; color: {t['text3']};")
            self._clabels[num] = clbl

            top.addWidget(lbl, stretch=1)
            top.addWidget(clbl)

            bar = QProgressBar()
            bar.setFixedHeight(5)
            bar.setTextVisible(False)
            bar.setValue(0)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background: {t['bar_track']};
                    border: none; border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    border-radius: 3px; background: {t['bar_proc']};
                }}
            """)
            self._bars[num] = bar

            row.addLayout(top)
            row.addWidget(bar)
            dl.addLayout(row)

        outer.addWidget(self._header)
        outer.addWidget(self._detail)

        # клик по шапке — раскрыть/свернуть
        self._header.mousePressEvent = lambda e: self._toggle()

    # ── раскрытие / сворачивание ──────────────────────────────────────────

    def _toggle(self):
        self._expanded = not self._expanded
        self._detail.setVisible(self._expanded)
        self._lbl_arrow.setText("▾" if self._expanded else "▸")

    # ── статус и цвет рамки ───────────────────────────────────────────────

    def _apply_status(self, state: str):
        """Меняет плашку статуса и цвет рамки карточки."""
        self._current_status = state
        t = self.theme
        s = {
            "wait":    (t['wait_bg'], t['wait_fg'], "Ожидает"),
            "proc":    (t['proc_bg'], t['proc_fg'], "В обработке"),
            "done":    (t['done_bg'], t['done_fg'], "Готово ✓"),
            "err":     (t['err_bg'],  t['err_fg'],  "Ошибка"),
            "stopped": (t['err_bg'],  t['err_fg'],  "Остановлено"),
        }
        bg, fg, label = s.get(state, s["wait"])
        self._lbl_status.setText(label)
        self._lbl_status.setStyleSheet(
            f"background: {bg}; color: {fg}; font-size: 11px;"
            f"padding: 3px 10px; border-radius: 8px;"
        )
        # обновляем рамку только если прогресс-бары уже созданы
        if hasattr(self, '_bars'):
            self._update_border(state)

    def _update_border(self, state: str):
        """
        Меняет цвет рамки карточки.
        Вызывается отдельно от _apply_status чтобы не сбросить
        стили прогресс-баров — setStyleSheet на родителе их перекрашивает.
        Поэтому после setStyleSheet сразу восстанавливаем стили баров.
        """
        t = self.theme
        border_color = {
            "wait":    t['border'],
            "proc":    t['proc_fg'],
            "done":    t['done_fg'],
            "err":     t['err_fg'],
            "stopped": t['err_fg'],
        }.get(state, t['border'])

        self.setStyleSheet(f"""
            QWidget#BookCard {{
                background: {t['bg']};
                border: 2px solid {border_color};
                border-radius: 10px;
            }}
            QPushButton#btn_stop_book {{
                background: transparent; color: {t['text3']};
                border: 1px solid {t['border']}; border-radius: 6px;
                padding: 2px 8px; font-size: 11px; text-align: center;
            }}
            QPushButton#btn_stop_book:hover {{
                background: {t['err_bg']}; color: {t['err_fg']};
                border-color: {t['err_fg']};
            }}
        """)

        # восстанавливаем стили прогресс-баров после setStyleSheet
        for bar in self._bars.values():
            is_done = bar.value() == bar.maximum() and bar.maximum() > 0
            bar_color = t['bar_done'] if is_done else t['bar_proc']
            bar.setStyleSheet(f"""
                QProgressBar {{ background: {t['bar_track']}; border: none; border-radius: 3px; }}
                QProgressBar::chunk {{ border-radius: 3px; background: {bar_color}; }}
            """)

    # ── кнопка стоп ───────────────────────────────────────────────────────

    def _on_stop(self):
        """Показывает диалог подтверждения. При согласии — отправляет сигнал."""
        dlg = ConfirmDialog(self.book_name, self.theme, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.stop_requested.emit(self.folder)

    # ── публичные методы — вызываются из MainWindow ───────────────────────

    def set_started(self, total: int):
        """Книга начала обрабатываться. total — количество страниц."""
        self.total = total
        for bar in self._bars.values():
            bar.setMaximum(total)
            bar.setValue(0)
        for lbl in self._clabels.values():
            lbl.setText(f"0 / {total}")
        self._apply_status("proc")
        self._btn_stop.setVisible(True)
        if not self._expanded:
            self._toggle()

    def update_step(self, step: int, done: int, total: int):
        """Обновляет прогресс одного этапа. Зеленеет сразу когда этап готов."""
        if step in self._bars:
            self._bars[step].setMaximum(total)
            self._bars[step].setValue(done)
            self._clabels[step].setText(f"{done} / {total}")
            if done == total:
                t = self.theme
                self._bars[step].setStyleSheet(f"""
                    QProgressBar {{ background: {t['bar_track']}; border: none; border-radius: 3px; }}
                    QProgressBar::chunk {{ border-radius: 3px; background: {t['bar_done']}; }}
                """)

    def set_done(self):
        """Все этапы завершены — красим всё в зелёный."""
        self._apply_status("done")
        self._btn_stop.setVisible(False)
        t = self.theme
        for bar in self._bars.values():
            bar.setValue(self.total)
            bar.setStyleSheet(f"""
                QProgressBar {{ background: {t['bar_track']}; border: none; border-radius: 3px; }}
                QProgressBar::chunk {{ border-radius: 3px; background: {t['bar_done']}; }}
            """)

    def set_error(self, msg: str):
        """Ошибка при обработке."""
        self._apply_status("err")
        self._btn_stop.setVisible(False)
        self.setToolTip(msg)

    def set_stopped(self):
        """Пользователь остановил обработку."""
        self._apply_status("stopped")
        self._btn_stop.setVisible(False)

    def _rebuild_styles(self):
        """Перекрашивает всю карточку при смене темы."""
        t = self.theme
        self._lbl_name.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {t['text']};"
        )
        self._lbl_arrow.setStyleSheet(f"color: {t['text3']}; font-size: 11px;")
        self._detail.setStyleSheet(
            f"background: {t['bg2']};"
            f"border-top: 1px solid {t['border']};"
            f"border-radius: 0 0 10px 10px;"
        )
        for lbl in self._clabels.values():
            lbl.setStyleSheet(f"font-size: 11px; color: {t['text3']};")
        for lbl in self._slabels.values():
            lbl.setStyleSheet(f"font-size: 11px; color: {t['text2']};")
        # перекрашиваем статус и рамку с текущим статусом
        self._apply_status(self._current_status)