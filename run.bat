@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel%==0 (
  python -u app.py
  goto done
)

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -u app.py
  goto done
)

echo Python نصب نیست. از python.org نسخه ۳ را نصب کن و دوباره run.bat را اجرا کن.
pause
exit /b 1

:done
if errorlevel 1 pause
