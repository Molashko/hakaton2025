# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы приложения
COPY . .

# Создаем директорию для БД если её нет
RUN mkdir -p streamlit_app

# Открываем порт для Streamlit
EXPOSE 8501

# Команда запуска (будет переопределена в docker-compose.yaml)
CMD ["streamlit", "run", "streamlit_app/ais_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]

