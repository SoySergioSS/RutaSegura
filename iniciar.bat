@echo off
cd /d "%~dp0"
if not exist "data\focos.db" python herramientas\generar_datos_demo.py
start "" http://localhost:5000
python app.py
