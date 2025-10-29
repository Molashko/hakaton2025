"""
Rule Engine - Движок правил для динамического матчинга заявок и исполнителей

Поддерживает:
- Динамические параметры через JSON
- Конфигурируемые правила матчинга
- Различные типы условий (equals, greater, contains, array_match)
- Настраиваемые веса правил
- Формулы для вычисления score
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple


class RuleEngine:
    """Движок правил для матчинга заявок и исполнителей"""
    
    def __init__(self, rules_config: Dict):
        """
        Инициализация движка правил
        
        Args:
            rules_config: Конфигурация правил в формате dict
        """
        self.rules = rules_config.get('rules', [])
        self.default_weight = rules_config.get('default_weight', 1.0)
        
    def get_nested_value(self, obj: Dict, path: str) -> Any:
        """
        Получить значение по вложенному пути (например: params.skills)
        
        Args:
            obj: Объект (dict)
            path: Путь к значению через точку
            
        Returns:
            Значение или None если не найдено
        """
        if not path:
            return None
            
        parts = path.split('.')
        value = obj
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
                
            if value is None:
                return None
                
        return value
    
    def evaluate_condition(self, condition: Dict, executor: Dict, task: Dict) -> bool:
        """
        Проверить выполнение условия
        
        Args:
            condition: Описание условия
            executor: Данные исполнителя
            task: Данные заявки
            
        Returns:
            True если условие выполнено
        """
        condition_type = condition.get('type')
        
        # Получаем значения
        exec_field = condition.get('executor_field')
        task_field = condition.get('task_field')
        
        exec_value = self.get_nested_value(executor, exec_field) if exec_field else None
        task_value = self.get_nested_value(task, task_field) if task_field else None
        
        # Если хотя бы одно значение отсутствует - условие не выполнено
        # (кроме случая optional=True)
        if condition.get('optional', False):
            if exec_value is None or task_value is None:
                return True  # Опциональное правило - не применяется
        else:
            if exec_value is None or task_value is None:
                return False
        
        # Проверка по типу
        if condition_type == 'equals':
            return exec_value == task_value
        
        elif condition_type == 'not_equals':
            return exec_value != task_value
        
        elif condition_type == 'greater':
            try:
                return float(exec_value) > float(task_value)
            except (ValueError, TypeError):
                return False
        
        elif condition_type == 'greater_or_equal':
            try:
                return float(exec_value) >= float(task_value)
            except (ValueError, TypeError):
                return False
        
        elif condition_type == 'less':
            try:
                return float(exec_value) < float(task_value)
            except (ValueError, TypeError):
                return False
        
        elif condition_type == 'less_or_equal':
            try:
                return float(exec_value) <= float(task_value)
            except (ValueError, TypeError):
                return False
        
        elif condition_type == 'contains':
            # Строка содержит подстроку
            return str(task_value).lower() in str(exec_value).lower()
        
        elif condition_type == 'array_contains':
            # Массив содержит все требуемые элементы
            if not isinstance(exec_value, list) or not isinstance(task_value, list):
                return False
            return all(item in exec_value for item in task_value)
        
        elif condition_type == 'array_intersects':
            # Массивы имеют хотя бы один общий элемент
            if not isinstance(exec_value, list) or not isinstance(task_value, list):
                return False
            return any(item in exec_value for item in task_value)
        
        elif condition_type == 'in_range':
            # Значение в диапазоне [min, max]
            try:
                min_val = condition.get('min', float('-inf'))
                max_val = condition.get('max', float('inf'))
                value = float(exec_value)
                return min_val <= value <= max_val
            except (ValueError, TypeError):
                return False
        
        elif condition_type == 'regex':
            # Регулярное выражение
            pattern = condition.get('pattern', '')
            return bool(re.search(pattern, str(exec_value)))
        
        return False
    
    def evaluate_formula(self, formula: str, executor: Dict, task: Dict) -> float:
        """
        Вычислить формулу для score
        
        Args:
            formula: Формула (например: "1.0 - (executor.assigned / executor.limit)")
            executor: Данные исполнителя
            task: Данные заявки
            
        Returns:
            Результат вычисления
        """
        try:
            # Заменяем пути на значения
            # executor.assigned -> значение
            # task.priority -> значение
            
            # Находим все пути вида executor.xxx или task.xxx
            paths = re.findall(r'(executor|task)\.([a-zA-Z_][a-zA-Z0-9_\.]*)', formula)
            
            result_formula = formula
            for obj_name, path in paths:
                full_path = f"{obj_name}.{path}"
                
                if obj_name == 'executor':
                    value = self.get_nested_value(executor, path)
                else:
                    value = self.get_nested_value(task, path)
                
                # Заменяем путь на значение
                if value is not None:
                    result_formula = result_formula.replace(full_path, str(value))
                else:
                    result_formula = result_formula.replace(full_path, '0')
            
            # Вычисляем формулу
            # ВНИМАНИЕ: eval опасен! Используйте только с проверенными формулами
            result = eval(result_formula, {"__builtins__": {}}, {})
            return float(result)
            
        except Exception as e:
            print(f"[WARN] Ошибка вычисления формулы '{formula}': {e}")
            return 0.0
    
    def calculate_score(self, executor: Dict, task: Dict) -> Tuple[float, List[str]]:
        """
        Вычислить score для пары исполнитель-заявка
        
        Args:
            executor: Данные исполнителя
            task: Данные заявки
            
        Returns:
            (score, matched_rules): Score и список сработавших правил
        """
        total_score = 0.0
        matched_rules = []
        
        for rule in self.rules:
            rule_id = rule.get('id', 'unknown')
            weight = rule.get('weight', self.default_weight)
            
            # Если есть условие - проверяем его
            if 'condition' in rule:
                if not self.evaluate_condition(rule['condition'], executor, task):
                    continue  # Условие не выполнено
            
            # Условие выполнено или отсутствует
            matched_rules.append(rule_id)
            
            # Вычисляем score для этого правила
            if 'score_multiplier' in rule:
                # Простой множитель
                score = rule['score_multiplier'] * weight
            elif 'formula' in rule:
                # Формула
                score = self.evaluate_formula(rule['formula'], executor, task) * weight
            else:
                # Просто вес
                score = weight
            
            total_score += score
        
        return total_score, matched_rules
    
    def find_best_match(self, task: Dict, executors: List[Dict]) -> Optional[Tuple[Dict, float, List[str]]]:
        """
        Найти лучшего исполнителя для заявки
        
        Args:
            task: Данные заявки
            executors: Список исполнителей
            
        Returns:
            (executor, score, matched_rules) или None если не найдено
        """
        if not executors:
            return None
        
        results = []
        
        for executor in executors:
            score, matched_rules = self.calculate_score(executor, task)
            results.append((executor, score, matched_rules))
        
        # Сортируем по score (убывание)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Возвращаем лучшего
        if results and results[0][1] > 0:
            return results[0]
        
        return None
    
    def rank_executors(self, task: Dict, executors: List[Dict], top_n: int = None) -> List[Tuple[Dict, float, List[str]]]:
        """
        Ранжировать исполнителей по пригодности для заявки
        
        Args:
            task: Данные заявки
            executors: Список исполнителей
            top_n: Вернуть только топ N (или все если None)
            
        Returns:
            Список (executor, score, matched_rules) отсортированный по score
        """
        results = []
        
        for executor in executors:
            score, matched_rules = self.calculate_score(executor, task)
            if score > 0:  # Только с положительным score
                results.append((executor, score, matched_rules))
        
        # Сортируем по score (убывание)
        results.sort(key=lambda x: x[1], reverse=True)
        
        if top_n:
            return results[:top_n]
        
        return results


def load_rules_from_file(filepath: str) -> RuleEngine:
    """
    Загрузить правила из JSON файла
    
    Args:
        filepath: Путь к файлу с правилами
        
    Returns:
        Инициализированный RuleEngine
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return RuleEngine(config)


def load_rules_from_string(json_string: str) -> RuleEngine:
    """
    Загрузить правила из JSON строки
    
    Args:
        json_string: JSON строка с конфигурацией
        
    Returns:
        Инициализированный RuleEngine
    """
    config = json.loads(json_string)
    return RuleEngine(config)

