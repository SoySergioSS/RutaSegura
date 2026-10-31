@echo off
chcp 65001 >nul
title Focos de Alerta
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro Python. Instalalo desde https://www.python.org/downloads/
    echo         y marca la opcion "Add Python to PATH".
    pause
    exit /b 1
)

python -c "import flask" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias...
    python -m pip install -r requirements.txt
)

if not exist "data\focos.db" (
    echo Cargando datos de demostracion...
    python herramientas\generar_datos_demo.py
)

echo.
echo Focos de Alerta se esta ejecutando en http://localhost:5000
echo Para detenerlo, cierra esta ventana o presiona Ctrl + C.
echo.
start "" http://localhost:5000
python app.py
pause
