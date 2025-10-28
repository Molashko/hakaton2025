# 🐳 ЗАПУСК ЧЕРЕЗ DOCKER

## ✅ Что уже готово

У вас всё настроено для работы через Docker:
- ✅ `Dockerfile` - образ с Python и зависимостями
- ✅ `docker-compose.yaml` - Streamlit на порту 8501
- ✅ `requirements.txt` - все необходимые зависимости
- ✅ Docker Desktop установлен

---

## 🚀 БЫСТРЫЙ ЗАПУСК (2 команды)

### Шаг 1: Инициализация демо-данных
```bash
docker-compose run --rm ais python scripts/init_demo_data.py
```
*При запросе "Пересоздать БД с нуля?" введите: `y`*

### Шаг 2: Запуск системы
```bash
docker-compose up
```

### Шаг 3: Открыть в браузере
```
http://localhost:8501
```

**Готово!** 🎉

---

## 📝 ДЕТАЛЬНАЯ ИНСТРУКЦИЯ

### 1. Первый запуск (с инициализацией)

```bash
# Остановить и удалить старые контейнеры (если есть)
docker-compose down

# Пересобрать образы (если были изменения)
docker-compose build

# Инициализировать демо-данные
docker-compose run --rm ais python scripts/init_demo_data.py

# Запустить систему
docker-compose up
```

### 2. Обычный запуск (после инициализации)

```bash
# Просто запустить
docker-compose up

# Или в фоновом режиме
docker-compose up -d

# Посмотреть логи
docker-compose logs -f ais
```

### 3. Остановка

```bash
# Остановить (сохранить данные)
docker-compose stop

# Остановить и удалить контейнеры (сохранить данные)
docker-compose down

# Удалить всё включая данные
docker-compose down -v
```

---

## 🔧 УПРАВЛЕНИЕ ДАННЫМИ

### Инициализация демо-данных
```bash
# Создать 10 демо-исполнителей
docker-compose run --rm ais python scripts/init_demo_data.py
```

### Сброс БД
```bash
# Удалить БД
docker-compose run --rm ais python scripts/reset_db.py

# Создать заново
docker-compose run --rm ais python scripts/init_demo_data.py
```

### Быстрый сброс (одна команда)
```bash
docker-compose run --rm ais python -c "import os; f='streamlit_app/ais.db'; os.remove(f) if os.path.exists(f) else None; print('БД удалена')" && docker-compose run --rm ais python -c "print('y')" | docker-compose run --rm -T ais python scripts/init_demo_data.py
```

---

## 🎯 DOCKER COMPOSE КОНФИГУРАЦИЯ

Ваш `docker-compose.yaml`:

```yaml
services:
  ais:
    build: .
    ports:
      - "8501:8501"  # Streamlit интерфейс
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - .:/app  # Код и БД доступны из контейнера
    command: streamlit run streamlit_app/ais_app.py --server.port 8501 --server.address 0.0.0.0

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

**Что это значит:**
- ✅ Streamlit доступен на `http://localhost:8501`
- ✅ БД SQLite сохраняется локально (volume `.:/app`)
- ✅ Redis для метрик и кэша
- ✅ Автоматическая пересборка при изменениях

---

## 📊 ДЕМОНСТРАЦИЯ ЧЕРЕЗ DOCKER

### Сценарий (5 минут)

#### 1. Запуск системы
```bash
# Терминал 1: Запуск
docker-compose up
```

Ждём сообщение:
```
ais_1  | You can now view your Streamlit app in your browser.
ais_1  | Network URL: http://0.0.0.0:8501
ais_1  | External URL: http://localhost:8501
```

#### 2. Открыть браузер
```
http://localhost:8501
```

#### 3. Нагрузочное тестирование
- Раздел: **"🧪 Нагрузочное тестирование"**
- Заявок: **1000**
- Батч: **50**
- Задержка: **50 мс**
- Нажать: **"🚀 Запустить"**

#### 4. Анализ результатов
- Раздел: **"⚖️ Распределение"**
- Проверить: **MAE < 0.05** ✅
- Посмотреть: **График утилизации**
- Изучить: **Таблицу распределения**

---

## 🛠️ ПОЛЕЗНЫЕ КОМАНДЫ

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Только ais
docker-compose logs -f ais

# Последние 100 строк
docker-compose logs --tail=100 -f ais
```

### Выполнение команд в контейнере
```bash
# Открыть shell
docker-compose exec ais bash

# Запустить Python скрипт
docker-compose exec ais python scripts/init_demo_data.py

# Проверить наличие БД
docker-compose exec ais ls -lh streamlit_app/ais.db
```

### Пересборка
```bash
# Полная пересборка (если изменились зависимости)
docker-compose build --no-cache

