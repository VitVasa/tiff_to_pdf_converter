@echo off
:: Установка зависимостей для Windows

echo === Проверка winget ===
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo Предупреждение: winget не найден.
    echo Установите qpdf вручную: https://github.com/qpdf/qpdf/releases
    echo Установите шрифт DejaVu вручную: https://dejavu-fonts.github.io/
    goto python_deps
)

echo === Установка системных зависимостей ===
winget install --id qpdf.qpdf -e --silent
echo Шрифт DejaVu: скачайте вручную https://dejavu-fonts.github.io/

:python_deps
echo === Создание виртуального окружения ===
python -m venv venv
call venv\Scripts\activate.bat

echo === Установка Python зависимостей ===
pip install --upgrade pip
pip install -r requirements.txt

echo === Готово ===
echo Для запуска: venv\Scripts\activate.bat и python main.py
pause