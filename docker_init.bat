@echo off
chcp 65001 > nul
echo ========================================
echo Инициализация демо-данных (Docker)
echo ========================================
echo.
echo Создание 10 демо-исполнителей...
echo.
echo y| docker-compose run --rm ais python scripts/init_demo_data.py
echo.
echo ========================================
echo Готово! Теперь запустите: docker_start.bat
echo ========================================
pause

