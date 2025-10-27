@echo off
echo 🚀 Тестирование API Executor Balancer
echo ========================================

echo.
echo 1. Проверка состояния системы...
curl http://localhost:5678/webhook/health
echo.

echo.
echo 2. Получение статистики...
curl http://localhost:5678/webhook/stats
echo.

echo.
echo 3. Создание заказа...
curl -X POST http://localhost:5678/webhook/new-order -H "Content-Type: application/json" -d "{\"orderId\":\"TEST-001\",\"customerId\":\"CUST-123\",\"description\":\"Тестовый заказ\"}"
echo.

echo.
echo ========================================
echo 🎉 Тестирование завершено!
echo.
echo Для доступа к n8n:
echo http://localhost:5678 (admin/admin123)
echo.
pause
