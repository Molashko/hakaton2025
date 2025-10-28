import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import uuid
import os
import sqlite3

# Конфигурация страницы
st.set_page_config(
    page_title="АИС - Система распределения заявок",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS стили
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    .card {
        background-color: transparent;
        padding: 0;
        border: none;
        margin: 0;
        box-shadow: none;
    }
    .parameter-row {
        display: flex;
        align-items: center;
        margin: 0.5rem 0;
        padding: 0.5rem;
        background-color: #f8f9fa;
        border-radius: 0.25rem;
    }
    .add-button {
        background-color: #28a745;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        cursor: pointer;
        margin: 0.5rem 0;
    }
    .delete-button {
        background-color: #dc3545;
        color: white;
        border: none;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        cursor: pointer;
        margin-left: 0.5rem;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3498db;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Хранилище: SQLite
DB_PATH = os.environ.get('SQLITE_PATH', os.path.join(os.path.dirname(__file__), 'ais.db'))

def get_sqlite_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite():
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'Новая',
        created_at TEXT,
        data TEXT
    )
    """)
    cur.execute("""
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
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id TEXT PRIMARY KEY,
        task_id TEXT,
        executor_id TEXT,
        assigned_at TEXT,
        status TEXT DEFAULT 'Назначена',
        score REAL
    )
    """)
    conn.commit()
    conn.close()

def _json_dumps(obj):
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return '{}'

def _json_loads(s):
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}

def load_tasks_from_db():
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,name,description,status,created_at,data FROM tasks ORDER BY datetime(created_at) DESC")
    rows = cur.fetchall()
    conn.close()
    tasks = []
    for r in rows:
        t = {
            'id': r['id'],
            'name': r['name'],
            'description': r['description'],
            'status': r['status'],
            'created_at': r['created_at'] or datetime.now().isoformat()
        }
        t.update(_json_loads(r['data']))
        tasks.append(t)
    return tasks

def load_executors_from_db():
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,name,email,phone,status,active,created_at,data FROM executors ORDER BY datetime(created_at) DESC")
    rows = cur.fetchall()
    conn.close()
    executors = []
    for r in rows:
        e = {
            'id': r['id'],
            'name': r['name'],
            'email': r['email'],
            'phone': r['phone'],
            'status': r['status'],
            'active': bool(r['active']),
            'created_at': r['created_at'] or datetime.now().isoformat()
        }
        e.update(_json_loads(r['data']))
        executors.append(e)
    return executors

def load_assignments_from_db():
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,task_id,executor_id,assigned_at,status,score FROM assignments ORDER BY datetime(assigned_at) DESC")
    rows = cur.fetchall()
    conn.close()
    return [{
        'id': r['id'],
        'task_id': r['task_id'],
        'executor_id': r['executor_id'],
        'assigned_at': r['assigned_at'] or datetime.now().isoformat(),
        'status': r['status'],
        'score': r['score'] if r['score'] is not None else 0.0
    } for r in rows]

def save_task_to_db(task):
    conn = get_sqlite_conn()
    cur = conn.cursor()
    base_keys = ['id','name','description','status','created_at']
    data = {k: v for k, v in task.items() if k not in base_keys}
    cur.execute("""
        INSERT INTO tasks(id,name,description,status,created_at,data)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            description=excluded.description,
            status=excluded.status,
            created_at=excluded.created_at,
            data=excluded.data
    """, (
        task['id'], task['name'], task.get('description',''), task.get('status','Новая'), task['created_at'], _json_dumps(data)
    ))
    conn.commit()
    conn.close()
    return True

def save_executor_to_db(executor):
    conn = get_sqlite_conn()
    cur = conn.cursor()
    base_keys = ['id','name','email','phone','status','active','created_at']
    data = {k: v for k, v in executor.items() if k not in base_keys}
    cur.execute("""
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
    """, (
        executor['id'], executor['name'], executor['email'], executor.get('phone',''), executor.get('status','Активен'), 1 if executor.get('active', True) else 0, executor['created_at'], _json_dumps(data)
    ))
    conn.commit()
    conn.close()
    return True

def save_assignment_to_db(assignment):
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO assignments(id,task_id,executor_id,assigned_at,status,score)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            task_id=excluded.task_id,
            executor_id=excluded.executor_id,
            assigned_at=excluded.assigned_at,
            status=excluded.status,
            score=excluded.score
    """, (
        assignment['id'], assignment['task_id'], assignment['executor_id'], assignment['assigned_at'], assignment.get('status','Назначена'), assignment.get('score', 0.0)
    ))
    conn.commit()
    conn.close()
    return True

def delete_task_from_db(task_id):
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM assignments WHERE task_id=?", (task_id,))
    cur.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return True

def delete_executor_from_db(executor_id):
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM assignments WHERE executor_id=?", (executor_id,))
    cur.execute("DELETE FROM executors WHERE id=?", (executor_id,))
    conn.commit()
    conn.close()
    return True

def clear_tasks_in_db():
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM assignments")
    cur.execute("DELETE FROM tasks")
    conn.commit()
    conn.close()
    return True

def clear_executors_in_db():
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM assignments")
    cur.execute("DELETE FROM executors")
    conn.commit()
    conn.close()
    return True

def clear_all_data_in_db():
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM assignments")
    cur.execute("DELETE FROM tasks")
    cur.execute("DELETE FROM executors")
    conn.commit()
    conn.close()
    return True

