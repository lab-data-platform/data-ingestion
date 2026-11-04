"""Regras de qualidade declaradas no contrato ODCS.

Suportadas hoje (subconjunto do ODCS, ampliado conforme as fontes precisarem):
- `required: true` numa propriedade do schema: a coluna existe e não é nula em nenhum registro;
- `quality` do tipo `library` com `metric: rowCount` e um operador
  (`mustBe`, `mustBeGreaterThan`, `mustBeGreaterOrEqualTo`, `mustBeLessThan`, `mustBeLessOrEqualTo`).
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from typing import Any

OPERATORS: dict[str, tuple[Callable[[Any, Any], bool], str]] = {
    "mustBe": (operator.eq, "="),
    "mustBeGreaterThan": (operator.gt, ">"),
    "mustBeGreaterOrEqualTo": (operator.ge, ">="),
    "mustBeLessThan": (operator.lt, "<"),
    "mustBeLessOrEqualTo": (operator.le, "<="),
}


def check_required(records: list[dict[str, Any]], schema: tuple[dict[str, Any], ...]) -> list[str]:
    reasons = []
    for prop in schema:
        if not prop.get("required"):
            continue
        name = prop["name"]
        missing = sum(1 for r in records if r.get(name) in (None, ""))
        if missing:
            reasons.append(f"coluna obrigatória '{name}' vazia ou ausente em {missing} registro(s)")
    return reasons


def check_library(records: list[dict[str, Any]], rule: dict[str, Any]) -> list[str]:
    metric = rule.get("metric")
    if metric != "rowCount":
        return [f"regra de qualidade não suportada: metric={metric!r}"]
    value = len(records)
    for key, (compare, symbol) in OPERATORS.items():
        if key in rule and not compare(value, rule[key]):
            return [f"rowCount = {value}, esperado {symbol} {rule[key]}"]
    return []


def check_quality(records: list[dict[str, Any]], quality: tuple[dict[str, Any], ...]) -> list[str]:
    reasons = []
    for rule in quality:
        if rule.get("type", "library") == "library":
            reasons += check_library(records, rule)
        else:
            reasons.append(f"tipo de regra de qualidade não suportado: {rule.get('type')!r}")
    return reasons
