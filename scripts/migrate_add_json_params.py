"""
Миграция: Добавление JSON колонок для динамических параметров
Версия: 1.0
Дата: 2025-10-28

Добавляет колонку 'params' (TEXT с JSON) в таблицы tasks и executors
для поддержки динамических параметров без изменения схемы БД.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = 'streamlit_app/ais.db'

def backup_database():
    """Создать резервную копию БД перед миграцией"""
    if os.path.exists(DB_PATH):
        backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"[OK] Создана резервная копия: {backup_path}")
        return backup_path
    return None

def add_params_column_to_tasks(conn):
    """Добавить колонку params в таблицу tasks"""
    try:
        cursor = conn.cursor()
        
        # Проверяем есть ли уже колонка
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'params' in columns:
            print("[INFO] Колонка 'params' уже существует в таблице tasks")
            return False
        
        # Добавляем колонку
        cursor.execute("ALTER TABLE tasks ADD COLUMN params TEXT")
        
        # Инициализируем пустым JSON для существующих записей
        cursor.execute("""
            UPDATE tasks 
            SET params = '{}' 
            WHERE params IS NULL
        """)
        
        print("[OK] Добавлена колонка 'params' в таблицу tasks")
        return True
        
    except sqlite3.OperationalError as e:
        print(f"[ERROR] Ошибка при добавлении колонки в tasks: {e}")
        return False

def add_params_column_to_executors(conn):
    """Добавить колонку params в таблицу executors"""
    try:
        cursor = conn.cursor()
        
        # Проверяем есть ли уже колонка
        cursor.execute("PRAGMA table_info(executors)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'params' in columns:
            print("[INFO] Колонка 'params' уже существует в таблице executors")
            return False
        
        # Добавляем колонку
        cursor.execute("ALTER TABLE executors ADD COLUMN params TEXT")
        
        # Инициализируем пустым JSON для существующих записей
        cursor.execute("""
            UPDATE executors 
            SET params = '{}' 
            WHERE params IS NULL
        """)
        
        print("[OK] Добавлена колонка 'params' в таблицу executors")
        return True
        
    except sqlite3.OperationalError as e:
        print(f"[ERROR] Ошибка при добавлении колонки в executors: {e}")
        return False

def migrate_existing_data(conn):
    """Мигрировать существующие данные в JSON формат"""
    cursor = conn.cursor()
    
    # Мигрировать skills из executors в params
    cursor.execute("SELECT id, skills FROM executors WHERE skills IS NOT NULL")
    executors = cursor.fetchall()
    
    migrated_count = 0
    for exec_id, skills_str in executors:
        if skills_str:
            try:
                # Парсим существующие навыки
                skills_list = [s.strip() for s in skills_str.split(',') if s.strip()]
                
                # Получаем текущий params
                cursor.execute("SELECT params FROM executors WHERE id = ?", (exec_id,))
                current_params = cursor.fetchone()[0]
                params = json.loads(current_params) if current_params else {}
                
                # Добавляем skills в params
                params['skills'] = skills_list
                
                # Сохраняем
                cursor.execute(
                    "UPDATE executors SET params = ? WHERE id = ?",
                    (json.dumps(params, ensure_ascii=False), exec_id)
                )
                migrated_count += 1
            except Exception as e:
                print(f"[WARN] Не удалось мигрировать навыки для исполнителя {exec_id}: {e}")
    
    if migrated_count > 0:
        print(f"[OK] Мигрировано навыков у {migrated_count} исполнителей")
    
    return migrated_count

def add_sample_params(conn):
    """Добавить примеры параметров для демонстрации"""
    cursor = conn.cursor()
    
    # Добавить примерные параметры к исполнителям
    sample_executor_params = [
        {
            'filter': "department = 'IT'",
            'params': json.dumps({
                'experience_years': 5,
                'remote_available': True,
                'hourly_rate': 3000,
                'max_complexity': 8,
                'certifications': ['Python', 'React'],
                'availability': 'full-time'
            }, ensure_ascii=False)
        },
        {
            'filter': "department = 'Строительство'",
            'params': json.dumps({
                'experience_years': 10,
                'location': 'Москва',
                'equipment_available': ['Кран', 'Экскаватор'],
                'max_project_size': 5000,
                'has_license': True
            }, ensure_ascii=False)
        },
        {
            'filter': "department = 'Страхование'",
            'params': json.dumps({
                'experience_years': 3,
                'insurance_types': ['ОСАГО', 'КАСКО'],
                'specialization': 'Автострахование',
                'avg_processing_time': 15
            }, ensure_ascii=False)
        }
    ]
    
    added_count = 0
    for sample in sample_executor_params:
        # SQLite не поддерживает LIMIT в UPDATE, используем подзапрос
        cursor.execute(f"""
            SELECT id FROM executors 
            WHERE {sample['filter']} 
            AND (params IS NULL OR params = '{{}}')
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row:
            cursor.execute("""
                UPDATE executors 
                SET params = ? 
                WHERE id = ?
            """, (sample['params'], row[0]))
            added_count += 1
    
    if added_count > 0:
        print(f"[OK] Добавлены примерные параметры к {added_count} исполнителям")
    
    return added_count

def create_migration_log(conn):
    """Создать таблицу для логирования миграций"""
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name TEXT NOT NULL,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            success INTEGER DEFAULT 1,
            notes TEXT
        )
    """)
    
    cursor.execute("""
        INSERT INTO schema_migrations (migration_name, notes)
        VALUES (?, ?)
    """, (
        'add_json_params_v1',
        'Добавлены JSON колонки params в tasks и executors'
    ))
    
    print("[OK] Создана таблица миграций")

def main():
    print("=" * 60)
    print("МИГРАЦИЯ БД: Добавление JSON параметров")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] База данных не найдена: {DB_PATH}")
        print("Запустите сначала docker_init.bat для создания БД")
        return
    
    # Создать резервную копию
    backup_path = backup_database()
    
    try:
        # Подключиться к БД
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        print("\n[1/6] Добавление колонки params в tasks...")
        tasks_added = add_params_column_to_tasks(conn)
        
        print("\n[2/6] Добавление колонки params в executors...")
        executors_added = add_params_column_to_executors(conn)
        
        print("\n[3/6] Миграция существующих данных...")
        migrated = migrate_existing_data(conn)
        
        print("\n[4/6] Добавление примерных параметров...")
        samples_added = add_sample_params(conn)
        
        print("\n[5/6] Создание таблицы миграций...")
        create_migration_log(conn)
        
        print("\n[6/6] Сохранение изменений...")
        conn.commit()
        
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"[OK] Columns added: {int(tasks_added) + int(executors_added)}")
        print(f"[OK] Records migrated: {migrated}")
        print(f"[OK] Samples added: {samples_added}")
        
        if backup_path:
            print(f"\n[BACKUP] Created: {backup_path}")
        
        print("\n[DB] Database structure updated:")
        print("   - tasks.params (TEXT/JSON)")
        print("   - executors.params (TEXT/JSON)")
        print("\n[SUCCESS] System now supports dynamic parameters!")
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка при миграции: {e}")
        conn.rollback()
        
        if backup_path:
            print(f"\n💾 Восстановите из резервной копии: {backup_path}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()

