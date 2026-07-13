from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re


_NATURAL_PART_RE = re.compile(r"(\d+)")


def voltage_token(name: str) -> str:
    parts = [part.strip() for part in name.strip().split("_")]
    if len(parts) < 2:
        return ""

    for part in parts[1:]:
        if _decimal_value(part) is not None:
            return part
    return parts[1]


def numeric_voltage_token(name: str) -> str:
    token = voltage_token(name)
    if _decimal_value(token) is None:
        return ""
    return token


def equipment_sort_key(name_or_voltage: str) -> tuple[int, Decimal, tuple[tuple[int, object], ...]]:
    token = voltage_token(name_or_voltage)
    if not token and name_or_voltage.strip():
        token = name_or_voltage.strip()

    numeric = _decimal_value(token)
    if numeric is None:
        return (1, Decimal("0"), natural_name_key(name_or_voltage))
    return (0, -numeric, natural_name_key(name_or_voltage))


def voltage_sort_key(name_or_voltage: str) -> tuple[int, Decimal, tuple[tuple[int, object], ...]]:
    return equipment_sort_key(name_or_voltage)


def sort_equipment_names(names: list[str]) -> list[str]:
    return sorted((name.strip() for name in names if name.strip()), key=equipment_sort_key)


def sort_voltage_tokens(tokens: list[str]) -> list[str]:
    return sorted((token.strip() for token in tokens if token.strip()), key=equipment_sort_key)


def natural_name_key(name: str) -> tuple[tuple[int, object], ...]:
    parts: list[tuple[int, object]] = []
    for part in _NATURAL_PART_RE.split(name.strip().casefold()):
        if not part:
            continue
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part))
    return tuple(parts)


def _decimal_value(value: str) -> Decimal | None:
    try:
        return Decimal(value.strip())
    except (InvalidOperation, ValueError):
        return None
