import json
from typing import Dict, Any, List, Union
from decimal import Decimal

class RuleEngine:
    """JSON-DSL Rule Engine for task assignment logic"""
    
    def __init__(self):
        self.operators = {
            'eq': self._eq,
            'ne': self._ne,
            'gt': self._gt,
            'lt': self._lt,
            'gte': self._gte,
            'lte': self._lte,
            'in': self._in,
            'not_in': self._not_in,
            'contains': self._contains,
            'and': self._and,
            'or': self._or,
            'not': self._not
        }
    
    def evaluate(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate a single rule against context"""
        if not rule:
            return True
        
        operator = rule.get('operator')
        if not operator or operator not in self.operators:
            raise ValueError(f"Unknown operator: {operator}")
        
        return self.operators[operator](rule, context)
    
    def evaluate_rule_set(self, rules: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        """Evaluate a set of rules (AND logic by default)"""
        if not rules:
            return True
        
        for rule in rules:
            if not self.evaluate(rule, context):
                return False
        return True
    
    def calculate_weight(self, weight_rules: List[Dict[str, Any]], context: Dict[str, Any]) -> float:
        """Calculate weight based on rules"""
        total_weight = 1.0
        
        for rule in weight_rules:
            if self.evaluate(rule.get('condition', {}), context):
                weight_multiplier = rule.get('weight', 1.0)
                total_weight *= weight_multiplier
        
        return total_weight
    
    def _eq(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        field = rule['field']
        value = rule['value']
        context_value = self._get_nested_value(context, field)
        return context_value == value
    
    def _ne(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        field = rule['field']
        value = rule['value']
        context_value = self._get_nested_value(context, field)
        return context_value != value
    
    def _gt(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        field = rule['field']
        value = rule['value']
        context_value = self._get_nested_value(context, field)
        return float(context_value) > float(value)
    
    def _lt(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        field = rule['field']
        value = rule['value']
        context_value = self._get_nested_value(context, field)
        return float(context_value) < float(value)
    
    def _gte(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        field = rule['field']
        value = rule['value']
        context_value = self._get_nested_value(context, field)
        return float(context_value) >= float(value)
    
    def _lte(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        field = rule['field']
        value = rule['value']
        context_value = self._get_nested_value(context, field)
        return float(context_value) <= float(value)
    
    def _in(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        field = rule['field']
        values = rule['value']
        context_value = self._get_nested_value(context, field)
        return context_value in values
    
    def _not_in(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        field = rule['field']
        values = rule['value']
        context_value = self._get_nested_value(context, field)
        return context_value not in values
    
    def _contains(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        field = rule['field']
        value = rule['value']
        context_value = self._get_nested_value(context, field)
        if isinstance(context_value, (list, tuple)):
            return value in context_value
        elif isinstance(context_value, str):
            return value in context_value
        return False
    
    def _and(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        conditions = rule.get('conditions', [])
        for condition in conditions:
            if not self.evaluate(condition, context):
                return False
        return True
    
    def _or(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        conditions = rule.get('conditions', [])
        for condition in conditions:
            if self.evaluate(condition, context):
                return True
        return False
    
    def _not(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        condition = rule.get('condition', {})
        return not self.evaluate(condition, context)
    
    def _get_nested_value(self, context: Dict[str, Any], field: str) -> Any:
        """Get nested value from context using dot notation"""
        keys = field.split('.')
        value = context
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value

# Example rule configurations
EXAMPLE_RULES = {
    "priority_based": [
        {
            "operator": "eq",
            "field": "task.priority",
            "value": "high"
        }
    ],
    "skill_matching": [
        {
            "operator": "in",
            "field": "executor.skills",
            "value": ["python", "fastapi"]
        }
    ],
    "workload_balancing": [
        {
            "operator": "lt",
            "field": "executor.assigned_today",
            "value": 50
        }
    ],
    "weight_calculation": [
        {
            "condition": {
                "operator": "eq",
                "field": "task.priority",
                "value": "high"
            },
            "weight": 2.0
        },
        {
            "condition": {
                "operator": "lt",
                "field": "executor.assigned_today",
                "value": 20
            },
            "weight": 1.5
        }
    ]
}