# Пересборка и запуск
docker-compose up --build
```

### Очистка
```bash
# Остановить и удалить контейнеры
docker-compose down

# + удалить volumes
docker-compose down -v

# + удалить образы
docker-compose down -v --rmi all

# Очистка Docker (осторожно!)
docker system prune -a
```

---

## 🐛 TROUBLESHOOTING

### Проблема: Порт 8501 занят
```bash
# Найти процесс
netstat -ano | findstr :8501

# Или изменить порт в docker-compose.yaml:
ports:
  - "8502:8501"  # Доступ через http://localhost:8502
```

### Проблема: Контейнер не запускается
```bash
# Посмотреть логи
docker-compose logs ais

# Проверить статус
docker-compose ps

# Пересобрать
docker-compose build --no-cache
docker-compose up
```

### Проблема: БД не создаётся
```bash
# Создать вручную в контейнере
docker-compose run --rm ais python scripts/init_demo_data.py

# Или через exec (если контейнер запущен)
docker-compose exec ais python scripts/init_demo_data.py
```

### Проблема: Изменения не применяются
```bash
# Пересобрать образ
docker-compose build

# Перезапустить
docker-compose restart

# Или полная пересборка
docker-compose down
docker-compose up --build
```

### Проблема: "No such file or directory: ais.db"
```bash
# Инициализировать БД
docker-compose run --rm ais python scripts/init_demo_data.py
```

---

## 📦 СТРУКТУРА VOLUMES

```
Локальная файловая система:
├── streamlit_app/
│   └── ais.db          ← БД сохраняется здесь
├── scripts/
│   └── init_demo_data.py
└── ...

↕️ Монтируется в контейнер как:
/app/streamlit_app/ais.db
/app/scripts/init_demo_data.py
```

**Это значит:**
- ✅ БД сохраняется локально даже после остановки контейнера
- ✅ Изменения в коде применяются автоматически (hot reload)
- ✅ Данные не теряются при `docker-compose down`

---

## 🎯 РЕКОМЕНДАЦИИ

### Для разработки
```bash
# Запуск с логами
docker-compose up

# Изменения в коде применяются автоматически
# Streamlit перезагрузится сам
```

### Для демонстрации
```bash
# Запуск в фоне
docker-compose up -d

# Открыть браузер
start http://localhost:8501

# Остановка после демо
docker-compose stop
```

### Для продакшена
```bash
# Отключить hot reload
# В docker-compose.yaml убрать volumes: - .:/app

# Или создать отдельный docker-compose.prod.yaml
```

---

## 🚀 СКРИПТЫ ДЛЯ БЫСТРОГО ЗАПУСКА

### Windows (PowerShell)

**start.ps1:**
```powershell
# Остановить старые контейнеры
docker-compose down

# Инициализация (первый раз)
docker-compose run --rm ais python scripts/init_demo_data.py

# Запуск
docker-compose up
```

### Linux/Mac (bash)

**start.sh:**
```bash
#!/bin/bash
# Остановить старые контейнеры
docker-compose down

# Инициализация (первый раз)
docker-compose run --rm ais python scripts/init_demo_data.py

# Запуск
docker-compose up
```

---

## 📋 CHECKLIST ДЛЯ ДЕМОНСТРАЦИИ

### Перед демонстрацией:
- [ ] Docker Desktop запущен
- [ ] Старые контейнеры остановлены: `docker-compose down`
- [ ] БД инициализирована: `docker-compose run --rm ais python scripts/init_demo_data.py`
- [ ] Система запущена: `docker-compose up -d`
- [ ] Браузер открыт: `http://localhost:8501`
- [ ] Дашборд загрузился и показывает 10 исполнителей

### Во время демонстрации:
- [ ] Показать метрики (пустые)
- [ ] Запустить нагрузочный тест (1000 заявок)
- [ ] Показать результаты (MAE < 0.05)
- [ ] Показать графики и таблицы

### После демонстрации:
- [ ] Остановить: `docker-compose stop`
- [ ] Или очистить данные: `docker-compose down -v`

---

## 🎉 ВСЁ ГОТОВО!

Система полностью настроена для работы через Docker:

✅ **Все зависимости в requirements.txt**
✅ **Docker Compose настроен**
✅ **Streamlit на порту 8501**
✅ **БД сохраняется локально**
✅ **Hot reload работает**

### Запуск одной командой:
```bash
docker-compose up
```

### Или с инициализацией:
```bash
docker-compose run --rm ais python -c "print('y')" | docker-compose run --rm -T ais python scripts/init_demo_data.py && docker-compose up
```

**Демонстрируйте через Docker! 🐳🚀**

