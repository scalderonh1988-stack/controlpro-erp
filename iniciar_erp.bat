@echo off
title CREC-ERP Negocio - ERP Local
cd /d "%~dp0"
echo Iniciando el sistema para el local...
streamlit run app.py
pause