# Инициализация состояния сессии
def init_session_state():
    if 'db_initialized' not in st.session_state:
        init_sqlite()
        st.session_state.db_initialized = True
    if 'tasks' not in st.session_state:
        st.session_state.tasks = load_tasks_from_db()
    if 'executors' not in st.session_state:
        st.session_state.executors = load_executors_from_db()
    if 'assignments' not in st.session_state:
        st.session_state.assignments = load_assignments_from_db()
    if 'task_parameters' not in st.session_state:
        st.session_state.task_parameters = [
            {'name': 'Приоритет', 'type': 'Выбор из списка', 'options': ['Низкий', 'Средний', 'Высокий', 'Критический'], 'weight': 2.0},
            {'name': 'Категория', 'type': 'Выбор из списка', 'options': ['IT', 'Строительство', 'Страхование', 'Консалтинг'], 'weight': 1.5},
            {'name': 'Сложность', 'type': 'Выбор из списка', 'options': ['Простая', 'Средняя', 'Сложная', 'Экспертная'], 'weight': 1.8},
            {'name': 'Бюджет', 'type': 'Число', 'options': [], 'weight': 1.0},
            {'name': 'Срок выполнения', 'type': 'Дата', 'options': [], 'weight': 1.2}
        ]
    if 'executor_parameters' not in st.session_state:
        st.session_state.executor_parameters = [
            {'name': 'Навыки', 'type': 'Множественный выбор', 'options': ['Python', 'JavaScript', 'Строительство', 'Проектирование', 'Анализ рисков', 'Продажи'], 'weight': 2.0},
            {'name': 'Опыт работы', 'type': 'Выбор из списка', 'options': ['До 1 года', '1-3 года', '3-5 лет', '5-10 лет', 'Более 10 лет'], 'weight': 1.8},
            {'name': 'Рейтинг', 'type': 'Слайдер', 'options': [1, 5], 'weight': 1.5},
            {'name': 'Отдел', 'type': 'Выбор из списка', 'options': ['IT', 'Строительство', 'Страхование', 'Консалтинг'], 'weight': 1.3},
            {'name': 'Максимум заявок в день', 'type': 'Число', 'options': [], 'weight': 1.0}
        ]

