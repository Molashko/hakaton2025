@echo off
chcp 65001 > nul
echo ========================================
echo АИС - Запуск через Docker
echo ========================================
echo.
echo Запуск системы...
echo Streamlit будет доступен на: http://localhost:8501
echo.
echo Для остановки нажмите Ctrl+C
echo ========================================
echo.
docker-compose up -d
echo Запущенно
echo ========================================
echo.