"""
Тестовый скрипт для демонстрации работы Rule Engine
"""

import json
import sys
import os

# Добавляем путь к scripts
sys.path.insert(0, os.path.dirname(__file__))
from rule_engine import RuleEngine

def test_basic_matching():
    """Тест базового матчинга"""
    print("=" * 60)
    print("TEST 1: Basic Matching")
    print("=" * 60)
    
    # Простая конфигурация правил
    config = {
        "rules": [
            {
                "id": "department_match",
                "condition": {
                    "type": "equals",
                    "executor_field": "department",
                    "task_field": "category"
                },
                "score_multiplier": 1.5,
                "weight": 10
            },
            {
                "id": "fairness",
                "formula": "1.0 - (executor.assigned_count / executor.max_assignments)",
                "weight": 20
            }
        ]
    }
    
    engine = RuleEngine(config)
    
    # Тестовая заявка
    task = {
        "id": "1",
        "category": "IT",
        "priority": "Высокий"
    }
    
    # Тестовые исполнители
    executors = [
        {
            "id": "1",
            "name": "Иван",
            "department": "IT",
            "assigned_count": 5,
            "max_assignments": 10
        },
        {
            "id": "2",
            "name": "Петр",
            "department": "Строительство",
            "assigned_count": 3,
            "max_assignments": 10
        },
        {
            "id": "3",
            "name": "Мария",
            "department": "IT",
            "assigned_count": 2,
            "max_assignments": 10
        }
    ]
    
    # Поиск лучшего
    result = engine.find_best_match(task, executors)
    
    if result:
        executor, score, matched_rules = result
        print(f"\n[RESULT] Best match: {executor['name']}")
        print(f"[SCORE] {score:.2f}")
        print(f"[RULES] Matched: {', '.join(matched_rules)}")
        print(f"\n[EXPLANATION]")
        print(f"  - Отдел совпадает: {'Да' if executor['department'] == task['category'] else 'Нет'}")
        print(f"  - Загрузка: {executor['assigned_count']}/{executor['max_assignments']}")
    else:
        print("[ERROR] No match found")
    
    return result is not None


def test_skill_matching():
    """Тест матчинга по навыкам"""
    print("\n" + "=" * 60)
    print("TEST 2: Skill Matching")
    print("=" * 60)
    
    config = {
        "rules": [
            {
                "id": "skill_match",
                "condition": {
                    "type": "array_contains",
                    "executor_field": "params.skills",
                    "task_field": "params.required_skills"
                },
                "score_multiplier": 2.0,
                "weight": 15
            },
            {
                "id": "experience",
                "condition": {
                    "type": "greater_or_equal",
                    "executor_field": "params.experience_years",
                    "task_field": "params.min_experience_years"
                },
                "score_multiplier": 1.5,
                "weight": 10
            }
        ]
    }
    
    engine = RuleEngine(config)
    
    task = {
        "id": "2",
        "category": "IT",
        "params": {
            "required_skills": ["Python", "React"],
            "min_experience_years": 3
        }
    }
    
    executors = [
        {
            "id": "1",
            "name": "Иван",
            "params": {
                "skills": ["Python", "React", "Docker"],
                "experience_years": 5
            }
        },
        {
            "id": "2",
            "name": "Петр",
            "params": {
                "skills": ["Java", "Spring"],
                "experience_years": 7
            }
        },
        {
            "id": "3",
            "name": "Мария",
            "params": {
                "skills": ["Python"],
                "experience_years": 2
            }
        }
    ]
    
    # Ранжирование всех
    results = engine.rank_executors(task, executors)
    
    print("\n[RANKING]")
    for i, (executor, score, matched_rules) in enumerate(results, 1):
        print(f"{i}. {executor['name']}: {score:.2f} points")
        print(f"   Skills: {executor['params'].get('skills', [])}")
        print(f"   Experience: {executor['params'].get('experience_years')} years")
        print(f"   Matched rules: {', '.join(matched_rules) if matched_rules else 'None'}")
        print()
    
    return len(results) > 0


