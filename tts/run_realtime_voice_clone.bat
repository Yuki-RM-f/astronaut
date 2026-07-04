@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
  echo 未找到虚拟环境 Python: %cd%\venv\Scripts\python.exe
  pause
  exit /b 1
)

"venv\Scripts\python.exe" -m voice_clone_app
pause

