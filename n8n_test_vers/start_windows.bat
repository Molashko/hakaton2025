@echo off
echo 🚀 Запуск Executor Balancer на Windows
echo ========================================

echo.
echo 1. Запуск Redis...
docker run -d --name executor_redis -p 6379:6379 redis:alpine
if %errorlevel% neq 0 (
    echo ⚠️ Redis уже запущен или ошибка
)

echo ✅ Redis готов

echo.
echo 2. Запуск n8n...
docker run -d --name n8n ^
  -p 5678:5678 ^
  -v "%cd%":/home/node/.n8n ^
  --link executor_redis:redis ^
  n8nio/n8n:latest

if %errorlevel% neq 0 (
    echo ❌ Ошибка запуска n8n
    pause
    exit /b 1
)

echo ✅ n8n запущен

echo.
echo 3. Запуск Redis Commander (опционально)...
docker run -d --name redis-commander ^
  -p 8081:8081 ^
  -e REDIS_HOSTS=local:redis:6379 ^
  --link executor_redis:redis ^
  rediscommander/redis-commander:latest

echo ✅ Redis Commander запущен

echo.
echo ========================================
echo 🎉 Система запущена!
echo.
echo Доступные сервисы:
echo - n8n: http://localhost:5678 (admin/admin123)
echo - Redis Commander: http://localhost:8081
echo.
echo Для остановки выполните: stop_windows.bat
echo Для тестирования выполните: test_api.ps1
echo.
pause
