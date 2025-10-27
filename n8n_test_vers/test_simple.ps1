# Простой тест API Executor Balancer
$BaseUrl = "http://localhost:5678/webhook"

Write-Host "🚀 Тестирование API Executor Balancer" -ForegroundColor Yellow
Write-Host "================================================"

# Функция для вывода результата
function Test-Result {
    param(
        [string]$TestName,
        [string]$Response,
        [string]$ExpectedStatus
    )
    
    if ($Response -match $ExpectedStatus) {
        Write-Host "✅ $TestName - УСПЕШНО" -ForegroundColor Green
    } else {
        Write-Host "❌ $TestName - ОШИБКА" -ForegroundColor Red
        Write-Host "Ответ: $Response"
    }
    Write-Host ""
}

# 1. Тест проверки состояния системы
Write-Host "1. Тестирование проверки состояния системы" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET
    Test-Result "Проверка состояния" ($response | ConvertTo-Json) "status"
} catch {
    Write-Host "❌ Проверка состояния - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Тест получения статистики
Write-Host "2. Тестирование получения статистики" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/stats" -Method GET
    Test-Result "Получение статистики" ($response | ConvertTo-Json) "totalOrders"
} catch {
    Write-Host "❌ Получение статистики - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Тест создания заказа
Write-Host "3. Тестирование создания заказа" -ForegroundColor Yellow
$orderData = @{
    orderId = "TEST-001"
    customerId = "CUST-123"
    description = "Тестовый заказ"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/new-order" -Method POST -Body $orderData -ContentType "application/json"
    Test-Result "Создание заказа" ($response | ConvertTo-Json) "success"
} catch {
    Write-Host "❌ Создание заказа - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "================================================" -ForegroundColor Yellow
Write-Host "🎉 Тестирование завершено!" -ForegroundColor Green
Write-Host ""
Write-Host "Для просмотра логов n8n:"
Write-Host "docker logs n8n"
Write-Host ""
Write-Host "Для доступа к n8n:"
Write-Host "http://localhost:5678 (admin/admin123)"
