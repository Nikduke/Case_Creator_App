from __future__ import annotations

from dataclasses import dataclass

from openpyxl.worksheet.worksheet import Worksheet

from case_builder_app.models import Project
from case_builder_app.services.equipment import sort_equipment_names, voltage_token
from case_builder_app.services.export_ordering import (
    excel_numeric_value,
    group_equipment_by_voltage,
    group_position,
)
from case_builder_app.services.generator import GeneratedCase


@dataclass(frozen=True)
class ExportRow:
    values: list[object]
    style_kind: str
    position: str = "middle"
    voltage: str = ""
    range_key: str = ""
    clear_fill: bool = False
    force_black_font: bool = False


def build_comp_stat_rows(
    case_names: list[str],
    generated_cases: list[GeneratedCase],
    breaker_keys: list[str],
    include_fault: bool,
    parameter_keys: list[tuple[str, str]],
) -> list[ExportRow]:
    rows = [
        ExportRow(["Breaker_Status"], "section", clear_fill=True),
        ExportRow(["Definition", "Breaker", *case_names], "header_main"),
    ]

    for voltage, names in group_equipment_by_voltage(breaker_keys):
        for item_index, cb_name in enumerate(names):
            values: list[object] = [cb_name, "CB"]
            values.extend(case.cb_states.get(cb_name, "") for case in generated_cases)
            rows.append(
                ExportRow(
                    values,
                    "cb",
                    position=group_position(item_index, len(names)),
                    voltage=voltage,
                    range_key="cb",
                )
            )

    if include_fault:
        rows.append(ExportRow(["Fault_level"], "section"))
        for item_index, field_name in enumerate(("Rpos", "Xpos", "Rzero", "Xzero")):
            values = ["Main", "Script_FL"]
            values.extend(excel_numeric_value(case.fault_level.get(field_name, "")) for case in generated_cases)
            rows.append(ExportRow(values, "fault", position=group_position(item_index, 4)))

    rows.append(ExportRow(["Constants"], "section"))
    for definition, parameter in parameter_keys:
        style_kind = "constant_main" if definition.casefold() == "main" else "constant_other"
        values = [definition, parameter]
        values.extend(excel_numeric_value(case.parameters.get((definition, parameter), "")) for case in generated_cases)
        rows.append(ExportRow(values, style_kind, range_key="constants"))

    return rows


def build_layer_stat_rows(
    case_names: list[str],
    generated_cases: list[GeneratedCase],
    layer_keys: list[tuple[str, str, str]],
) -> list[ExportRow]:
    rows = [
        ExportRow(["Layers"], "section", clear_fill=True),
        ExportRow(["Layer", "String", *case_names], "header_main"),
    ]

    layer_rows = [item for item in layer_keys if item[0] == "Layers"]
    for item_index, (section, layer_type, target) in enumerate(layer_rows):
        values = [layer_type, target]
        values.extend(case.layer_changes.get((section, layer_type, target), "") for case in generated_cases)
        rows.append(ExportRow(values, "layer", position=group_position(item_index, len(layer_rows)), range_key="layer"))

    rows.append(ExportRow(["Sweep_Components"], "section", clear_fill=True))
    sweep_rows = [item for item in layer_keys if item[0] == "Sweep_Components"]
    for item_index, (section, layer_type, target) in enumerate(sweep_rows):
        values = [layer_type, target]
        values.extend(case.layer_changes.get((section, layer_type, target), "") for case in generated_cases)
        rows.append(ExportRow(values, "layer", position=group_position(item_index, len(sweep_rows)), range_key="sweep"))

    return rows


def build_res_flux_rows(
    case_names: list[str],
    generated_cases: list[GeneratedCase],
    flux_keys: list[tuple[str, str]],
) -> list[ExportRow]:
    rows = [
        ExportRow(["R_flux"], "section"),
        ExportRow(["Layer", "Trf", *case_names], "header_main"),
    ]

    for item_index, (layer, transformer) in enumerate(flux_keys):
        values = [layer, transformer]
        values.extend(case.flux_changes.get((layer, transformer), "") for case in generated_cases)
        rows.append(ExportRow(values, "flux", position=group_position(item_index, len(flux_keys))))

    return rows


def build_mm_blocks_rows(project: Project) -> list[ExportRow]:
    rows = [
        ExportRow(["Group", "Un", "Um", "SDPF_LG", "SDPF_LL", "SIWL_LG", "SIWL_LL", "LIWL"], "header_mm"),
    ]
    limits_by_voltage = {item.voltage.strip(): item for item in project.mm_blocks.limits_by_voltage if item.voltage.strip()}

    for voltage, elements in group_equipment_by_voltage(sort_equipment_names(project.mm_blocks.elements)):
        limit = limits_by_voltage.get(voltage)
        for item_index, element in enumerate(elements):
            values: list[object] = [element]
            if limit is None:
                values.extend([""] * 7)
            else:
                values.extend(
                    excel_numeric_value(value)
                    for value in (
                        limit.un,
                        limit.um,
                        limit.sdpf_lg,
                        limit.sdpf_ll,
                        limit.siwl_lg,
                        limit.siwl_ll,
                        limit.liwl,
                    )
                )
            rows.append(
                ExportRow(
                    values,
                    "mm",
                    position=group_position(item_index, len(elements)),
                    voltage=voltage_token(element),
                    force_black_font=True,
                )
            )

    return rows


def write_simple_rows(sheet: Worksheet, rows: list[ExportRow]) -> None:
    for row_index, row in enumerate(rows, start=1):
        for column, value in enumerate(row.values, start=1):
            sheet.cell(row_index, column).value = value
