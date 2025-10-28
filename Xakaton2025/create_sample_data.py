#!/usr/bin/env python3
"""
Скрипт инициализации тестовых данных для АИС
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any

def create_sample_executors() -> List[Dict[str, Any]]:
    """Создание тестовых исполнителей"""
    return [
        {
            "id": str(uuid.uuid4()),
            "name": "Анна Петрова",
            "email": "anna.petrova@company.com",
            "phone": "+7 (999) 123-45-67",
            "department": "IT",
            "skills": ["Python", "FastAPI", "SQL", "Docker"],
            "experience": "3-5 лет",
            "rating": 4,
            "capacity": 8,
            "active": True,
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "specialization": "Backend разработка",
                "certifications": ["AWS", "Python Professional"],
                "languages": ["Русский", "Английский"]
            }
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Михаил Смирнов",
            "email": "mikhail.smirnov@company.com",
            "phone": "+7 (999) 234-56-78",
            "department": "Строительство",
            "skills": ["Проектирование", "Смета", "Контроль качества"],
            "experience": "5-10 лет",
            "rating": 5,
            "capacity": 6,
            "active": True,
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "specialization": "Жилые здания",
                "certifications": ["ГИП", "СРО"],
                "languages": ["Русский"]
            }
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Елена Козлова",
            "email": "elena.kozlova@company.com",
            "phone": "+7 (999) 345-67-89",
            "department": "Страхование",
            "skills": ["Анализ рисков", "Оценка ущерба", "Продажи"],
            "experience": "1-3 года",
            "rating": 3,
            "capacity": 10,
            "active": True,
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "specialization": "Автострахование",
                "certifications": ["Страховой агент"],
                "languages": ["Русский", "Английский"]
            }
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Дмитрий Волков",
            "email": "dmitry.volkov@company.com",
            "phone": "+7 (999) 456-78-90",
            "department": "IT",
            "skills": ["JavaScript", "React", "Node.js", "MongoDB"],
            "experience": "1-3 года",
            "rating": 3,
            "capacity": 12,
            "active": True,
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "specialization": "Frontend разработка",
                "certifications": ["React Developer"],
                "languages": ["Русский", "Английский"]
            }
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Ольга Морозова",
            "email": "olga.morozova@company.com",
            "phone": "+7 (999) 567-89-01",
            "department": "Консалтинг",
            "skills": ["Бизнес-анализ", "Процессы", "Управление проектами"],
            "experience": "Более 10 лет",
            "rating": 5,
            "capacity": 4,
            "active": True,
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "specialization": "Бизнес-консалтинг",
                "certifications": ["PMP", "MBA"],
                "languages": ["Русский", "Английский", "Немецкий"]
            }
        }
    ]

def create_sample_tasks() -> List[Dict[str, Any]]:
    """Создание тестовых заявок"""
    return [
        {
            "id": str(uuid.uuid4()),
            "name": "Разработка API для мобильного приложения",
            "description": "Необходимо создать REST API для мобильного приложения с использованием FastAPI и PostgreSQL",
            "priority": "Высокий",
            "category": "IT",
            "complexity": "Средняя",
            "deadline": (datetime.now() + timedelta(days=14)).isoformat(),
            "budget": 150000,
            "status": "new",
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "technology_stack": "Python, FastAPI, PostgreSQL",
                "team_size": "2-3 человека",
                "client": "Стартап TechCorp"
            }
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Проектирование жилого комплекса",
            "description": "Разработка архитектурного проекта жилого комплекса на 200 квартир",
            "priority": "Критический",
            "category": "Строительство",
            "complexity": "Экспертная",
            "deadline": (datetime.now() + timedelta(days=30)).isoformat(),
            "budget": 500000,
            "status": "new",
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "building_type": "Многоквартирный дом",
                "floors": "9 этажей",
                "location": "Москва, САО"
            }
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Страхование автопарка компании",
            "description": "Оформление комплексного страхования для автопарка из 50 автомобилей",
            "priority": "Средний",
            "category": "Страхование",
            "complexity": "Средняя",
            "deadline": (datetime.now() + timedelta(days=7)).isoformat(),
            "budget": 200000,
            "status": "new",
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "vehicle_count": "50 автомобилей",
                "insurance_type": "КАСКО + ОСАГО",
                "company": "Логистическая компания"
            }
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Оптимизация бизнес-процессов",
            "description": "Анализ и оптимизация бизнес-процессов производственного предприятия",
            "priority": "Высокий",
            "category": "Консалтинг",
            "complexity": "Сложная",
            "deadline": (datetime.now() + timedelta(days=21)).isoformat(),
            "budget": 300000,
            "status": "new",
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "industry": "Производство",
                "employees": "500+ сотрудников",
                "scope": "Полный аудит процессов"
            }
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Создание корпоративного сайта",
            "description": "Разработка современного корпоративного сайта с админ-панелью",
            "priority": "Средний",
            "category": "IT",
            "complexity": "Средняя",
            "deadline": (datetime.now() + timedelta(days=10)).isoformat(),
            "budget": 100000,
            "status": "new",
            "created_at": datetime.now().isoformat(),
            "parameters": {
                "technology_stack": "React, Node.js, MongoDB",
                "pages": "15-20 страниц",
                "features": "CMS, блог, контакты"
            }
        }
    ]

def create_sample_assignments() -> List[Dict[str, Any]]:
    """Создание тестовых назначений"""
    return []

def save_sample_data():
    """Сохранение тестовых данных в файлы"""
    
    # Создаем данные
    executors = create_sample_executors()
    tasks = create_sample_tasks()
    assignments = create_sample_assignments()
    
    # Сохраняем в JSON файлы
    with open('sample_data/executors.json', 'w', encoding='utf-8') as f:
        json.dump(executors, f, ensure_ascii=False, indent=2)
    
    with open('sample_data/tasks.json', 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    
    with open('sample_data/assignments.json', 'w', encoding='utf-8') as f:
        json.dump(assignments, f, ensure_ascii=False, indent=2)
    
    print("Тестовые данные созданы:")
    print(f"   - {len(executors)} исполнителей")
    print(f"   - {len(tasks)} заявок")
    print(f"   - {len(assignments)} назначений")
    print("\nФайлы сохранены в папку sample_data/")

if __name__ == "__main__":
    import os
    os.makedirs('sample_data', exist_ok=True)
    save_sample_data()
