from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal, InvalidOperation
from typing import Callable, TypeVar

from case_builder_app.models import Project, ValueChanges
from case_builder_app.services.equipment import sort_equipment_names, voltage_token
from case_builder_app.services.generator import GeneratedCase


T = TypeVar("T")


def ordered_breaker_keys(project: Project, generated_cases: list[GeneratedCase]) -> list[str]:
    ordered = ordered_used_keys(
        project=project,
        used={key for case in generated_cases for key in case.cb_states},
        key_for_changes=lambda changes: [item.strip() for item in changes.cb.off + changes.cb.switch + changes.cb.on],
    )
    return sort_equipment_names(ordered)


def ordered_parameter_keys(project: Project, generated_cases: list[GeneratedCase]) -> list[tuple[str, str]]:
    ordered = ordered_used_keys(
        project=project,
        used={key for case in generated_cases for key in case.parameters},
        key_for_changes=lambda changes: [(item.definition.strip(), item.parameter.strip()) for item in changes.parameters],
    )
    return sorted(
        ordered,
        key=lambda item: (
            0 if item[0].casefold() == "main" else 1,
            item[0].casefold(),
        ),
    )


def ordered_layer_keys(project: Project, generated_cases: list[GeneratedCase]) -> list[tuple[str, str, str]]:
    ordered = ordered_used_keys(
        project=project,
        used={key for case in generated_cases for key in case.layer_changes},
        key_for_changes=lambda changes: [
            (item.section.strip(), item.layer_type.strip(), item.target.strip())
            for item in changes.layers
        ],
    )
    layer_type_order = {"extra": 0, "main": 1}
    return sorted(
        ordered,
        key=lambda item: (
            item[0].casefold(),
            layer_type_order.get(item[1].casefold(), 99),
            item[1].casefold(),
            item[2].casefold(),
        ),
    )


def ordered_flux_keys(project: Project, generated_cases: list[GeneratedCase]) -> list[tuple[str, str]]:
    return ordered_used_keys(
        project=project,
        used={key for case in generated_cases for key in case.flux_changes},
        key_for_changes=lambda changes: [(item.layer.strip(), item.transformer.strip()) for item in changes.flux],
    )


def ordered_used_keys(
    *,
    project: Project,
    used: set[T],
    key_for_changes: Callable[[ValueChanges], list[T]],
) -> list[T]:
    ordered: OrderedDict[T, None] = OrderedDict()
    for key in key_for_changes(project.base_case.changes):
        if key in used and key not in ordered:
            ordered[key] = None
    for case_part in project.case_parts:
        for value in case_part.values:
            for key in key_for_changes(value.changes):
                if key in used and key not in ordered:
                    ordered[key] = None
    for rule in project.conditional_rules:
        for key in key_for_changes(rule.changes):
            if key in used and key not in ordered:
                ordered[key] = None
    return list(ordered.keys())


def group_equipment_by_voltage(names: list[str]) -> list[tuple[str, list[str]]]:
    groups: OrderedDict[str, list[str]] = OrderedDict()
    for name in names:
        groups.setdefault(voltage_token(name), []).append(name)
    return list(groups.items())


def group_position(index: int, total: int) -> str:
    if total <= 1:
        return "single"
    if index == 0:
        return "top"
    if index == total - 1:
        return "bottom"
    return "middle"


def excel_numeric_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return ""
    try:
        numeric = Decimal(stripped)
    except InvalidOperation:
        return value
    if numeric == numeric.to_integral_value():
        return int(numeric)
    return float(numeric)
