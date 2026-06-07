"""
ocr_chandra.py — второй этап обработки книг.

Принимает PDF файл, прогоняет каждую страницу через Chandra OCR
и сохраняет результат как JSON файл.

Структура JSON:
    {
        "source_file": "1_ocr.pdf",
        "dpi": 150,
        "total_pages": 16,
        "pages": [
            {
                "page": 1,
                "width_px": 1240,
                "height_px": 1748,
                "markdown": "...",
                "blocks": [
                    {
                        "bbox": [x1, y1, x2, y2],  # координаты в диапазоне 0–1000
                        "label": "Text",
                        "content": "текст блока"
                    }
                ]
            }
        ]
    }
"""

import gc
import re
import json
import ctypes
from pathlib import Path

import torch
import fitz
from PIL import Image

from chandra.model import InferenceManager
from chandra.model.schema import BatchInputItem
from chandra.output import parse_markdown

_manager: InferenceManager | None = None


def get_manager() -> InferenceManager:
    """
    Возвращает единственный экземпляр InferenceManager (singleton).

    Returns:
        инициализированный InferenceManager
    """
    global _manager
    if _manager is None:
        _manager = InferenceManager(method="hf")
    return _manager


def clean_memory() -> None:
    """
    Освобождает память GPU и RAM после обработки каждой страницы.
    """
    gc.collect()
    torch.cuda.empty_cache()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


def parse_raw_blocks(raw: str) -> list[dict]:
    """
    Извлекает блоки текста из сырого HTML вывода Chandra.

    Chandra возвращает HTML с div-элементами содержащими
    координаты bbox и метку блока (Text, Header, Image и т.д.).

    Args:
        raw: сырой HTML вывод Chandra

    Returns:
        список словарей с ключами bbox, label, content
    """
    blocks = []
    pattern = re.compile(
        r'<div\s+data-bbox="([^"]+)"\s+data-label="([^"]+)">(.*?)</div>',
        re.DOTALL
    )
    for m in pattern.finditer(raw):
        try:
            bbox = [int(x) for x in m.group(1).split()]
        except ValueError:
            continue

        label   = m.group(2)
        content = re.sub(r'<[^>]+>', ' ', m.group(3)).strip()
        content = re.sub(r'\s+', ' ', content)

        if bbox and content:
            blocks.append({
                "bbox":    bbox,
                "label":   label,
                "content": content,
            })
    return blocks


def recognize_page(image: Image.Image) -> dict:
    """
    Распознаёт текст на одной странице через Chandra OCR.

    Args:
        image: страница в формате PIL Image (RGB)

    Returns:
        словарь с ключами:
            markdown: текст страницы в формате markdown
            blocks:   список блоков с координатами и текстом
    """
    manager = get_manager()
    result = manager.generate(
        [BatchInputItem(image=image, prompt_type="ocr_layout")]
    )[0]
    return {
        "markdown": parse_markdown(result.raw),
        "blocks":   parse_raw_blocks(result.raw),
    }


def run_ocr(pdf_path: Path,
            output_json: Path,
            dpi: int = 150,
            max_pages: int | None = None,
            on_progress=None) -> None:
    """
    Основная функция второго этапа. Прогоняет PDF через Chandra OCR.

    Для каждой страницы: рендерит в изображение, распознаёт текст,
    извлекает блоки с координатами. Сохраняет результат в JSON.

    Args:
        pdf_path:    путь к входному PDF файлу
        output_json: путь для сохранения результирующего JSON
        dpi:         разрешение рендеринга страниц (по умолчанию 150)
        max_pages:   максимальное количество страниц (None = все)
        on_progress: callback(percent: int) для отслеживания прогресса (0–100)
    """
    pdf_path    = Path(pdf_path)
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    doc   = fitz.open(str(pdf_path))
    total = len(doc)
    if max_pages:
        total = min(total, max_pages)

    pages = []
    for i in range(total):
        pix = doc[i].get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        w, h = pix.width, pix.height
        del pix

        res = recognize_page(img)
        pages.append({
            "page":      i + 1,
            "width_px":  w,
            "height_px": h,
            "markdown":  res["markdown"],
            "blocks":    res["blocks"],
        })
        del img, res
        clean_memory()

        if on_progress:
            on_progress(int((i + 1) / total * 100))

    doc.close()

    result = {
        "source_file": pdf_path.name,
        "dpi":         dpi,
        "total_pages": total,
        "pages":       pages,
    }
    output_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )