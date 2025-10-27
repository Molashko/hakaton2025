# Скрипт для тестирования API Executor Balancer
# Убедитесь, что n8n запущен на localhost:5678

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

# 1. Тест создания заказа
Write-Host "1. Тестирование создания заказа" -ForegroundColor Yellow
$orderData = @{
    orderId = "TEST-001"
    customerId = "CUST-123"
    description = "Тестовый заказ"
    priority = "high"
    category = "technical"
    estimatedDuration = 30
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/new-order" -Method POST -Body $orderData -ContentType "application/json"
    Test-Result "Создание заказа" ($response | ConvertTo-Json) "success"
} catch {
    Write-Host "❌ Создание заказа - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Тест получения статистики
Write-Host "2. Тестирование получения статистики" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/stats" -Method GET
    Test-Result "Получение статистики" ($response | ConvertTo-Json) "totalAssignments"
} catch {
    Write-Host "❌ Получение статистики - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Тест получения детальной статистики
Write-Host "3. Тестирование детальной статистики" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/stats?includeDetails=true" -Method GET
    Test-Result "Детальная статистика" ($response | ConvertTo-Json) "executorStats"
} catch {
    Write-Host "❌ Детальная статистика - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Тест регистрации исполнителя
Write-Host "4. Тестирование регистрации исполнителя" -ForegroundColor Yellow
$executorData = @{
    id = "test-executor-1"
    name = "Тестовый Исполнитель"
    specialization = "technical"
    rating = 4.8
    maxLoad = 0.8
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/executor/register" -Method POST -Body $executorData -ContentType "application/json"
    Test-Result "Регистрация исполнителя" ($response | ConvertTo-Json) "success"
} catch {
    Write-Host "❌ Регистрация исполнителя - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Тест обновления исполнителя
Write-Host "5. Тестирование обновления исполнителя" -ForegroundColor Yellow
$updateData = @{
    id = "test-executor-1"
    rating = 4.9
    specialization = "urgent"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/executor/update" -Method PUT -Body $updateData -ContentType "application/json"
    Test-Result "Обновление исполнителя" ($response | ConvertTo-Json) "success"
} catch {
    Write-Host "❌ Обновление исполнителя - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}

# 6. Тест проверки состояния системы
Write-Host "6. Тестирование проверки состояния системы" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET
    Test-Result "Проверка состояния" ($response | ConvertTo-Json) "status"
} catch {
    Write-Host "❌ Проверка состояния - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}

# 7. Тест создания срочного заказа
Write-Host "7. Тестирование создания срочного заказа" -ForegroundColor Yellow
$urgentOrderData = @{
    orderId = "URGENT-001"
    customerId = "CUST-456"
    description = "Срочный заказ"
    priority = "urgent"
    category = "urgent"
    estimatedDuration = 15
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/new-order" -Method POST -Body $urgentOrderData -ContentType "application/json"
    Test-Result "Срочный заказ" ($response | ConvertTo-Json) "success"
} catch {
    Write-Host "❌ Срочный заказ - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}


Write-Host "8. Тестирование статистики исполнителя" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/stats?executorId=test-executor-1&includeDetails=true" -Method GET
    Test-Result "Статистика исполнителя" ($response | ConvertTo-Json) "executorStats"
} catch {
    Write-Host "❌ Статистика исполнителя - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}


Write-Host "9. Тестирование удаления исполнителя" -ForegroundColor Yellow
$removeData = @{
    executorId = "test-executor-1"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/executor/remove" -Method DELETE -Body $removeData -ContentType "application/json"
    Test-Result "Удаление исполнителя" ($response | ConvertTo-Json) "success"
} catch {
    Write-Host "❌ Удаление исполнителя - ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "================================================" -ForegroundColor Yellow
Write-Host "🎉 Тестирование завершено!" -ForegroundColor Green
Write-Host ""
Write-Host "Для просмотра логов n8n:"
Write-Host "docker logs executor-balancer-n8n"
Write-Host ""
Write-Host "Для доступа к Redis Commander:"
Write-Host "http://localhost:8081"
Write-Host ""
Write-Host "Для доступа к n8n:"
Write-Host "http://localhost:5678 (admin/admin123)"