# Заголовок приложения
def render_header():
    st.markdown('<h1 class="main-header">🏢 АИС - Система распределения заявок</h1>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #7f8c8d; margin-bottom: 2rem;">
        Простая и понятная система для распределения заявок между исполнителями<br>
        Никакого программирования - только удобные формы и кнопки
    </div>
    """, unsafe_allow_html=True)

# Главное меню
def render_main_menu():
    st.sidebar.markdown("## 📋 Главное меню")
    
    # Инициализация текущей страницы
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "dashboard"
    
    # Кнопки для каждого раздела
    current_page = st.session_state.current_page
    
    if st.sidebar.button("📊 Общая статистика", use_container_width=True, type="primary" if current_page == "dashboard" else "secondary"):
        st.session_state.current_page = "dashboard"
        st.rerun()
    
    if st.sidebar.button("📝 Заявки", use_container_width=True, type="primary" if current_page == "tasks" else "secondary"):
        st.session_state.current_page = "tasks"
        st.rerun()
    
    if st.sidebar.button("👥 Исполнители", use_container_width=True, type="primary" if current_page == "executors" else "secondary"):
        st.session_state.current_page = "executors"
        st.rerun()
    
    if st.sidebar.button("⚙️ Настройки параметров", use_container_width=True, type="primary" if current_page == "parameters" else "secondary"):
        st.session_state.current_page = "parameters"
        st.rerun()
    
    if st.sidebar.button("📈 Отчеты", use_container_width=True, type="primary" if current_page == "reports" else "secondary"):
        st.session_state.current_page = "reports"
        st.rerun()
    
    if st.sidebar.button("🔧 Управление системой", use_container_width=True, type="primary" if current_page == "settings" else "secondary"):
        st.session_state.current_page = "settings"
        st.rerun()
    
    # Показываем текущую страницу
    return st.session_state.current_page

# Общая статистика
def _aggregate_per_minute(items, timestamp_key, window_minutes=5):
    now = datetime.now()
    start = now - timedelta(minutes=window_minutes)
    buckets = {}
    for i in range(window_minutes + 1):
        t = (start + timedelta(minutes=i)).replace(second=0, microsecond=0)
        buckets[t] = 0
    for it in items:
        try:
            ts = datetime.fromisoformat(it.get(timestamp_key, now.isoformat()))
            ts0 = ts.replace(second=0, microsecond=0)
            if ts0 >= start:
                buckets[ts0] = buckets.get(ts0, 0) + 1
        except Exception:
            pass
    times = sorted(buckets.keys())
    return pd.DataFrame({
        'Минута': [t.strftime('%H:%M') for t in times],
        'Количество': [buckets[t] for t in times],
    })


def render_dashboard():
    st.markdown('<h2 class="section-header">📊 Общая статистика</h2>', unsafe_allow_html=True)

    # Автообновление: при включённой настройке перечитываем данные и запускаем авто-рефреш
    auto_refresh_enabled = st.session_state.get('auto_refresh', True)
    if auto_refresh_enabled:
        # Перечитываем актуальные данные из SQLite перед отрисовкой метрик
        st.session_state.tasks = load_tasks_from_db()
        st.session_state.executors = load_executors_from_db()
        st.session_state.assignments = load_assignments_from_db()
        # Мягкий автообновитель: пробуем библиотеку, иначе fallback
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=2000, limit=None, key="ais_realtime")
        except Exception:
            st.markdown('<meta http-equiv="refresh" content="2">', unsafe_allow_html=True)
    
    # Ключевые метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📝 Всего заявок",
            value=len(st.session_state.tasks),
            delta=f"+{len([t for t in st.session_state.tasks if t.get('status') == 'Новая'])} новых"
        )
    
    with col2:
        st.metric(
            label="👥 Исполнителей",
            value=len([e for e in st.session_state.executors if e.get('active', True)]),
            delta=f"{len([e for e in st.session_state.executors if e.get('active', True)])} активных"
        )
    
    with col3:
        assigned_tasks = len([t for t in st.session_state.tasks if t.get('status') == 'Назначена'])
        st.metric(
            label="✅ Назначенных заявок",
            value=assigned_tasks,
            delta=f"{assigned_tasks/len(st.session_state.tasks)*100:.1f}%" if st.session_state.tasks else "0%"
        )
    
    with col4:
        active_executors = len([e for e in st.session_state.executors if e.get('active', True)])
        tasks_per_executor = len(st.session_state.tasks) / active_executors if active_executors > 0 else 0
        st.metric(
            label="📊 Заявок на исполнителя",
            value=f"{tasks_per_executor:.1f}",
            delta=f"{tasks_per_executor:.1f}"
        )
    
    # Графики (новое применение, без статусов)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🗂 Категории заявок (все данные)")
        category_counts = {}
        for t in st.session_state.tasks:
            c = t.get('Категория', 'Не указана')
            category_counts[c] = category_counts.get(c, 0) + 1
        if category_counts:
            df_cat_all = pd.DataFrame({'Категория': list(category_counts.keys()), 'Количество': list(category_counts.values())})
            fig1 = px.pie(df_cat_all, values='Количество', names='Категория', hole=0.35, color_discrete_sequence=px.colors.qualitative.Set3)
            fig1.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.markdown("### ⚡ Назначения (последние 5 минут)")
        df_assign_min = _aggregate_per_minute(st.session_state.assignments, 'assigned_at', window_minutes=5)
        fig2 = px.line(df_assign_min, x='Минута', y='Количество', markers=True, color_discrete_sequence=['#2ca02c'])
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("### 🏆 Топ исполнителей по активным назначениям")
        active_counts = []
        for e in st.session_state.executors:
            count = len([a for a in st.session_state.assignments if a.get('executor_id') == e['id']])
            active_counts.append({'Исполнитель': e['name'], 'Назначений': count})
        if active_counts:
            df_top = pd.DataFrame(active_counts).sort_values('Назначений', ascending=False).head(10)
            fig3 = px.bar(df_top, x='Исполнитель', y='Назначений', color='Назначений', color_continuous_scale='Blues')
            fig3.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.markdown("### ⏱ Поступление заявок (последние 5 минут)")
        df_tasks_min = _aggregate_per_minute(st.session_state.tasks, 'created_at', window_minutes=5)
        fig4 = px.line(df_tasks_min, x='Минута', y='Количество', markers=True)
        st.plotly_chart(fig4, use_container_width=True)

# Управление заявками
def render_tasks_management():
    st.markdown('<h2 class="section-header">📝 Управление заявками</h2>', unsafe_allow_html=True)
    
    # Проверка на редактирование заявки
    editing_task_id = None
    for task in st.session_state.tasks:
        if st.session_state.get(f"editing_task_{task['id']}", False):
            editing_task_id = task['id']
            break
    
    if editing_task_id:
        # Редактирование существующей заявки
        task_to_edit = next(t for t in st.session_state.tasks if t['id'] == editing_task_id)
        st.markdown("### ✏️ Редактировать заявку")
        
        col1, col2 = st.columns(2)
        
        with col1:
            task_name = st.text_input("Название заявки", value=task_to_edit['name'], key="edit_task_name")
            task_description = st.text_area("Описание", value=task_to_edit['description'], key="edit_task_description")
        
        with col2:
            # Динамические параметры заявки для редактирования
            task_data = {}
            for param in st.session_state.task_parameters:
                current_value = task_to_edit.get(param['name'], '')
                if param['type'] == 'Выбор из списка':
                    # Находим индекс текущего значения
                    try:
                        index = param['options'].index(current_value)
                    except ValueError:
                        index = 0
                    task_data[param['name']] = st.selectbox(param['name'], param['options'], index=index, key=f"edit_{param['name']}")
                elif param['type'] == 'Число':
                    task_data[param['name']] = st.number_input(param['name'], min_value=0, value=current_value, key=f"edit_{param['name']}")
                elif param['type'] == 'Дата':
                    if isinstance(current_value, str):
                        current_date = datetime.fromisoformat(current_value).date()
                    else:
                        current_date = current_value
                    task_data[param['name']] = st.date_input(param['name'], value=current_date, min_value=datetime.now().date(), key=f"edit_{param['name']}")
                elif param['type'] == 'Множественный выбор':
                    task_data[param['name']] = st.multiselect(param['name'], param['options'], default=current_value, key=f"edit_{param['name']}")
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Сохранить изменения", type="primary"):
                if task_name and task_description:
                    # Обновляем заявку
                    task_to_edit['name'] = task_name
                    task_to_edit['description'] = task_description
                    task_to_edit.update(task_data)
                    
                    # Сохраняем в SQLite
                    save_task_to_db(task_to_edit)
                    st.session_state[f"editing_task_{editing_task_id}"] = False
                    st.session_state.tasks = load_tasks_from_db()
                    st.success("✅ Заявка успешно обновлена!")
                    st.rerun()
                else:
                    st.error("❌ Заполните обязательные поля")
        
        with col2:
            if st.button("❌ Отменить", type="secondary"):
                st.session_state[f"editing_task_{editing_task_id}"] = False
                st.rerun()
        
        with col3:
            if st.button("🗑️ Удалить заявку", type="secondary"):
                delete_task_from_db(editing_task_id)
                st.session_state.tasks = load_tasks_from_db()
                st.session_state.assignments = load_assignments_from_db()
                st.session_state[f"editing_task_{editing_task_id}"] = False
                st.success("✅ Заявка удалена!")
                st.rerun()
        
        return  # Выходим из функции, чтобы не показывать остальное
    
    # Создание новой заявки
    st.markdown("### ➕ Создать новую заявку")
    
    # Основная информация
    st.markdown("#### 📋 Основная информация")
    col1, col2 = st.columns(2)
    
    with col1:
        task_name = st.text_input("Название заявки", placeholder="Введите название заявки")
        task_description = st.text_area("Описание", placeholder="Подробное описание заявки")
    
    with col2:
        # Динамические параметры заявки
        task_data = {}
        for param in st.session_state.task_parameters:
            if param['type'] == 'Выбор из списка':
                # Специальная обработка для параметра "Категория"
                if param['name'] == 'Категория':
                    # Добавляем "Другое" в опции, если его еще нет
                    options = param['options'].copy()
                    if 'Другое' not in options:
                        options.append('Другое')
                    
                    selected_category = st.selectbox(param['name'], options)
                    
                    # Если выбрано "Другое", показываем поле для ввода
                    if selected_category == 'Другое':
                        other_category = st.text_input("Укажите категорию", placeholder="Введите название категории")
                        if other_category:
                            # Добавляем новую категорию в опции параметра
                            if other_category not in param['options']:
                                param['options'].append(other_category)
                            task_data[param['name']] = other_category
                        else:
                            task_data[param['name']] = 'Другое'
                    else:
                        task_data[param['name']] = selected_category
                else:
                    task_data[param['name']] = st.selectbox(param['name'], param['options'])
            elif param['type'] == 'Число':
                task_data[param['name']] = st.number_input(param['name'], min_value=0, value=100000)
            elif param['type'] == 'Дата':
                task_data[param['name']] = st.date_input(param['name'], min_value=datetime.now().date())
            elif param['type'] == 'Множественный выбор':
                task_data[param['name']] = st.multiselect(param['name'], param['options'])
    
    st.markdown("---")
    
    if st.button("📝 Создать заявку", type="primary"):
        if task_name and task_description:
            new_task = {
                'id': str(uuid.uuid4()),
                'name': task_name,
                'description': task_description,
                'status': 'Новая',
                'created_at': datetime.now().isoformat(),
                **task_data
            }
            # Сохраняем в SQLite
            save_task_to_db(new_task)
            st.session_state.tasks = load_tasks_from_db()
            
            # Автоматическое назначение
            best_executor = find_best_executor(new_task)
            if best_executor:
                assignment = {
                    'id': str(uuid.uuid4()),
                    'task_id': new_task['id'],
                    'executor_id': best_executor['id'],
                    'assigned_at': datetime.now().isoformat(),
                    'score': calculate_match_score(new_task, best_executor)
                }
                save_assignment_to_db(assignment)
                new_task['status'] = 'Назначена'
                new_task['assigned_to'] = best_executor['name']
                save_task_to_db(new_task)
            
            st.success("✅ Заявка успешно создана и назначена исполнителю!")
            st.rerun()
        else:
            st.error("❌ Заполните обязательные поля")
    
    # Список заявок
    st.markdown("### 📋 Список заявок")
    
    if st.session_state.tasks:
        # Фильтры
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Фильтр по статусу", ["Все", "Новая", "Назначена", "В работе", "Завершена"])
        with col2:
            category_filter = st.selectbox("Фильтр по категории", ["Все"] + [param['options'] for param in st.session_state.task_parameters if param['name'] == 'Категория'][0])
        with col3:
            priority_filter = st.selectbox("Фильтр по приоритету", ["Все"] + [param['options'] for param in st.session_state.task_parameters if param['name'] == 'Приоритет'][0])
        
        # Отображение заявок
        filtered_tasks = st.session_state.tasks
        if status_filter != "Все":
            filtered_tasks = [t for t in filtered_tasks if t.get('status') == status_filter]
        if category_filter != "Все":
            filtered_tasks = [t for t in filtered_tasks if t.get('Категория') == category_filter]
        if priority_filter != "Все":
            filtered_tasks = [t for t in filtered_tasks if t.get('Приоритет') == priority_filter]
        
        for i, task in enumerate(filtered_tasks):
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{task['name']}**")
                    st.markdown(f"*{task['description']}*")
                    
                    # Параметры заявки
                    params_text = []
                    for param in st.session_state.task_parameters:
                        if param['name'] in task and task[param['name']]:
                            if param['type'] == 'Множественный выбор':
                                params_text.append(f"**{param['name']}:** {', '.join(task[param['name']])}")
                            else:
                                params_text.append(f"**{param['name']}:** {task[param['name']]}")
                    
                    if params_text:
                        st.markdown(" | ".join(params_text))
                    
                    st.markdown(f"**Статус:** {task['status']} | **Создана:** {task['created_at'][:19]}")
                    
                    if 'assigned_to' in task:
                        st.markdown(f"**Назначена:** {task['assigned_to']}")
                
                with col2:
                    if st.button(f"✏️ Редактировать", key=f"edit_{task['id']}"):
                        st.session_state[f"editing_task_{task['id']}"] = True
                        st.rerun()
                
                with col3:
                    if st.button(f"🗑️ Удалить", key=f"delete_{task['id']}"):
                        delete_task_from_db(task['id'])
                        st.session_state.tasks = load_tasks_from_db()
                        st.session_state.assignments = load_assignments_from_db()
                        st.success("✅ Заявка удалена!")
                        st.rerun()
                
                st.markdown("---")
    else:
        st.info("📝 Заявок пока нет. Создайте первую заявку выше.")

# Управление исполнителями
def render_executors_management():
    st.markdown('<h2 class="section-header">👥 Управление исполнителями</h2>', unsafe_allow_html=True)
    
    # Проверка на редактирование исполнителя
    editing_executor_id = None
    for executor in st.session_state.executors:
        if st.session_state.get(f"editing_executor_{executor['id']}", False):
            editing_executor_id = executor['id']
            break
    
    if editing_executor_id:
        # Редактирование существующего исполнителя
        executor_to_edit = next(e for e in st.session_state.executors if e['id'] == editing_executor_id)
        st.markdown("### ✏️ Редактировать исполнителя")
        
        col1, col2 = st.columns(2)
        
        with col1:
            executor_name = st.text_input("Имя исполнителя", value=executor_to_edit['name'], key="edit_executor_name")
            executor_email = st.text_input("Email", value=executor_to_edit['email'], key="edit_executor_email")
            phone = st.text_input("Телефон", value=executor_to_edit.get('phone', ''), key="edit_executor_phone")
        
        with col2:
            # Динамические параметры исполнителя для редактирования
            executor_data = {}
            for param in st.session_state.executor_parameters:
                current_value = executor_to_edit.get(param['name'], '')
                if param['type'] == 'Выбор из списка':
                    # Находим индекс текущего значения
                    try:
                        index = param['options'].index(current_value)
                    except ValueError:
                        index = 0
                    executor_data[param['name']] = st.selectbox(param['name'], param['options'], index=index, key=f"edit_exec_{param['name']}")
                elif param['type'] == 'Число':
                    executor_data[param['name']] = st.number_input(param['name'], min_value=1, max_value=50, value=current_value, key=f"edit_exec_{param['name']}")
                elif param['type'] == 'Слайдер':
                    executor_data[param['name']] = st.slider(param['name'], param['options'][0], param['options'][1], current_value, key=f"edit_exec_{param['name']}")
                elif param['type'] == 'Множественный выбор':
                    executor_data[param['name']] = st.multiselect(param['name'], param['options'], default=current_value, key=f"edit_exec_{param['name']}")
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Сохранить изменения", type="primary"):
                if executor_name and executor_email:
                    # Обновляем исполнителя
                    executor_to_edit['name'] = executor_name
                    executor_to_edit['email'] = executor_email
                    executor_to_edit['phone'] = phone
                    executor_to_edit.update(executor_data)
                    
                    # Сохраняем в SQLite
                    save_executor_to_db(executor_to_edit)
                    st.session_state[f"editing_executor_{editing_executor_id}"] = False
                    st.session_state.executors = load_executors_from_db()
                    st.success("✅ Исполнитель успешно обновлен!")
                    st.rerun()
                else:
                    st.error("❌ Заполните обязательные поля")
        
        with col2:
            if st.button("❌ Отменить", type="secondary"):
                st.session_state[f"editing_executor_{editing_executor_id}"] = False
                st.rerun()
        
        with col3:
            if st.button("🗑️ Удалить исполнителя", type="secondary"):
                delete_executor_from_db(editing_executor_id)
                st.session_state.executors = load_executors_from_db()
                st.session_state.assignments = load_assignments_from_db()
                st.session_state[f"editing_executor_{editing_executor_id}"] = False
                st.success("✅ Исполнитель удален!")
                st.rerun()
        
        return  # Выходим из функции, чтобы не показывать остальное
    
    # Создание нового исполнителя
    st.markdown("### ➕ Добавить нового исполнителя")
    
    # Основная информация
    st.markdown("#### 👤 Основная информация")
    col1, col2 = st.columns(2)
    
    with col1:
        executor_name = st.text_input("Имя исполнителя", placeholder="Введите имя исполнителя")
        executor_email = st.text_input("Email", placeholder="email@example.com")
        phone = st.text_input("Телефон", placeholder="+7 (999) 123-45-67")
    
    with col2:
        # Динамические параметры исполнителя
        executor_data = {}
        for param in st.session_state.executor_parameters:
            if param['type'] == 'Выбор из списка':
                # Специальная обработка для параметра "Отдел"
                if param['name'] == 'Отдел':
                    # Добавляем "Другое" в опции, если его еще нет
                    options = param['options'].copy()
                    if 'Другое' not in options:
                        options.append('Другое')
                    
                    selected_department = st.selectbox(param['name'], options)
                    
                    # Если выбрано "Другое", показываем поле для ввода
                    if selected_department == 'Другое':
                        other_department = st.text_input("Укажите отдел", placeholder="Введите название отдела")
                        if other_department:
                            # Добавляем новый отдел в опции параметра
                            if other_department not in param['options']:
                                param['options'].append(other_department)
                            executor_data[param['name']] = other_department
                        else:
                            executor_data[param['name']] = 'Другое'
                    else:
                        executor_data[param['name']] = selected_department
                else:
                    executor_data[param['name']] = st.selectbox(param['name'], param['options'])
            elif param['type'] == 'Число':
                executor_data[param['name']] = st.number_input(param['name'], min_value=1, max_value=50, value=10)
            elif param['type'] == 'Слайдер':
                executor_data[param['name']] = st.slider(param['name'], param['options'][0], param['options'][1], 3)
            elif param['type'] == 'Множественный выбор':
                # Специальная обработка для параметра "Навыки"
                if param['name'] == 'Навыки':
                    # Добавляем "Другое" в опции, если его еще нет
                    options = param['options'].copy()
                    if 'Другое' not in options:
                        options.append('Другое')
                    
                    selected_skills = st.multiselect(param['name'], options)
                    
                    # Если выбрано "Другое", показываем поле для ввода
                    if 'Другое' in selected_skills:
                        other_skill = st.text_input("Укажите навык", placeholder="Введите название навыка")
                        if other_skill:
                            # Добавляем новый навык в опции параметра
                            if other_skill not in param['options']:
                                param['options'].append(other_skill)
                            # Заменяем "Другое" на введенный навык
                            selected_skills = [skill for skill in selected_skills if skill != 'Другое']
                            selected_skills.append(other_skill)
                        executor_data[param['name']] = selected_skills
                    else:
                        executor_data[param['name']] = selected_skills
                else:
                    executor_data[param['name']] = st.multiselect(param['name'], param['options'])
    
    st.markdown("---")
    
    if st.button("👥 Добавить исполнителя", type="primary"):
        if executor_name and executor_email:
            new_executor = {
                'id': str(uuid.uuid4()),
                'name': executor_name,
                'email': executor_email,
                'phone': phone,
                'active': True,
                'created_at': datetime.now().isoformat(),
                **executor_data
            }
            save_executor_to_db(new_executor)
            st.session_state.executors = load_executors_from_db()
            st.success("✅ Исполнитель успешно добавлен!")
            st.rerun()
        else:
            st.error("❌ Заполните обязательные поля")
    
    # Список исполнителей
    st.markdown("### 👥 Список исполнителей")
    
    if st.session_state.executors:
        for executor in st.session_state.executors:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    status_color = "🟢" if executor.get('active', True) else "🔴"
                    st.markdown(f"**{status_color} {executor['name']}**")
                    st.markdown(f"**Email:** {executor['email']} | **Телефон:** {executor['phone']}")
                    
                    # Параметры исполнителя
                    params_text = []
                    for param in st.session_state.executor_parameters:
                        if param['name'] in executor and executor[param['name']]:
                            if param['type'] == 'Множественный выбор':
                                params_text.append(f"**{param['name']}:** {', '.join(executor[param['name']])}")
                            elif param['type'] == 'Слайдер':
                                stars = '⭐' * executor[param['name']]
                                params_text.append(f"**{param['name']}:** {stars}")
                            else:
                                params_text.append(f"**{param['name']}:** {executor[param['name']]}")
                    
                    if params_text:
                        st.markdown(" | ".join(params_text))
                
                with col2:
                    if st.button(f"✏️ Редактировать", key=f"edit_exec_{executor['id']}"):
                        st.session_state[f"editing_executor_{executor['id']}"] = True
                        st.rerun()
                
                with col3:
                    if st.button(f"🗑️ Удалить", key=f"delete_exec_{executor['id']}"):
                        delete_executor_from_db(executor['id'])
                        st.session_state.executors = load_executors_from_db()
                        st.session_state.assignments = load_assignments_from_db()
                        st.success("✅ Исполнитель удален!")
                        st.rerun()
                
                st.markdown("---")
    else:
        st.info("👥 Исполнителей пока нет. Добавьте первого исполнителя выше.")

# Настройки параметров
def render_parameters_settings():
    st.markdown('<h2 class="section-header">⚙️ Настройки параметров</h2>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 🛠️ Управление параметрами системы
    
    Здесь вы можете добавлять, удалять и настраивать параметры для заявок и исполнителей.
    Все изменения применяются мгновенно!
    """)
    
    # Параметры заявок
    st.markdown("#### 📝 Параметры заявок")
    
    for i, param in enumerate(st.session_state.task_parameters):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
        
        with col1:
            new_name = st.text_input(f"Название параметра", value=param['name'], key=f"task_param_name_{i}")
            if new_name != param['name']:
                st.session_state.task_parameters[i]['name'] = new_name
        
        with col2:
            new_type = st.selectbox(f"Тип параметра", ["Выбор из списка", "Число", "Дата", "Множественный выбор"], 
                                  index=["Выбор из списка", "Число", "Дата", "Множественный выбор"].index(param['type']), 
                                  key=f"task_param_type_{i}")
            if new_type != param['type']:
                st.session_state.task_parameters[i]['type'] = new_type
                # Очищаем опции при смене типа
                st.session_state.task_parameters[i]['options'] = []
        
        with col3:
            weight = st.number_input(f"Вес", value=param['weight'], min_value=0.1, max_value=5.0, step=0.1, key=f"task_param_weight_{i}")
            st.session_state.task_parameters[i]['weight'] = weight
        
        with col4:
            if st.button("⚙️", key=f"edit_task_param_{i}", help="Редактировать опции"):
                st.session_state[f"editing_task_param_{i}"] = True
                st.rerun()
        
        with col5:
            if st.button("🗑️", key=f"del_task_param_{i}"):
                st.session_state.task_parameters.pop(i)
                st.rerun()
        
        # Редактирование опций параметра
        if st.session_state.get(f"editing_task_param_{i}", False):
            st.markdown(f"**Редактирование опций для параметра: {param['name']}**")
            
            # Показываем текущие опции
            current_options = param.get('options', [])
            st.markdown("**Текущие опции:**")
            for j, option in enumerate(current_options):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.text_input(f"Опция {j+1}", value=option, key=f"task_option_{i}_{j}")
                with col_b:
                    if st.button("🗑️", key=f"del_task_option_{i}_{j}"):
                        current_options.pop(j)
                        st.session_state.task_parameters[i]['options'] = current_options
                        st.rerun()
            
            # Добавление новой опции
            col_a, col_b = st.columns([3, 1])
            with col_a:
                new_option = st.text_input("Новая опция", key=f"new_task_option_{i}")
            with col_b:
                if st.button("➕", key=f"add_task_option_{i}"):
                    if new_option and new_option not in current_options:
                        current_options.append(new_option)
                        st.session_state.task_parameters[i]['options'] = current_options
                        st.rerun()
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("💾 Сохранить", key=f"save_task_param_{i}"):
                    st.session_state[f"editing_task_param_{i}"] = False
                    st.rerun()
            with col_b:
                if st.button("❌ Отменить", key=f"cancel_task_param_{i}"):
                    st.session_state[f"editing_task_param_{i}"] = False
                    st.rerun()
            
            st.markdown("---")
    
    # Добавление нового параметра заявки
    st.markdown("---")
    st.markdown("#### ➕ Добавить новый параметр заявки")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        new_param_name = st.text_input("Название параметра", key="new_task_param_name")
    with col2:
        new_param_type = st.selectbox("Тип параметра", ["Выбор из списка", "Число", "Дата", "Множественный выбор"], key="new_task_param_type")
    with col3:
        new_param_weight = st.number_input("Вес", min_value=0.1, max_value=5.0, step=0.1, value=1.0, key="new_task_param_weight")
    
    if st.button("➕ Добавить параметр заявки"):
        if new_param_name:
            new_param = {
                'name': new_param_name,
                'type': new_param_type,
                'options': [],
                'weight': new_param_weight
            }
            st.session_state.task_parameters.append(new_param)
            st.success(f"✅ Параметр '{new_param_name}' добавлен!")
            st.rerun()
    
    st.markdown("---")
    
    # Параметры исполнителей
    st.markdown("#### 👥 Параметры исполнителей")
    
    for i, param in enumerate(st.session_state.executor_parameters):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
        
        with col1:
            new_name = st.text_input(f"Название параметра", value=param['name'], key=f"exec_param_name_{i}")
            if new_name != param['name']:
                st.session_state.executor_parameters[i]['name'] = new_name
        
        with col2:
            new_type = st.selectbox(f"Тип параметра", ["Выбор из списка", "Число", "Слайдер", "Множественный выбор"], 
                                  index=["Выбор из списка", "Число", "Слайдер", "Множественный выбор"].index(param['type']), 
                                  key=f"exec_param_type_{i}")
            if new_type != param['type']:
                st.session_state.executor_parameters[i]['type'] = new_type
                # Очищаем опции при смене типа
                st.session_state.executor_parameters[i]['options'] = []
        
        with col3:
            weight = st.number_input(f"Вес", value=param['weight'], min_value=0.1, max_value=5.0, step=0.1, key=f"exec_param_weight_{i}")
            st.session_state.executor_parameters[i]['weight'] = weight
        
        with col4:
            if st.button("⚙️", key=f"edit_exec_param_{i}", help="Редактировать опции"):
                st.session_state[f"editing_exec_param_{i}"] = True
                st.rerun()
        
        with col5:
            if st.button("🗑️", key=f"del_exec_param_{i}"):
                st.session_state.executor_parameters.pop(i)
                st.rerun()
        
        # Редактирование опций параметра
        if st.session_state.get(f"editing_exec_param_{i}", False):
            st.markdown(f"**Редактирование опций для параметра: {param['name']}**")
            
            # Показываем текущие опции
            current_options = param.get('options', [])
            st.markdown("**Текущие опции:**")
            for j, option in enumerate(current_options):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.text_input(f"Опция {j+1}", value=option, key=f"exec_option_{i}_{j}")
                with col_b:
                    if st.button("🗑️", key=f"del_exec_option_{i}_{j}"):
                        current_options.pop(j)
                        st.session_state.executor_parameters[i]['options'] = current_options
                        st.rerun()
            
            # Добавление новой опции
            col_a, col_b = st.columns([3, 1])
            with col_a:
                new_option = st.text_input("Новая опция", key=f"new_exec_option_{i}")
            with col_b:
                if st.button("➕", key=f"add_exec_option_{i}"):
                    if new_option and new_option not in current_options:
                        current_options.append(new_option)
                        st.session_state.executor_parameters[i]['options'] = current_options
                        st.rerun()
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("💾 Сохранить", key=f"save_exec_param_{i}"):
                    st.session_state[f"editing_exec_param_{i}"] = False
                    st.rerun()
            with col_b:
                if st.button("❌ Отменить", key=f"cancel_exec_param_{i}"):
                    st.session_state[f"editing_exec_param_{i}"] = False
                    st.rerun()
            
            st.markdown("---")
    
    # Добавление нового параметра исполнителя
    st.markdown("---")
    st.markdown("#### ➕ Добавить новый параметр исполнителя")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        new_param_name = st.text_input("Название параметра", key="new_exec_param_name")
    with col2:
        new_param_type = st.selectbox("Тип параметра", ["Выбор из списка", "Число", "Слайдер", "Множественный выбор"], key="new_exec_param_type")
    with col3:
        new_param_weight = st.number_input("Вес", min_value=0.1, max_value=5.0, step=0.1, value=1.0, key="new_exec_param_weight")
    
    if st.button("➕ Добавить параметр исполнителя"):
        if new_param_name:
            new_param = {
                'name': new_param_name,
                'type': new_param_type,
                'options': [],
                'weight': new_param_weight
            }
            st.session_state.executor_parameters.append(new_param)
            st.success(f"✅ Параметр '{new_param_name}' добавлен!")
            st.rerun()
    
    st.markdown("---")

