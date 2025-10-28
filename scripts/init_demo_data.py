"""
Скрипт инициализации демо-данных для АИС
Создает исполнителей и опционально заявки для демонстрации
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
import uuid
from datetime import datetime
import json

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'streamlit_app', 'ais.db')

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Создание таблиц
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT,
        priority TEXT,
        created_at TEXT,
        data TEXT
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS executors (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        department TEXT,
        skills TEXT,
        active INTEGER DEFAULT 1,
        daily_limit INTEGER DEFAULT 10,
        assigned_today INTEGER DEFAULT 0,
        created_at TEXT,
        data TEXT
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id TEXT PRIMARY KEY,
        task_id TEXT,
        executor_id TEXT,
        assigned_at TEXT,
        score REAL
    )
    """)
    
    conn.commit()
    conn.close()
    print("[OK] База данных инициализирована")

def clear_all_data():
    """Очистка всех данных"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("DELETE FROM assignments")
    cur.execute("DELETE FROM tasks")
    cur.execute("DELETE FROM executors")
    
    conn.commit()
    conn.close()
    print("[OK] Все данные очищены")

def create_demo_executors():
    """Создание демо-исполнителей"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    executors = [
        {
            'name': 'Иванов Иван',
            'email': 'ivanov@company.ru',
            'department': 'IT',
            'skills': 'Python,JavaScript',
            'daily_limit': 15
        },
        {
            'name': 'Петрова Мария',
            'email': 'petrova@company.ru',
            'department': 'IT',
            'skills': 'Python',
            'daily_limit': 12
        },
        {
            'name': 'Сидоров Петр',
            'email': 'sidorov@company.ru',
            'department': 'Строительство',
            'skills': 'Строительство,Проектирование',
            'daily_limit': 10
        },
        {
            'name': 'Козлова Анна',
            'email': 'kozlova@company.ru',
            'department': 'Страхование',
            'skills': 'Анализ рисков',
            'daily_limit': 20
        },
        {
            'name': 'Смирнов Алексей',
            'email': 'smirnov@company.ru',
            'department': 'Консалтинг',
            'skills': 'Продажи',
            'daily_limit': 18
        },
        {
            'name': 'Новикова Елена',
            'email': 'novikova@company.ru',
            'department': 'IT',
            'skills': 'JavaScript',
            'daily_limit': 14
        },
        {
            'name': 'Морозов Дмитрий',
            'email': 'morozov@company.ru',
            'department': 'Строительство',
            'skills': 'Строительство',
            'daily_limit': 16
        },
        {
            'name': 'Волкова Ольга',
            'email': 'volkova@company.ru',
            'department': 'Страхование',
            'skills': 'Анализ рисков,Продажи',
            'daily_limit': 15
        },
        {
            'name': 'Лебедев Сергей',
            'email': 'lebedev@company.ru',
            'department': 'IT',
            'skills': 'Python,JavaScript',
            'daily_limit': 20
        },
        {
            'name': 'Соколова Наталья',
            'email': 'sokolova@company.ru',
            'department': 'Консалтинг',
            'skills': 'Продажи',
            'daily_limit': 12
        }
    ]
    
    count = 0
    for exec_data in executors:
        executor_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO executors(id, name, email, department, skills, active, daily_limit, assigned_today, created_at, data)
            VALUES(?, ?, ?, ?, ?, 1, ?, 0, ?, '{}')
        """, (
            executor_id,
            exec_data['name'],
            exec_data['email'],
            exec_data['department'],
            exec_data['skills'],
            exec_data['daily_limit'],
            datetime.now().isoformat()
        ))
        count += 1
    
    conn.commit()
    conn.close()
    print(f"[OK] Создано {count} исполнителей")

def main():
    print("=" * 60)
    print("Инициализация демо-данных для АИС")
    print("=" * 60)
    
    # Проверка существования БД
    db_exists = os.path.exists(DB_PATH)
    
    if db_exists:
        response = input("\n[!] БД уже существует. Пересоздать с нуля? (y/n): ")
        if response.lower() == 'y':
            os.remove(DB_PATH)
            print("[OK] Старая БД удалена")
            init_db()
        else:
            print("[INFO] Используем существующую БД")
            # Очистка только данных
            response2 = input("\n[!] Очистить только данные (оставить структуру)? (y/n): ")
            if response2.lower() == 'y':
                clear_all_data()
    else:
        # Инициализация новой БД
        init_db()
    
    # Создание исполнителей
    print("\n[INFO] Создание демо-исполнителей...")
    create_demo_executors()
    
    print("\n" + "=" * 60)
    print("[OK] Инициализация завершена!")
    print("=" * 60)
    print("\n[INFO] Теперь запустите Streamlit приложение:")
    print("   cd streamlit_app")
    print("   streamlit run ais_app.py")
    print("\n[INFO] Для нагрузочного тестирования перейдите в раздел")
    print("   'Нагрузочное тестирование' в интерфейсе")

if __name__ == "__main__":
    main()

