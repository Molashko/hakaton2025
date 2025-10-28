import argparse
import json
import os
import random
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
import time


TASK_PARAMS = {
    'Приоритет': ['Низкий', 'Средний', 'Высокий', 'Критический'],
    'Категория': ['IT', 'Строительство', 'Страхование', 'Консалтинг'],
    'Сложность': ['Простая', 'Средняя', 'Сложная', 'Экспертная'],
}

EXECUTOR_PARAMS = {
    'Отдел': ['IT', 'Строительство', 'Страхование', 'Консалтинг'],
    'Опыт работы': ['До 1 года', '1-3 года', '3-5 лет', '5-10 лет', 'Более 10 лет'],
    'Навыки': ['Python', 'JavaScript', 'Строительство', 'Проектирование', 'Анализ рисков', 'Продажи'],
}


def detect_db_path() -> Path:
    # 1) env override
    env_path = os.environ.get('SQLITE_PATH')
    if env_path:
        return Path(env_path)
    # 2) typical project path
    p = Path(__file__).resolve().parents[1] / 'streamlit_app' / 'ais.db'
    return p


def get_conn(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Новая',
            created_at TEXT,
            data TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS executors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            status TEXT DEFAULT 'Активен',
            active INTEGER DEFAULT 1,
            created_at TEXT,
            data TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS assignments (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            executor_id TEXT,
            assigned_at TEXT,
            status TEXT DEFAULT 'Назначена',
            score REAL
        )
        """
    )
    conn.commit()


def insert_task(cur: sqlite3.Cursor, t: dict):
    data = {k: v for k, v in t.items() if k not in ['id', 'name', 'description', 'status', 'created_at']}
    cur.execute(
        """
        INSERT INTO tasks(id,name,description,status,created_at,data)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
          name=excluded.name,
          description=excluded.description,
          status=excluded.status,
          created_at=excluded.created_at,
          data=excluded.data
        """,
        (
            t['id'],
            t['name'],
            t.get('description', ''),
            t.get('status', 'Новая'),
            t['created_at'],
            json.dumps(data, ensure_ascii=False),
        ),
    )


def insert_executor(cur: sqlite3.Cursor, e: dict):
    data = {
        k: v
        for k, v in e.items()
        if k not in ['id', 'name', 'email', 'phone', 'status', 'active', 'created_at']
    }
    cur.execute(
        """
        INSERT INTO executors(id,name,email,phone,status,active,created_at,data)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
          name=excluded.name,
          email=excluded.email,
          phone=excluded.phone,
          status=excluded.status,
          active=excluded.active,
          created_at=excluded.created_at,
          data=excluded.data
        """,
        (
            e['id'],
            e['name'],
            e['email'],
            e.get('phone', ''),
            e.get('status', 'Активен'),
            1 if e.get('active', True) else 0,
            e['created_at'],
            json.dumps(data, ensure_ascii=False),
        ),
    )


def generate_tasks(n: int) -> list[dict]:
    tasks = []
    for i in range(n):
        cat = random.choice(TASK_PARAMS['Категория'])
        t = {
            'id': str(uuid.uuid4()),
            'name': f'Заявка #{i+1}',
            'description': f'Автогенерация описания для заявки #{i+1}',
            'status': random.choice(['Новая', 'Назначена', 'В работе', 'Завершена']),
            'created_at': datetime.now().isoformat(),
            'Приоритет': random.choice(TASK_PARAMS['Приоритет']),
            'Категория': cat,
            'Сложность': random.choice(TASK_PARAMS['Сложность']),
            'Бюджет': random.choice([50000, 100000, 250000, 500000]),
            'Срок выполнения': datetime.now().date().isoformat(),
        }
        tasks.append(t)
    return tasks


def generate_executors(n: int) -> list[dict]:
    executors = []
    for i in range(n):
        dep = random.choice(EXECUTOR_PARAMS['Отдел'])
        skills = random.sample(EXECUTOR_PARAMS['Навыки'], k=random.randint(1, 3))
        e = {
            'id': str(uuid.uuid4()),
            'name': f'Исполнитель {i+1}',
            'email': f'user{i+1}@example.com',
            'phone': f'+7 (900) {random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}',
            'status': 'Активен',
            'active': True,
            'created_at': datetime.now().isoformat(),
            'Отдел': dep,
            'Опыт работы': random.choice(EXECUTOR_PARAMS['Опыт работы']),
            'Рейтинг': random.randint(1, 5),
            'Навыки': skills,
            'Максимум заявок в день': random.choice([5, 10, 15, 20]),
        }
        executors.append(e)
    return executors


def main():
    parser = argparse.ArgumentParser(description='Наполнить SQLite тестовыми заявками и исполнителями')
    parser.add_argument('--tasks', type=int, default=100, help='Количество заявок')
    parser.add_argument('--executors', type=int, default=50, help='Количество исполнителей')
    parser.add_argument('--sleep-ms', type=int, default=0, help='Пауза между вставками (миллисекунды)')
    args = parser.parse_args()

    db_path = detect_db_path()
    conn = get_conn(db_path)
    init_schema(conn)
    cur = conn.cursor()

    gen_tasks = generate_tasks(args.tasks)
    gen_execs = generate_executors(args.executors)

    # Постепенная вставка с паузой и коммитом
    delay = max(0, args.sleep_ms) / 1000.0
    for i, t in enumerate(gen_tasks, 1):
        insert_task(cur, t)
        conn.commit()
        if delay:
            time.sleep(delay)
        if i % 10 == 0:
            print(f"Добавлено заявок: {i}/{len(gen_tasks)}", flush=True)

    for j, e in enumerate(gen_execs, 1):
        insert_executor(cur, e)
        conn.commit()
        if delay:
            time.sleep(delay)
        if j % 10 == 0:
            print(f"Добавлено исполнителей: {j}/{len(gen_execs)}", flush=True)

    conn.close()
    print(f'OK: добавлено заявок: {len(gen_tasks)}, исполнителей: {len(gen_execs)} в {db_path}')


if __name__ == '__main__':
    sys.exit(main())