# Отчеты
def render_reports():
    st.markdown('<h2 class="section-header">📈 Отчеты и аналитика</h2>', unsafe_allow_html=True)
    
    if not st.session_state.tasks:
        st.info("📊 Нет данных для отображения отчетов")
        return
    
    # Выбор периода
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Начальная дата", value=datetime.now().date() - timedelta(days=30))
    with col2:
        end_date = st.date_input("Конечная дата", value=datetime.now().date())
    
    # Основные метрики
    st.markdown("### 📊 Ключевые показатели")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_tasks = len(st.session_state.tasks)
        st.metric("Всего заявок", total_tasks)
    
    with col2:
        completed_tasks = len([t for t in st.session_state.tasks if t.get('status') == 'Завершена'])
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        st.metric("Процент выполнения", f"{completion_rate:.1f}%")
    
    with col3:
        active_executors = len([e for e in st.session_state.executors if e.get('active', True)])
        tasks_per_executor = total_tasks / active_executors if active_executors > 0 else 0
        st.metric("Заявок на исполнителя", f"{tasks_per_executor:.1f}")
    
    with col4:
        avg_score = sum([a.get('score', 0) for a in st.session_state.assignments]) / len(st.session_state.assignments) if st.session_state.assignments else 0
        st.metric("Средний балл соответствия", f"{avg_score:.1f}")
    
    # Графики
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Распределение по категориям")
        category_counts = {}
        for task in st.session_state.tasks:
            category = task.get('Категория', 'Не указана')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        if category_counts:
            fig = px.pie(
                values=list(category_counts.values()),
                names=list(category_counts.keys()),
                title="Заявки по категориям"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📊 Эффективность исполнителей")
        executor_scores = {}
        for assignment in st.session_state.assignments:
            executor_id = assignment.get('executor_id')
            score = assignment.get('score', 0)
            if executor_id not in executor_scores:
                executor_scores[executor_id] = []
            executor_scores[executor_id].append(score)
        
        if executor_scores:
            avg_scores = {executor_id: sum(scores)/len(scores) for executor_id, scores in executor_scores.items()}
            executor_names = {executor['id']: executor['name'] for executor in st.session_state.executors}
            
            df = pd.DataFrame([
                {'Исполнитель': executor_names.get(executor_id, 'Неизвестно'), 'Средний балл': avg_score}
                for executor_id, avg_score in avg_scores.items()
            ])
            
            fig = px.bar(df, x='Исполнитель', y='Средний балл', title='Средний балл соответствия')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    # Экспорт данных
    st.markdown("### 📤 Экспорт данных")
    if st.session_state.tasks:
        csv_data = pd.DataFrame(st.session_state.tasks).to_csv(index=False)
        st.download_button(
            label="📥 Скачать отчет в CSV",
            data=csv_data,
            file_name=f"tasks_report_{start_date}_{end_date}.csv",
            mime="text/csv"
        )

# Управление системой
def render_settings():
    st.markdown('<h2 class="section-header">🔧 Управление системой</h2>', unsafe_allow_html=True)
    
    st.markdown("### ⚙️ Общие настройки")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎯 Параметры распределения")
        auto_assignment = st.checkbox("Автоматическое назначение заявок", value=True)
        fairness_threshold = st.slider("Порог справедливости", 0.0, 1.0, 0.8, 0.1)
    
    with col2:
        st.markdown("#### 📊 Настройки отчетов")
        default_period = st.selectbox("Период по умолчанию", ["7 дней", "30 дней", "90 дней", "1 год"])
        auto_refresh = st.checkbox("Автообновление дашборда", value=st.session_state.get('auto_refresh', True))
        st.session_state.auto_refresh = auto_refresh
    
    # Сброс данных
    st.markdown("### 🗑️ Управление данными")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Очистить все заявки", type="secondary"):
            st.session_state.tasks = []
            st.session_state.assignments = []
            st.success("✅ Все заявки удалены!")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Очистить всех исполнителей", type="secondary"):
            st.session_state.executors = []
            st.session_state.assignments = []
            st.success("✅ Все исполнители удалены!")
            st.rerun()
    
    with col3:
        if st.button("🗑️ Сбросить все настройки", type="secondary"):
            st.session_state.task_parameters = [
                {'name': 'Приоритет', 'type': 'Выбор из списка', 'options': ['Низкий', 'Средний', 'Высокий', 'Критический'], 'weight': 2.0},
                {'name': 'Категория', 'type': 'Выбор из списка', 'options': ['IT', 'Строительство', 'Страхование', 'Консалтинг'], 'weight': 1.5},
                {'name': 'Сложность', 'type': 'Выбор из списка', 'options': ['Простая', 'Средняя', 'Сложная', 'Экспертная'], 'weight': 1.8},
                {'name': 'Бюджет', 'type': 'Число', 'options': [], 'weight': 1.0},
                {'name': 'Срок выполнения', 'type': 'Дата', 'options': [], 'weight': 1.2}
            ]
            st.session_state.executor_parameters = [
                {'name': 'Навыки', 'type': 'Множественный выбор', 'options': ['Python', 'JavaScript', 'Строительство', 'Проектирование', 'Анализ рисков', 'Продажи'], 'weight': 2.0},
                {'name': 'Опыт работы', 'type': 'Выбор из списка', 'options': ['До 1 года', '1-3 года', '3-5 лет', '5-10 лет', 'Более 10 лет'], 'weight': 1.8},
                {'name': 'Рейтинг', 'type': 'Слайдер', 'options': [1, 5], 'weight': 1.5},
                {'name': 'Отдел', 'type': 'Выбор из списка', 'options': ['IT', 'Строительство', 'Страхование', 'Консалтинг'], 'weight': 1.3},
                {'name': 'Максимум заявок в день', 'type': 'Число', 'options': [], 'weight': 1.0}
            ]
            st.success("✅ Настройки сброшены!")
            st.rerun()

# Вспомогательные функции
def find_best_executor(task):
    """Поиск лучшего исполнителя для заявки"""
    active_executors = [e for e in st.session_state.executors if e.get('active', True)]
    if not active_executors:
        return None
    
    best_executor = None
    best_score = 0
    
    for executor in active_executors:
        score = calculate_match_score(task, executor)
        if score > best_score:
            best_score = score
            best_executor = executor
    
    return best_executor

def calculate_match_score(task, executor):
    """Расчет соответствия заявки и исполнителя"""
    score = 0
    
    # Соответствие категории и отдела
    task_category = task.get('Категория')
    executor_department = executor.get('Отдел')
    
    if task_category == executor_department:
        score += 3.0
    
    # Соответствие навыков
    task_skills = []
    if task_category == 'IT':
        if 'Python' in str(task.get('Навыки', '')):
            task_skills.append('Python')
        if 'JavaScript' in str(task.get('Навыки', '')):
            task_skills.append('JavaScript')
    elif task_category == 'Строительство':
        task_skills = ['Проектирование', 'Строительство']
    elif task_category == 'Страхование':
        task_skills = ['Анализ рисков', 'Продажи']
    elif task_category == 'Консалтинг':
        task_skills = ['Бизнес-анализ', 'Процессы']
    
    executor_skills = executor.get('Навыки', [])
    if isinstance(executor_skills, list):
        skill_matches = len(set(task_skills) & set(executor_skills))
        if task_skills:
            score += (skill_matches / len(task_skills)) * 2.0
    
    # Соответствие сложности и опыта
    complexity_experience_map = {
        'Простая': ['До 1 года', '1-3 года'],
        'Средняя': ['1-3 года', '3-5 лет'],
        'Сложная': ['3-5 лет', '5-10 лет'],
        'Экспертная': ['5-10 лет', 'Более 10 лет']
    }
    
    task_complexity = task.get('Сложность')
    executor_experience = executor.get('Опыт работы')
    
    if executor_experience in complexity_experience_map.get(task_complexity, []):
        score += 1.5
    
    # Рейтинг исполнителя
    executor_rating = executor.get('Рейтинг', 3)
    score += executor_rating * 0.5
    
    # Доступность (чем меньше назначений, тем выше приоритет)
    assigned_count = len([a for a in st.session_state.assignments if a.get('executor_id') == executor['id']])
    capacity = executor.get('Максимум заявок в день', 10)
    availability_score = max(0, (capacity - assigned_count) / capacity)
    score += availability_score * 1.0
    
    return score

# Главная функция
def main():
    init_session_state()
    render_header()
    
    # Главное меню
    selected_page = render_main_menu()
    
    # Отображение выбранной страницы
    if selected_page == "dashboard":
        render_dashboard()
    elif selected_page == "tasks":
        render_tasks_management()
    elif selected_page == "executors":
        render_executors_management()
    elif selected_page == "parameters":
        render_parameters_settings()
    elif selected_page == "reports":
        render_reports()
    elif selected_page == "settings":
        render_settings()

if __name__ == "__main__":
    main()