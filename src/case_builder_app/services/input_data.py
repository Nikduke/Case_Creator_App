from __future__ import annotations

from openpyxl.worksheet.worksheet import Worksheet

from case_builder_app.models import (
    INPUT_DATA_FAULT,
    INPUT_DATA_FREQUENCY_SWEEP,
    INPUT_DATA_SWITCHING,
    InputDataSettings,
    Project,
)


def apply_input_data_settings(sheet: Worksheet, project: Project) -> None:
    for cell_ref, value in input_data_cell_values(project).items():
        sheet[cell_ref] = value


def input_data_cached_formula_values(project: Project) -> dict[str, object]:
    settings = project.settings.input_data
    timing = input_data_timing_values(settings)
    return {
        "B40": timing["increment"],
        "B41": timing["fault_end"],
        "B45": timing["increment"],
        "B46": timing["switch_stop"],
    }


def input_data_cell_values(project: Project) -> dict[str, object]:
    settings = project.settings.input_data
    studies = set(settings.normalized_studies())
    is_frequency_sweep = INPUT_DATA_FREQUENCY_SWEEP in studies
    is_switching = INPUT_DATA_SWITCHING in studies
    is_fault = INPUT_DATA_FAULT in studies
    switch_type = "Sequential" if is_switching and is_fault else settings.switch_type
    points_over_wave = _positive_int(settings.points_over_wave, 20)
    fault_points_to_check = _positive_int(
        settings.switch_points_to_check if is_switching and is_fault and switch_type == "Sequential" else settings.fault_points_to_check,
        9,
    )
    switch_points_to_check = _positive_int(settings.switch_points_to_check, 19)

    return {
        "B2": "No",
        "B3": "Yes" if is_frequency_sweep else "No",
        "B4": settings.switch_operation if is_switching else "On",
        "B5": switch_type if is_switching else ("Sequential" if is_frequency_sweep else "None"),
        "B6": "Yes" if is_fault else "No",
        "B7": "Yes" if settings.uses_residual_flux() else "No",
        "B10": settings.folders,
        "B11": settings.libraries,
        "B12": settings.files_inside_cases,
        "B13": settings.files_in_case_folder,
        "B16": _excel_value(settings.frequency),
        "B17": _excel_value(settings.initialisation_duration),
        "B18": _excel_value(settings.time_step),
        "B19": _excel_value(settings.plot_step),
        "B20": settings.create_cases,
        "B21": settings.take_snapshot,
        "B22": settings.adjust_names,
        "B23": _excel_value(settings.snapshot_time),
        "B24": "Yes" if is_frequency_sweep else "No",
        "B25": settings.mpe_workspace,
        "B26": settings.client_workspace if is_frequency_sweep else None,
        "B27": settings.pscad_version,
        "B28": settings.fortran_compiler,
        "B29": _excel_value(settings.parallel_simulations),
        "B30": _excel_value(settings.pscad_instances),
        "B33": settings.auto_ctrl if is_frequency_sweep else None,
        "B36": _excel_value(settings.final_duration),
        "B39": _excel_value(settings.fault_start),
        "B40": f"=1/(B16*{points_over_wave})",
        "B41": f"=B39+{fault_points_to_check}*B40",
        "B44": _excel_value(settings.switch_start),
        "B45": f"=1/(B16*{points_over_wave})",
        "B46": f"=B44+{switch_points_to_check}*B45",
        "B47": _excel_value(settings.second_switch_delay),
        "B50": _excel_value(settings.n1r),
        "B51": _excel_value(settings.n2r),
        "B52": _excel_value(settings.n3r),
        "B53": _excel_value(settings.min1r),
        "B54": _excel_value(settings.max1r),
        "B55": _excel_value(settings.min2r),
        "B56": _excel_value(settings.max2r),
        "B57": _excel_value(settings.min3r),
        "B58": _excel_value(settings.max3r),
        "B61": _excel_value(settings.min_frequency),
        "B62": _excel_value(settings.max_frequency),
        "B63": _excel_value(settings.frequency_increment),
        "B64": _excel_value(settings.increment_type),
        "B65": _excel_value(settings.z_output_type),
        "B66": _excel_value(settings.frequency_units),
        "B67": _excel_value(settings.impedance_output_units),
        "B70": _excel_value(settings.number_of_cores),
    }


def input_data_timing_values(settings: InputDataSettings) -> dict[str, float]:
    studies = set(settings.normalized_studies())
    switch_type = "Sequential" if INPUT_DATA_SWITCHING in studies and INPUT_DATA_FAULT in studies else settings.switch_type
    points_over_wave = _positive_int(settings.points_over_wave, 20)
    frequency = _positive_float(settings.frequency, 60.0)
    increment = 1.0 / (frequency * points_over_wave)
    fault_points_to_check = _positive_int(
        settings.switch_points_to_check
        if INPUT_DATA_SWITCHING in studies and INPUT_DATA_FAULT in studies and switch_type == "Sequential"
        else settings.fault_points_to_check,
        9,
    )
    switch_points_to_check = _positive_int(settings.switch_points_to_check, 19)
    fault_start = _safe_float(settings.fault_start, 2.1)
    switch_start = _safe_float(settings.switch_start, 2.1)
    return {
        "increment": increment,
        "fault_end": fault_start + fault_points_to_check * increment,
        "switch_stop": switch_start + switch_points_to_check * increment,
    }


def _excel_value(raw: str) -> object:
    value = str(raw).strip()
    if not value:
        return None
    if value.startswith("="):
        return value
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer() and "." not in value:
        return int(number)
    return number


def _positive_int(raw: str, fallback: int) -> int:
    try:
        value = int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return fallback
    return value if value > 0 else fallback


def _positive_float(raw: str, fallback: float) -> float:
    value = _safe_float(raw, fallback)
    return value if value > 0 else fallback


def _safe_float(raw: str, fallback: float) -> float:
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return fallback
