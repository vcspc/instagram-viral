@echo off
setlocal
cd /d "%~dp0"
echo ===================================================
echo   Compilando Executavel Standalone (.exe)
echo ===================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PY_EXEC=.venv\Scripts\python.exe"
) else (
    set "PY_EXEC=python"
)

"%PY_EXEC%" build_exe.py %*
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha na compilacao do executavel.
    pause
    exit /b %errorlevel%
)

echo.
pause
