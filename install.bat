@echo off
setlocal enabledelayedexpansion
title Instalador - Instagram Viral Reels AI Agent
cd /d "%~dp0"

echo ===================================================
echo   Instagram Viral Reels AI Agent - Instalador
echo ===================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERRO] Python nao foi encontrado no sistema!
        echo Baixe e instale o Python 3.10+ em https://www.python.org/
        echo Marque a opcao "Add Python to PATH" durante a instalacao.
        pause
        exit /b 1
    ) else (
        set PYTHON_BIN=py
    )
) else (
    set PYTHON_BIN=python
)

%PYTHON_BIN% install.py %*
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] O processo finalizou com erros.
    pause
    exit /b %errorlevel%
)

echo.
pause
