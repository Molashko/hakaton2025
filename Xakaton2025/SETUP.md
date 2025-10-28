# 🚀 Executor Balancer - Инструкции по запуску

## Быстрый старт

### 1. Подготовка окружения

```bash
# Клонировать проект
git clone <repository-url>
cd executor-balancer

# Создать виртуальное окружение (опционально)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установить зависимости
pip install -r requirements.txt
```

### 2. Запуск через Docker Compose

```bash
# Запустить все сервисы
docker-compose up -d

# Проверить статус
docker-compose ps

# Просмотр логов
docker-compose logs -f app
```

### 3. Инициализация базы данных

```bash
# Запустить миграции
alembic upgrade head

# Создать начальные данные
python init_db.py
```

### 4. Проверка работы

```bash
# Запустить демо
python demo.py

# Или проверить API
curl http://localhost:8000/v1/health
```

## Доступные сервисы

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Streamlit Dashboard**: http://localhost:8501
- **Prometheus**: http://localhost:9090
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Ручной запуск (без Docker)

### 1. Запуск PostgreSQL и Redis

```bash
# PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_DB=executor_balancer \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15

# Redis
docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 2. Запуск приложения

```bash
# Терминал 1: API сервер
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Терминал 2: Worker
python app/worker.py

# Терминал 3: Streamlit
streamlit run streamlit_app/dashboard.py --server.port 8501

# Терминал 4: Prometheus (опционально)
prometheus --config.file=prometheus.yml
```

## Тестирование

```bash
# Запуск тестов
pytest tests/ -v

# Запуск с покрытием
pytest --cov=app tests/

# Запуск линтеров
flake8 app/ tests/
black --check app/ tests/
isort --check-only app/ tests/
```

## Мониторинг

### Prometheus метрики

- `assignments_total` - Общее количество назначений
- `assignment_latency_seconds` - Время обработки заявок
- `mae_fairness` - Показатель справедливости
- `queue_lag` - Задержка в очереди
- `executor_utilization` - Загрузка исполнителей

### Логи

```bash
# Просмотр логов приложения
docker-compose logs -f app

# Просмотр логов worker
docker-compose logs -f worker

# Просмотр логов всех сервисов
docker-compose logs -f
```

## Устранение неполадок

### Проблемы с подключением к БД

```bash
# Проверить статус PostgreSQL
docker-compose ps postgres

# Проверить логи
docker-compose logs postgres

# Перезапустить БД
docker-compose restart postgres
```

### Проблемы с Redis

```bash
# Проверить статус Redis
docker-compose ps redis

# Проверить подключение
redis-cli -h localhost -p 6379 ping
```

### Проблемы с миграциями

```bash
# Сбросить миграции
alembic downgrade base
alembic upgrade head

# Создать новую миграцию
alembic revision --autogenerate -m "description"
```

## Производительность

### Настройка для production

```bash
# Увеличить лимиты PostgreSQL
docker-compose exec postgres psql -U postgres -d executor_balancer -c "
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
SELECT pg_reload_conf();
"

# Настройка Redis
docker-compose exec redis redis-cli CONFIG SET maxmemory 512mb
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Масштабирование

```bash
# Запуск нескольких worker'ов
docker-compose up --scale worker=3

# Или вручную
python app/worker.py &
python app/worker.py &
python app/worker.py &
```

## Разработка

### Структура проекта

```
executor_balancer/
├── app/                    # Основное приложение
│   ├── main.py            # FastAPI приложение
│   ├── models.py          # SQLAlchemy модели
│   ├── schemas.py         # Pydantic схемы
│   ├── database.py        # Подключение к БД
│   ├── worker.py          # Worker для Redis Streams
│   ├── rule_engine.py     # JSON-DSL движок правил
│   ├── services/          # Бизнес-логика
│   └── utils/             # Утилиты
├── streamlit_app/         # Streamlit дашборд
├── alembic/              # Миграции БД
├── tests/                 # Тесты
├── docker-compose.yaml   # Docker конфигурация
└── requirements.txt      # Зависимости
```

### Добавление новых функций

1. Создать модель в `app/models.py`
2. Создать схему в `app/schemas.py`
3. Добавить эндпоинт в `app/main.py`
4. Создать миграцию: `alembic revision --autogenerate -m "description"`
5. Добавить тесты в `tests/`

### Отладка

```bash
# Запуск с отладкой
python -m debugpy --listen 5678 --wait-for-client app/main.py

# Подключение к отладчику в VS Code
# Добавить конфигурацию в .vscode/launch.json
```

## Безопасность

### Настройка HTTPS

```bash
# Генерация SSL сертификатов
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Запуск с HTTPS
uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

### Настройка аутентификации

```bash
# Установка дополнительных зависимостей
pip install python-jose[cryptography] passlib[bcrypt]

# Настройка JWT токенов в app/config.py
```

## Поддержка

Для вопросов и предложений:
- Создать Issue в репозитории
- Написать в Telegram: @your_username
- Email: your.email@example.com
