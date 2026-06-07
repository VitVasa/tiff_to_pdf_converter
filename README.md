# TIFF to PDF Converter

Приложение для пакетной обработки сканов книг для ИНИОН РАН.  
Преобразует папки с TIFF файлами в поисковые PDF/A с текстовым слоем.

## Как работает

1. **Этап 1** — предобработка сканов: выравнивание, обрезка рамок, нормализация яркости → PDF
2. **Этап 2** — распознавание текста через Chandra OCR → JSON
3. **Этап 3** — вставка невидимого текстового слоя, закладки, PDF/A → финальный PDF

## Требования

- Python 3.10+
- GPU с поддержкой CUDA (рекомендуется, без GPU работает медленно)
- 8+ ГБ RAM

## Установка

### Linux / Mac
```bash
git clone https://github.com/your-username/tiff_to_pdf_converter.git
cd tiff_to_pdf_converter
chmod +x setup.sh
./setup.sh
```

### Windows
```bat
git clone https://github.com/your-username/tiff_to_pdf_converter.git
cd tiff_to_pdf_converter
setup.bat
```

## Запуск

### Linux / Mac
```bash
source venv/bin/activate
python main.py
```

### Windows
```bat
venv\Scripts\activate.bat
python main.py
```

## Примечания

- Первый запуск займёт время — Chandra и EasyOCR скачают модели автоматически
- Без GPU обработка одной книги может занять несколько часов
- Промежуточные файлы удаляются автоматически после завершения