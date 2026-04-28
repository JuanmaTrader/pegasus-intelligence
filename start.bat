@echo off
title PEGASUS TRADING TOOLS — Market Intelligence Backend

echo.
echo  ═══════════════════════════════════════════════════
echo    PEGASUS TRADING TOOLS — Market Intelligence
echo    Backend v1.0
echo  ═══════════════════════════════════════════════════
echo.

:: Configura tu API key aquí o en variables de entorno
:: set ANTHROPIC_API_KEY=sk-ant-tu-key-aqui
:: set NEWS_API_KEY=tu-newsapi-key (opcional)

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python no encontrado. Instala Python 3.10+
    pause
    exit /b
)

:: Instalar dependencias si faltan
echo  Verificando dependencias...
pip install yfinance anthropic flask requests pandas fredapi -q

echo.
echo  Iniciando servidor en http://localhost:5050
echo  Presiona Ctrl+C para detener
echo.

python backend.py

pause
