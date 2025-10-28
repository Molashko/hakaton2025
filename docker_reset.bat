@echo off
chcp 65001 > nul
echo ========================================
echo Сброс всех данных (Docker)
echo ========================================
echo.
echo Остановка контейнеров...
docker-compose down
echo.
echo Инициализация демо-данных...
echo y| docker-compose run --rm ais python scripts/init_demo_data.py
echo.
echo ========================================
echo Готово! Запустите: docker_start.bat
echo ========================================
pause

