"""
pipeline3.py — третий этап обработки книг.

Принимает PDF файл и JSON с результатами Chandra OCR,
вставляет невидимый текстовый слой поверх изображений страниц,
добавляет закладки из заголовков и сохраняет результат как PDF/A.
"""

import json
from pathlib import Path

import fitz
import numpy as np
import easyocr
from PIL import Image

from text_placement import (
    get_lines_in_block,
    calc_fontsize,
    get_word_boxes,
    insert_words,
    FONT_PATH,
    FONT_NAME,
)
from pdf_utils import (
    make_pdfa,
    add_blank_page,
    set_two_page_view,
    linearize_pdf,
)

DPI = 150

# Масштаб координат Chandra (0–1000) в пиксели изображения при dpi=150
SX_PX = 1240 / 1000
SY_PX = 1748 / 1000

_reader: easyocr.Reader | None = None


def get_reader() -> easyocr.Reader:
    """
    Возвращает единственный экземпляр EasyOCR Reader (singleton).

    Returns:
        инициализированный EasyOCR Reader для русского и английского языков
    """
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['ru', 'en'], gpu=True)
    return _reader


def process_book(pdf_path: Path,
                 json_path: Path,
                 output_path: Path,
                 starts_on_right: bool = True,
                 has_cover: bool = False,
                 max_pages: int | None = None,
                 on_progress=None) -> None:
    """
    Основная функция третьего этапа. Вставляет текстовый слой в PDF.

    Для каждой страницы: рендерит в изображение, прогоняет через EasyOCR,
    сопоставляет фрагменты с блоками Chandra, вставляет невидимый текст.
    Добавляет закладки из заголовков, обеспечивает чётность страниц,
    сохраняет как PDF/A с линеаризацией.

    Args:
        pdf_path:        путь к входному PDF файлу
        json_path:       путь к JSON файлу с результатами Chandra OCR
        output_path:     путь для сохранения результирующего PDF/A
        starts_on_right: True если книга начинается с правой страницы
        has_cover:       True если первая страница — обложка
        max_pages:       максимальное количество страниц (None = все)
        on_progress:     callback(percent: int) для отслеживания прогресса (0–100)
    """
    pdf_path    = Path(pdf_path)
    json_path   = Path(json_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    fitz_font  = fitz.Font(fontfile=FONT_PATH)
    reader     = get_reader()
    doc        = fitz.open(str(pdf_path))
    pages_data = {p["page"]: p for p in data["pages"]}
    toc        = []

    total_pages = len(doc)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    for i in range(total_pages):
        page_num = i + 1
        page     = doc[i]
        page.insert_font(fontname=FONT_NAME, fontfile=FONT_PATH)
        px_to_pt = page.rect.width / 1240

        page_data = pages_data.get(page_num)
        if not page_data:
            continue

        pix = page.get_pixmap(dpi=DPI)
        img = np.array(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))

        results_full = reader.readtext(img, width_ths=0.001, paragraph=False,
                                       min_size=3, text_threshold=0.4, low_text=0.3)

        for block in page_data.get("blocks", []):
            if block["label"] == "Image" or not block["content"].strip():
                continue

            chandra_words = block["content"].split()
            if not chandra_words:
                continue

            rows, bx1, by1, bx2, by2 = get_lines_in_block(
                block, results_full, SX_PX, SY_PX
            )

            if not rows:
                fontsize = 8
                x  = bx1 * px_to_pt
                cy = (by1 + by2) / 2 * px_to_pt
                for word in chandra_words:
                    page.insert_text(fitz.Point(x, cy), word,
                                     fontname=FONT_NAME, fontsize=fontsize,
                                     render_mode=3)
                    x += fitz_font.text_length(word + " ", fontsize=fontsize)
                continue

            fontsize   = calc_fontsize(chandra_words, rows, px_to_pt, fitz_font)
            word_boxes = get_word_boxes(rows, fontsize, fitz_font, px_to_pt)
            insert_words(chandra_words, word_boxes, rows, page, px_to_pt, fitz_font)

            label = block.get("label", "")
            if "header" in label.lower() or "heading" in label.lower():
                level = 2 if "sub" in label.lower() else 1
                toc.append([level, block["content"][:80], page_num])

        if on_progress:
            on_progress(int((i + 1) / total_pages * 100))

    if toc:
        doc.set_toc(toc)

    # Чётность страниц для двустраничного просмотра
    total_pages = len(doc)
    if has_cover:
        if total_pages % 2 == 0:
            add_blank_page(doc, "start")
    elif starts_on_right:
        if total_pages % 2 == 0:
            add_blank_page(doc, "start")
    if len(doc) % 2 != 0:
        add_blank_page(doc, "end")

    make_pdfa(doc, title=pdf_path.stem)
    doc.save(str(output_path), garbage=4, deflate=True)
    doc.close()

    set_two_page_view(output_path)
    linearize_pdf(output_path)