"""
pdf_utils.py — вспомогательные функции для работы с PDF.

Используется в pipeline3.py для финальной обработки PDF:
добавление метаданных PDF/A, чётность страниц,
двустраничный режим просмотра, линеаризация.
"""

import os
import subprocess
from pathlib import Path

import fitz


FONTS_DIR = Path(__file__).parent.parent / "resources"
XMP_PATH  = FONTS_DIR / "pdfa_xmp.xml"
ICC_PATH  = FONTS_DIR / "sRGB.icc"


def make_pdfa(doc: fitz.Document, title: str = "") -> None:
    """
    Добавляет метаданные PDF/A в документ.

    Записывает XMP метаданные и OutputIntent с ICC профилем sRGB —
    минимально необходимые компоненты для соответствия PDF/A-2b.

    Args:
        doc:   открытый документ PyMuPDF
        title: название документа для XMP метаданных
    """
    with open(XMP_PATH, encoding="utf-8") as f:
        xmp = f.read().replace("{title}", title)
    doc.set_xml_metadata(xmp)

    with open(ICC_PATH, "rb") as f:
        icc_data = f.read()

    icc_xref = doc.get_new_xref()
    doc.update_object(icc_xref, "<</N 3>>")
    doc.update_stream(icc_xref, icc_data)

    intent_xref = doc.get_new_xref()
    doc.update_object(intent_xref, f"""
/Type /OutputIntent
/S /GTS_PDFA1
/OutputConditionIdentifier (sRGB IEC61966-2.1)
/Info (sRGB IEC61966-2.1)
/DestOutputProfile {icc_xref} 0 R
>>""")

    catalog_xref = doc.pdf_catalog()
    catalog      = doc.xref_object(catalog_xref)
    if "/OutputIntents" not in catalog:
        doc.update_object(catalog_xref,
                          catalog.replace(">>", f"/OutputIntents [{intent_xref} 0 R]\n>>"))


def add_blank_page(doc: fitz.Document, position: str = "start") -> None:
    """
    Добавляет пустую страницу в начало или конец документа.

    Используется для обеспечения чётности страниц при двустраничном просмотре.

    Args:
        doc:      открытый документ PyMuPDF
        position: "start" для добавления в начало, "end" для добавления в конец
    """
    w, h = doc[0].rect.width, doc[0].rect.height
    doc.insert_page(0 if position == "start" else len(doc), width=w, height=h)


def set_two_page_view(output_path: Path) -> None:
    """
    Устанавливает режим двустраничного просмотра через pikepdf.

    Args:
        output_path: путь к PDF файлу
    """
    try:
        import pikepdf
        with pikepdf.open(str(output_path), allow_overwriting_input=True) as pdf:
            vp = pikepdf.Dictionary(
                Type=pikepdf.Name("/ViewerPreferences"),
                PageLayout=pikepdf.Name("/TwoPageRight"),
                PageMode=pikepdf.Name("/UseNone"),
            )
            pdf.Root["/ViewerPreferences"] = pdf.make_indirect(vp)
            pdf.Root["/PageLayout"]        = pikepdf.Name("/TwoPageRight")
            pdf.save(str(output_path))
    except Exception as e:
        print(f"  Двустраничный режим не установлен: {e}")


def linearize_pdf(path: Path) -> None:
    """
    Линеаризует PDF через qpdf для оптимизации веб-просмотра.

    Линеаризованный PDF загружается побайтово — первая страница
    доступна сразу без загрузки всего файла.

    Args:
        path: путь к PDF файлу (перезаписывается на месте)
    """
    tmp = str(path) + ".tmp.pdf"
    try:
        result = subprocess.run(
            ["qpdf", "--linearize", str(path), tmp],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            os.replace(tmp, str(path))
        else:
            print(f"  Линеаризация не выполнена: {result.stderr}")
    except FileNotFoundError:
        print("  qpdf не найден, линеаризация пропущена")