def test_complex_scenario():
    """Тест сложного сценария с множеством параметров"""
    print("=" * 60)
    print("TEST 3: Complex Scenario (Multiple Parameters)")
    print("=" * 60)
    
    # Загружаем реальную конфигурацию
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'matching_rules.json')
    
    if not os.path.exists(config_path):
        print(f"[SKIP] Config not found: {config_path}")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    engine = RuleEngine(config)
    print(f"[INFO] Loaded {len(config['rules'])} rules from config")
    
    # Сложная заявка
    task = {
        "id": "3",
        "category": "IT",
        "priority": "Критический",
        "is_active": 1,
        "params": {
            "required_skills": ["Python", "FastAPI"],
            "min_experience_years": 3,
            "complexity": 7,
            "remote_work": True,
            "max_hourly_rate": 5000
        }
    }
    
    # Исполнители с разными параметрами
    executors = [
        {
            "id": "1",
            "name": "Иван (Senior)",
            "department": "IT",
            "rating": 5.0,
            "is_active": 1,
            "assigned_count": 3,
            "max_assignments": 10,
            "params": {
                "skills": ["Python", "FastAPI", "PostgreSQL"],
                "experience_years": 7,
                "max_complexity": 10,
                "remote_available": True,
                "hourly_rate": 4500,
                "certifications": ["AWS", "Python Professional"]
            }
        },
        {
            "id": "2",
            "name": "Петр (Middle)",
            "department": "IT",
            "rating": 4.2,
            "is_active": 1,
            "assigned_count": 1,
            "max_assignments": 10,
            "params": {
                "skills": ["Python", "Django"],
                "experience_years": 4,
                "max_complexity": 7,
                "remote_available": True,
                "hourly_rate": 3500
            }
        },
        {
            "id": "3",
            "name": "Мария (Junior)",
            "department": "IT",
            "rating": 4.8,
            "is_active": 1,
            "assigned_count": 0,
            "max_assignments": 10,
            "params": {
                "skills": ["Python"],
                "experience_years": 2,
                "max_complexity": 5,
                "remote_available": True,
                "hourly_rate": 2500
            }
        }
    ]
    
    # Ранжирование
    results = engine.rank_executors(task, executors, top_n=3)
    
    print("\n[TASK]")
    print(f"  Category: {task['category']}")
    print(f"  Priority: {task['priority']}")
    print(f"  Required: {task['params']['required_skills']}, {task['params']['min_experience_years']}+ years")
    print(f"  Complexity: {task['params']['complexity']}/10")
    print(f"  Budget: {task['params']['max_hourly_rate']} руб/час")
    
    print("\n[TOP MATCHES]")
    for i, (executor, score, matched_rules) in enumerate(results, 1):
        print(f"\n{i}. {executor['name']} - {score:.2f} points")
        print(f"   Department: {executor.get('department')}")
        print(f"   Rating: {executor.get('rating')}/5.0")
        print(f"   Utilization: {executor['assigned_count']}/{executor['max_assignments']}")
        print(f"   Skills: {executor['params'].get('skills', [])}")
        print(f"   Experience: {executor['params'].get('experience_years')} years")
        print(f"   Rate: {executor['params'].get('hourly_rate')} руб/час")
        print(f"   Matched rules ({len(matched_rules)}): {', '.join(matched_rules[:5])}")
        if len(matched_rules) > 5:
            print(f"      ... and {len(matched_rules) - 5} more")
    
    return len(results) > 0


def main():
    """Запуск всех тестов"""
    print("\n")
    print("=" * 60)
    print(" " * 20 + "RULE ENGINE TESTS")
    print("=" * 60)
    print()
    
    tests = [
        ("Basic Matching", test_basic_matching),
        ("Skill Matching", test_skill_matching),
        ("Complex Scenario", test_complex_scenario)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n[ERROR] {name} failed: {e}")
            results.append((name, False))
    
    # Итоги
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    for name, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {name}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())

