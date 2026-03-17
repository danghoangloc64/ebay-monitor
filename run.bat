@echo off
echo ========================================
echo   eBay Monitor - Setup and Run
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python khong duoc tim thay. Hay cai Python truoc: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Cai dat pip packages...
pip install -r ebay_monitor\requirements.txt
if errorlevel 1 (
    echo [ERROR] Cai dat requirements that bai.
    pause
    exit /b 1
)

echo.
echo [2/4] Cai dat Playwright browsers (Chromium)...
playwright install chromium
if errorlevel 1 (
    echo [ERROR] Cai dat Playwright browser that bai.
    pause
    exit /b 1
)

echo.
echo [3/3] Kiem tra file .env...
if not exist ebay_monitor\.env (
    echo [WARNING] Khong tim thay ebay_monitor\.env
    echo    Hay copy ebay_monitor\.env.example thanh ebay_monitor\.env
    echo    va dien TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID vao.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Khoi dong bot...
echo ========================================
cd ebay_monitor
python bot.py
pause
