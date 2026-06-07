#!/bin/bash
# Установка зависимостей для Linux/Mac

set -e

echo "=== Установка системных зависимостей ==="
if command -v apt-get &> /dev/null; then
    sudo apt-get update -q
    sudo apt-get install -y qpdf fonts-dejavu
elif command -v brew &> /dev/null; then
    brew install qpdf
    echo "Шрифт DejaVu: скачайте вручную https://dejavu-fonts.github.io/"
else
    echo "Предупреждение: apt-get и brew не найдены. Установите qpdf вручную."
fi

echo "=== Создание виртуального окружения ==="
python3 -m venv venv
source venv/bin/activate

echo "=== Установка Python зависимостей ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Готово ==="
echo "Для запуска: source venv/bin/activate && python main.py"