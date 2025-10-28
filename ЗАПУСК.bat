@echo off
chcp 65001 > nul
echo ========================================
echo АИС - Система распределения заявок
echo ========================================
echo.
echo Запуск интерфейса...
echo.
cd streamlit_app
streamlit run ais_app.py

