"""Classificação e criticidade dos dados (data-platform/docs/governanca.md, seção 2)."""

from enum import StrEnum


class Classification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PERSONAL = "personal"


class Criticality(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
