@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    set "PY_EXEC=.venv\Scripts\python.exe"
) else (
    set "PY_EXEC=python"
)

if "%~1"=="" (
    echo Iniciando Painel Web Dashboard...
    "%PY_EXEC%" -m src.main ui
) else (
    "%PY_EXEC%" -m src.main %*
)
endlocal
