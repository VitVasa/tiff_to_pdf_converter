"""
pipeline.py — первый этап обработки книг.

Принимает папку с TIFF файлами, выполняет предобработку каждой страницы
через image_processing.py и сохраняет результат как единый PDF файл.
"""

import re
import tempfile
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from image_processing import (
    load_image_downscaled,
    fix_orientation,
    should_trim,
    trim_scan_borders,
    get_page_bg_brightness,
    normalize_brightness,
)


def extract_page_number(filename: str) -> int:
    """
    Извлекает номер страницы из имени файла.

    Args:
        filename: имя файла (например, "page_003.tiff")

    Returns:
        номер страницы, или 10**9 если номер не найден
    """
    match = re.search(r"(\d+)(?=\D*$)", filename)
    return int(match.group(1)) if match else 10**9


def find_tiff_files(folder: Path) -> list[Path]:
    """
    Возвращает список TIFF файлов из папки, отсортированных по номеру страницы.

    Args:
        folder: путь к папке с TIFF файлами

    Returns:
        список Path объектов, отсортированных по номеру страницы
    """
    files = [
        p for p in folder.iterdir()
        if p.suffix.lower() in {".tif", ".tiff"}
    ]
    files.sort(key=lambda x: (extract_page_number(x.name), x.name.lower()))
    return files


def run_pipeline(input_folder: Path,
                 output_pdf: Path,
                 dpi: int = 200,
                 has_cover: bool = False,
                 starts_on_right: bool = True,
                 max_pages: int | None = None,
                 on_progress=None) -> None:
    """
    Основная функция первого этапа. Преобразует папку с TIFF файлами в PDF.

    Выполняет для каждой страницы: исправление ориентации, обрезку рамок
    сканера, нормализацию яркости, масштабирование под A4.
    Сохраняет результат как единый PDF с настройками двустраничного просмотра.

    Args:
        input_folder:    путь к папке с TIFF файлами
        output_pdf:      путь для сохранения результирующего PDF
        dpi:             разрешение для сохранения изображений в PDF
        has_cover:       True если первая страница — обложка (зарезервировано)
        starts_on_right: True если книга начинается с правой страницы (зарезервировано)
        max_pages:       максимальное количество страниц (None = все)
        on_progress:     callback(percent: int) для отслеживания прогресса (0–100)
    """
    files = find_tiff_files(input_folder)
    if max_pages:
        files = files[:max_pages]

    total = len(files)
    if total == 0:
        raise ValueError(f"TIFF файлы не найдены в {input_folder}")

    target_h = int(11.7 * dpi)
    target_w = int(8.27 * dpi)
    tmp_dir = Path(tempfile.mkdtemp(prefix="pipeline_tmp_"))

    try:
        tmp_files = []
        brightnesses = []

        for idx, f in enumerate(files):
            img = load_image_downscaled(f)
            img = fix_orientation(img)
            if should_trim(img):
                img = trim_scan_borders(img)

            h, w = img.shape[:2]
            pre_scale = min(target_h / h, target_w / w)
            if pre_scale < 1.0:
                img = cv2.resize(img,
                                 (max(1, int(w * pre_scale)), max(1, int(h * pre_scale))),
                                 interpolation=cv2.INTER_AREA)

            brightnesses.append(get_page_bg_brightness(img))
            tmp_path = tmp_dir / (f.stem + ".png")
            cv2.imwrite(str(tmp_path), img)
            tmp_files.append(tmp_path)
            del img

            if on_progress:
                on_progress(int((idx + 1) / total * 50))

        sizes = [cv2.imread(str(f)).shape[:2] for f in tmp_files]
        hs = sorted([s[0] for s in sizes])
        ws = sorted([s[1] for s in sizes])
        med_h = hs[len(hs) // 2]
        med_w = ws[len(ws) // 2]
        a4_scale = min(target_h / med_h, target_w / med_w)
        canvas_h = max(1, int(med_h * a4_scale))
        canvas_w = max(1, int(med_w * a4_scale))

        imgs = [cv2.imread(str(f)) for f in tmp_files]
        imgs = normalize_brightness(imgs, brightnesses)

        pil_pages = []
        for idx, img in enumerate(imgs):
            h, w = img.shape[:2]
            scale = min(canvas_h / h, canvas_w / w)
            img = cv2.resize(img,
                             (max(1, int(w * scale)), max(1, int(h * scale))),
                             interpolation=cv2.INTER_AREA)
            if img.shape[1] != canvas_w or img.shape[0] != canvas_h:
                img = cv2.resize(img, (canvas_w, canvas_h), interpolation=cv2.INTER_AREA)
            pil_pages.append(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
            del img

            if on_progress:
                on_progress(50 + int((idx + 1) / total * 50))

        output_pdf = Path(output_pdf)
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        pil_pages[0].save(output_pdf, save_all=True,
                          append_images=pil_pages[1:], resolution=dpi)

        try:
            import pikepdf
            with pikepdf.open(str(output_pdf), allow_overwriting_input=True) as pdf:
                vp = pikepdf.Dictionary(
                    Type=pikepdf.Name("/ViewerPreferences"),
                    PageLayout=pikepdf.Name("/TwoPageRight"),
                    PageMode=pikepdf.Name("/UseNone"),
                )
                pdf.Root["/ViewerPreferences"] = pdf.make_indirect(vp)
                pdf.Root["/PageLayout"] = pikepdf.Name("/TwoPageRight")
                pdf.save(str(output_pdf))
        except Exception as e:
            print(f"  Двустраничный режим не установлен: {e}")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)