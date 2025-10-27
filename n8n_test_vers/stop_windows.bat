@echo off
echo 🛑 Остановка Executor Balancer
echo =============================

echo.
echo Остановка контейнеров...

docker stop n8n executor_redis redis-commander 2>nul
if %errorlevel% equ 0 (
    echo ✅ Контейнеры остановлены
) else (
    echo ⚠️ Некоторые контейнеры уже остановлены
)

echo.
echo Удаление контейнеров...
docker rm n8n executor_redis redis-commander 2>nul
if %errorlevel% equ 0 (
    echo ✅ Контейнеры удалены
) else (
    echo ⚠️ Некоторые контейнеры уже удалены
)

echo.
echo =============================
echo 🎉 Система остановлена!
echo.
pause
