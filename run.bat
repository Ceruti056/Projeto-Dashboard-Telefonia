@echo off
title Dashboard de Telefonia - Streamlit
echo ==============================================
echo   Iniciando Dashboard de Telefonia & Supabase
echo ==============================================
echo.

IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual .venv nao encontrado!
    echo Execute: python -m venv .venv
    echo E depois: .venv\Scripts\pip.exe install -r requirements.txt
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
streamlit run app.py
pause
