from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


def new_id() -> str:
    return uuid4().hex


def default_base_changes() -> "ValueChanges":
    return ValueChanges(
        use_cb=True,
        use_parameters=True,
        use_fault_level=True,
        use_layers=True,
        use_flux=True,
    )


def _payload_dict(payload: dict | None) -> dict:
    return payload or {}


def _payload_str(payload: dict, key: str, default: str = "") -> str:
    return str(payload.get(key, default))


def _payload_bool(payload: dict, key: str, default: bool = False) -> bool:
    return bool(payload.get(key, default))


def _payload_int(payload: dict, key: str, default: int = 0) -> int:
    try:
        return int(payload.get(key, default))
    except (TypeError, ValueError):
        return default


def _payload_list(payload: dict, key: str) -> list:
    value = payload.get(key, [])
    return value if isinstance(value, list) else []


INPUT_DATA_FREQUENCY_SWEEP = "frequency_sweep"
INPUT_DATA_SWITCHING = "switching"
INPUT_DATA_FAULT = "fault"
INPUT_DATA_STUDIES = {INPUT_DATA_FREQUENCY_SWEEP, INPUT_DATA_SWITCHING, INPUT_DATA_FAULT}
PROJECT_SCHEMA_VERSION = 2


def default_input_data_studies() -> list[str]:
    return [INPUT_DATA_FREQUENCY_SWEEP]


@dataclass
class InputDataSettings:
    studies: list[str] = field(default_factory=default_input_data_studies)
    folders: str = ""
    libraries: str = ""
    files_inside_cases: str = ""
    files_in_case_folder: str = ""
    frequency: str = "60"
    initialisation_duration: str = "2.01"
    time_step: str = "2"
    plot_step: str = "20"
    create_cases: str = "Yes"
    take_snapshot: str = "Yes"
    adjust_names: str = "Yes"
    snapshot_time: str = "2"
    mpe_workspace: str = "Formosa_IV.pswx"
    pscad_version: str = "5.0.2"
    fortran_compiler: str = "Intel 16.0.207"
    parallel_simulations: str = "4"
    pscad_instances: str = "4"
    final_duration: str = "1"
    residual_flux: str = "No"
    number_of_cores: str = "Auto"
    auto_ctrl: str = "ONT1_Tap, ONT2_Tap, OFT1_Tap, OFT2_Tap"
    client_workspace: str = "Formosa_IV_FS.pswx"
    min_frequency: str = "0"
    max_frequency: str = "360"
    frequency_increment: str = "1"
    increment_type: str = "0"
    z_output_type: str = "0"
    frequency_units: str = "0"
    impedance_output_units: str = "1"
    switch_operation: str = "On"
    switch_type: str = "Sequential"
    points_over_wave: str = "20"
    switch_start: str = "2.1000"
    switch_points_to_check: str = "19"
    second_switch_delay: str = "0.1000"
    n1r: str = "5"
    n2r: str = "5"
    n3r: str = "4"
    min1r: str = "2.050"
    max1r: str = "2.066667"
    min2r: str = "-0.003"
    max2r: str = "0.003"
    min3r: str = "-0.003"
    max3r: str = "0.003"
    fault_start: str = "2.1000"
    fault_points_to_check: str = "9"

    def normalized_studies(self) -> list[str]:
        studies = [study for study in self.studies if study in INPUT_DATA_STUDIES]
        if INPUT_DATA_FREQUENCY_SWEEP in studies:
            return [INPUT_DATA_FREQUENCY_SWEEP]
        if INPUT_DATA_SWITCHING in studies and INPUT_DATA_FAULT in studies:
            return [INPUT_DATA_SWITCHING, INPUT_DATA_FAULT]
        if INPUT_DATA_SWITCHING in studies:
            return [INPUT_DATA_SWITCHING]
        if INPUT_DATA_FAULT in studies:
            return [INPUT_DATA_FAULT]
        return default_input_data_studies()

    def uses_residual_flux(self) -> bool:
        return INPUT_DATA_SWITCHING in self.normalized_studies() and self.residual_flux.strip().casefold() == "yes"

    def to_dict(self) -> dict:
        return {
            "studies": self.normalized_studies(),
            "folders": self.folders,
            "libraries": self.libraries,
            "files_inside_cases": self.files_inside_cases,
            "files_in_case_folder": self.files_in_case_folder,
            "frequency": self.frequency,
            "initialisation_duration": self.initialisation_duration,
            "time_step": self.time_step,
            "plot_step": self.plot_step,
            "create_cases": self.create_cases,
            "take_snapshot": self.take_snapshot,
            "adjust_names": self.adjust_names,
            "snapshot_time": self.snapshot_time,
            "mpe_workspace": self.mpe_workspace,
            "pscad_version": self.pscad_version,
            "fortran_compiler": self.fortran_compiler,
            "parallel_simulations": self.parallel_simulations,
            "pscad_instances": self.pscad_instances,
            "final_duration": self.final_duration,
            "residual_flux": self.residual_flux,
            "number_of_cores": self.number_of_cores,
            "auto_ctrl": self.auto_ctrl,
            "client_workspace": self.client_workspace,
            "min_frequency": self.min_frequency,
            "max_frequency": self.max_frequency,
            "frequency_increment": self.frequency_increment,
            "increment_type": self.increment_type,
            "z_output_type": self.z_output_type,
            "frequency_units": self.frequency_units,
            "impedance_output_units": self.impedance_output_units,
            "switch_operation": self.switch_operation,
            "switch_type": self.switch_type,
            "points_over_wave": self.points_over_wave,
            "switch_start": self.switch_start,
            "switch_points_to_check": self.switch_points_to_check,
            "second_switch_delay": self.second_switch_delay,
            "n1r": self.n1r,
            "n2r": self.n2r,
            "n3r": self.n3r,
            "min1r": self.min1r,
            "max1r": self.max1r,
            "min2r": self.min2r,
            "max2r": self.max2r,
            "min3r": self.min3r,
            "max3r": self.max3r,
            "fault_start": self.fault_start,
            "fault_points_to_check": self.fault_points_to_check,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "InputDataSettings":
        payload = _payload_dict(payload)
        settings = cls(
            studies=[str(item) for item in _payload_list(payload, "studies")],
            folders=_payload_str(payload, "folders"),
            libraries=_payload_str(payload, "libraries"),
            files_inside_cases=_payload_str(payload, "files_inside_cases"),
            files_in_case_folder=_payload_str(payload, "files_in_case_folder"),
            frequency=_payload_str(payload, "frequency", "60"),
            initialisation_duration=_payload_str(payload, "initialisation_duration", "2.01"),
            time_step=_payload_str(payload, "time_step", "2"),
            plot_step=_payload_str(payload, "plot_step", "20"),
            create_cases=_payload_str(payload, "create_cases", "Yes"),
            take_snapshot=_payload_str(payload, "take_snapshot", "Yes"),
            adjust_names=_payload_str(payload, "adjust_names", "Yes"),
            snapshot_time=_payload_str(payload, "snapshot_time", "2"),
            mpe_workspace=_payload_str(payload, "mpe_workspace", "Formosa_IV.pswx"),
            pscad_version=_payload_str(payload, "pscad_version", "5.0.2"),
            fortran_compiler=_payload_str(payload, "fortran_compiler", "Intel 16.0.207"),
            parallel_simulations=_payload_str(payload, "parallel_simulations", "4"),
            pscad_instances=_payload_str(payload, "pscad_instances", "4"),
            final_duration=_payload_str(payload, "final_duration", "1"),
            residual_flux=_payload_str(payload, "residual_flux", "No"),
            number_of_cores=_payload_str(payload, "number_of_cores", "Auto"),
            auto_ctrl=_payload_str(payload, "auto_ctrl", "ONT1_Tap, ONT2_Tap, OFT1_Tap, OFT2_Tap"),
            client_workspace=_payload_str(payload, "client_workspace", "Formosa_IV_FS.pswx"),
            min_frequency=_payload_str(payload, "min_frequency", "0"),
            max_frequency=_payload_str(payload, "max_frequency", "360"),
            frequency_increment=_payload_str(payload, "frequency_increment", "1"),
            increment_type=_payload_str(payload, "increment_type", "0"),
            z_output_type=_payload_str(payload, "z_output_type", "0"),
            frequency_units=_payload_str(payload, "frequency_units", "0"),
            impedance_output_units=_payload_str(payload, "impedance_output_units", "1"),
            switch_operation=_payload_str(payload, "switch_operation", "On"),
            switch_type=_payload_str(payload, "switch_type", "Sequential"),
            points_over_wave=_payload_str(payload, "points_over_wave", "20"),
            switch_start=_payload_str(payload, "switch_start", "2.1000"),
            switch_points_to_check=_payload_str(payload, "switch_points_to_check", "19"),
            second_switch_delay=_payload_str(payload, "second_switch_delay", "0.1000"),
            n1r=_payload_str(payload, "n1r", "5"),
            n2r=_payload_str(payload, "n2r", "5"),
            n3r=_payload_str(payload, "n3r", "4"),
            min1r=_payload_str(payload, "min1r", "2.050"),
            max1r=_payload_str(payload, "max1r", "2.066667"),
            min2r=_payload_str(payload, "min2r", "-0.003"),
            max2r=_payload_str(payload, "max2r", "0.003"),
            min3r=_payload_str(payload, "min3r", "-0.003"),
            max3r=_payload_str(payload, "max3r", "0.003"),
            fault_start=_payload_str(payload, "fault_start", "2.1000"),
            fault_points_to_check=_payload_str(payload, "fault_points_to_check", "9"),
        )
        settings.studies = settings.normalized_studies()
        return settings


@dataclass
class ProjectSettings:
    simple_export_enabled: bool = False
    input_data: InputDataSettings = field(default_factory=InputDataSettings)
    case_name_order: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "simple_export_enabled": self.simple_export_enabled,
            "input_data": self.input_data.to_dict(),
            "case_name_order": list(self.case_name_order),
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "ProjectSettings":
        payload = _payload_dict(payload)
        input_data = InputDataSettings.from_dict(payload.get("input_data"))
        if (
            "residual_flux" not in _payload_dict(payload.get("input_data"))
            and _payload_bool(payload, "res_flux_enabled", False)
            and INPUT_DATA_SWITCHING in input_data.normalized_studies()
        ):
            input_data.residual_flux = "Yes"
        return cls(
            simple_export_enabled=_payload_bool(payload, "simple_export_enabled"),
            input_data=input_data,
            case_name_order=[str(item) for item in _payload_list(payload, "case_name_order") if str(item).strip()],
        )


@dataclass
class MMLimit:
    voltage: str = ""
    un: str = ""
    um: str = ""
    sdpf_lg: str = ""
    sdpf_ll: str = ""
    siwl_lg: str = ""
    siwl_ll: str = ""
    liwl: str = ""

    def is_complete(self) -> bool:
        return all(
            value.strip()
            for value in (
                self.voltage,
                self.un,
                self.um,
                self.sdpf_lg,
                self.sdpf_ll,
                self.siwl_lg,
                self.siwl_ll,
                self.liwl,
            )
        )

    def to_dict(self) -> dict:
        return {
            "voltage": self.voltage,
            "un": self.un,
            "um": self.um,
            "sdpf_lg": self.sdpf_lg,
            "sdpf_ll": self.sdpf_ll,
            "siwl_lg": self.siwl_lg,
            "siwl_ll": self.siwl_ll,
            "liwl": self.liwl,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "MMLimit":
        payload = _payload_dict(payload)
        return cls(
            voltage=_payload_str(payload, "voltage"),
            un=_payload_str(payload, "un"),
            um=_payload_str(payload, "um"),
            sdpf_lg=_payload_str(payload, "sdpf_lg"),
            sdpf_ll=_payload_str(payload, "sdpf_ll"),
            siwl_lg=_payload_str(payload, "siwl_lg"),
            siwl_ll=_payload_str(payload, "siwl_ll"),
            liwl=_payload_str(payload, "liwl"),
        )


@dataclass
class MMBlocks:
    elements: list[str] = field(default_factory=list)
    limits_by_voltage: list[MMLimit] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "elements": list(self.elements),
            "limits_by_voltage": [item.to_dict() for item in self.limits_by_voltage],
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "MMBlocks":
        payload = _payload_dict(payload)
        return cls(
            elements=[str(item) for item in _payload_list(payload, "elements")],
            limits_by_voltage=[MMLimit.from_dict(item) for item in _payload_list(payload, "limits_by_voltage")],
        )


@dataclass
class CBChanges:
    off: list[str] = field(default_factory=list)
    switch: list[str] = field(default_factory=list)
    on: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.off or self.switch or self.on)

    def to_dict(self) -> dict:
        return {
            "off": list(self.off),
            "switch": list(self.switch),
            "on": list(self.on),
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "CBChanges":
        payload = _payload_dict(payload)
        return cls(
            off=list(_payload_list(payload, "off")),
            switch=list(_payload_list(payload, "switch")),
            on=list(_payload_list(payload, "on")),
        )


@dataclass
class ParameterChange:
    id: str = field(default_factory=new_id)
    base_row_id: str = ""
    definition: str = ""
    parameter: str = ""
    value: str = ""

    def is_complete(self) -> bool:
        if self.base_row_id.strip():
            return bool(self.definition.strip() or self.parameter.strip() or self.value.strip())
        return bool(self.definition.strip() and self.parameter.strip() and self.value.strip())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "base_row_id": self.base_row_id,
            "definition": self.definition,
            "parameter": self.parameter,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "ParameterChange":
        payload = _payload_dict(payload)
        return cls(
            id=_payload_str(payload, "id", new_id()),
            base_row_id=_payload_str(payload, "base_row_id"),
            definition=_payload_str(payload, "definition"),
            parameter=_payload_str(payload, "parameter"),
            value=_payload_str(payload, "value"),
        )


@dataclass
class FaultLevelChange:
    rpos: str = ""
    xpos: str = ""
    rzero: str = ""
    xzero: str = ""

    def is_empty(self) -> bool:
        return not any((self.rpos.strip(), self.xpos.strip(), self.rzero.strip(), self.xzero.strip()))

    def is_complete(self) -> bool:
        return all((self.rpos.strip(), self.xpos.strip(), self.rzero.strip(), self.xzero.strip()))

    def to_dict(self) -> dict:
        return {
            "rpos": self.rpos,
            "xpos": self.xpos,
            "rzero": self.rzero,
            "xzero": self.xzero,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "FaultLevelChange":
        payload = _payload_dict(payload)
        return cls(
            rpos=_payload_str(payload, "rpos"),
            xpos=_payload_str(payload, "xpos"),
            rzero=_payload_str(payload, "rzero"),
            xzero=_payload_str(payload, "xzero"),
        )


@dataclass
class LayerChange:
    id: str = field(default_factory=new_id)
    base_row_id: str = ""
    section: str = "Layers"
    layer_type: str = "Extra"
    target: str = ""
    state: str = "Disable"

    def is_complete(self) -> bool:
        if self.base_row_id.strip():
            return bool(self.section.strip() or self.layer_type.strip() or self.target.strip() or self.state.strip())
        return bool(self.section.strip() and self.layer_type.strip() and self.target.strip() and self.state.strip())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "base_row_id": self.base_row_id,
            "section": self.section,
            "layer_type": self.layer_type,
            "target": self.target,
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "LayerChange":
        payload = _payload_dict(payload)
        return cls(
            id=_payload_str(payload, "id", new_id()),
            base_row_id=_payload_str(payload, "base_row_id"),
            section=_payload_str(payload, "section", "Layers"),
            layer_type=_payload_str(payload, "layer_type", "Extra"),
            target=_payload_str(payload, "target"),
            state=_payload_str(payload, "state", "Disable"),
        )


@dataclass
class FluxChange:
    id: str = field(default_factory=new_id)
    base_row_id: str = ""
    layer: str = "Main"
    transformer: str = ""
    value: str = ""

    def is_complete(self) -> bool:
        if self.base_row_id.strip():
            return bool(self.layer.strip() or self.transformer.strip() or self.value.strip())
        return bool(self.layer.strip() and self.transformer.strip() and self.value.strip())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "base_row_id": self.base_row_id,
            "layer": self.layer,
            "transformer": self.transformer,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "FluxChange":
        payload = _payload_dict(payload)
        return cls(
            id=_payload_str(payload, "id", new_id()),
            base_row_id=_payload_str(payload, "base_row_id"),
            layer=_payload_str(payload, "layer", "Main"),
            transformer=_payload_str(payload, "transformer"),
            value=_payload_str(payload, "value"),
        )


@dataclass
class ValueChanges:
    use_cb: bool = False
    use_parameters: bool = False
    use_fault_level: bool = False
    use_layers: bool = False
    use_flux: bool = False
    cb: CBChanges = field(default_factory=CBChanges)
    parameters: list[ParameterChange] = field(default_factory=list)
    fault_level: FaultLevelChange = field(default_factory=FaultLevelChange)
    layers: list[LayerChange] = field(default_factory=list)
    flux: list[FluxChange] = field(default_factory=list)

    def is_empty(self) -> bool:
        return (
            not (self.use_cb and not self.cb.is_empty())
            and not (self.use_parameters and bool(self.parameters))
            and not (self.use_fault_level and not self.fault_level.is_empty())
            and not (self.use_layers and bool(self.layers))
            and not (self.use_flux and bool(self.flux))
        )

    def to_dict(self) -> dict:
        return {
            "use_cb": self.use_cb,
            "use_parameters": self.use_parameters,
            "use_fault_level": self.use_fault_level,
            "use_layers": self.use_layers,
            "use_flux": self.use_flux,
            "cb": self.cb.to_dict(),
            "parameters": [item.to_dict() for item in self.parameters],
            "fault_level": self.fault_level.to_dict(),
            "layers": [item.to_dict() for item in self.layers],
            "flux": [item.to_dict() for item in self.flux],
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "ValueChanges":
        payload = _payload_dict(payload)
        cb = CBChanges.from_dict(payload.get("cb"))
        parameters = [ParameterChange.from_dict(item) for item in _payload_list(payload, "parameters")]
        fault_level = FaultLevelChange.from_dict(payload.get("fault_level"))
        layers = [LayerChange.from_dict(item) for item in _payload_list(payload, "layers")]
        flux = [FluxChange.from_dict(item) for item in _payload_list(payload, "flux")]
        return cls(
            use_cb=_payload_bool(payload, "use_cb", not cb.is_empty()),
            use_parameters=_payload_bool(payload, "use_parameters", bool(parameters)),
            use_fault_level=_payload_bool(payload, "use_fault_level", not fault_level.is_empty()),
            use_layers=_payload_bool(payload, "use_layers", bool(layers)),
            use_flux=_payload_bool(payload, "use_flux", bool(flux)),
            cb=cb,
            parameters=parameters,
            fault_level=fault_level,
            layers=layers,
            flux=flux,
        )


@dataclass
class CaseValue:
    token: str
    id: str = field(default_factory=new_id)
    changes: ValueChanges = field(default_factory=ValueChanges)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "token": self.token,
            "changes": self.changes.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "CaseValue":
        payload = _payload_dict(payload)
        return cls(
            id=_payload_str(payload, "id", new_id()),
            token=_payload_str(payload, "token"),
            changes=ValueChanges.from_dict(payload.get("changes")),
        )


@dataclass
class CasePart:
    label: str
    id: str = field(default_factory=new_id)
    values: list[CaseValue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "values": [item.to_dict() for item in self.values],
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "CasePart":
        payload = _payload_dict(payload)
        return cls(
            id=_payload_str(payload, "id", new_id()),
            label=_payload_str(payload, "label"),
            values=[CaseValue.from_dict(item) for item in _payload_list(payload, "values")],
        )


@dataclass
class RuleClause:
    case_part_id: str = ""
    value_id: str = ""

    def is_complete(self) -> bool:
        return bool(self.case_part_id and self.value_id)

    def to_dict(self) -> dict:
        return {
            "case_part_id": self.case_part_id,
            "value_id": self.value_id,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "RuleClause":
        payload = _payload_dict(payload)
        return cls(
            case_part_id=_payload_str(payload, "case_part_id"),
            value_id=_payload_str(payload, "value_id"),
        )


@dataclass
class ExclusionCombination:
    id: str = field(default_factory=new_id)
    clauses: list[RuleClause] = field(default_factory=list)

    def is_complete(self) -> bool:
        return bool(self.clauses) and all(clause.is_complete() for clause in self.clauses)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "clauses": [item.to_dict() for item in self.clauses],
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "ExclusionCombination":
        payload = _payload_dict(payload)
        return cls(
            id=_payload_str(payload, "id", new_id()),
            clauses=[RuleClause.from_dict(item) for item in _payload_list(payload, "clauses")],
        )


@dataclass
class SelectedCaseList:
    name: str = ""
    case_names: list[str] = field(default_factory=list)
    id: str = field(default_factory=new_id)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "case_names": list(self.case_names),
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "SelectedCaseList":
        payload = _payload_dict(payload)
        return cls(
            id=_payload_str(payload, "id", new_id()),
            name=_payload_str(payload, "name"),
            case_names=[str(item).strip() for item in _payload_list(payload, "case_names") if str(item).strip()],
        )


@dataclass
class ConditionalRule:
    name: str = ""
    match_mode: str = "ALL"
    priority: int = 100
    id: str = field(default_factory=new_id)
    clauses: list[RuleClause] = field(default_factory=list)
    changes: ValueChanges = field(default_factory=ValueChanges)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "match_mode": self.match_mode,
            "priority": self.priority,
            "clauses": [item.to_dict() for item in self.clauses],
            "changes": self.changes.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "ConditionalRule":
        payload = _payload_dict(payload)
        return cls(
            id=_payload_str(payload, "id", new_id()),
            name=_payload_str(payload, "name"),
            match_mode=_payload_str(payload, "match_mode", "ALL"),
            priority=_payload_int(payload, "priority", 100),
            clauses=[RuleClause.from_dict(item) for item in _payload_list(payload, "clauses")],
            changes=ValueChanges.from_dict(payload.get("changes")),
        )


@dataclass
class BaseCase:
    label: str = "Base Case"
    token: str = "BC"
    include_in_case_name: bool = False
    changes: ValueChanges = field(default_factory=default_base_changes)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "token": self.token,
            "include_in_case_name": self.include_in_case_name,
            "changes": self.changes.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "BaseCase":
        payload = _payload_dict(payload)
        changes = ValueChanges.from_dict(payload.get("changes"))
        if "changes" not in payload:
            changes = default_base_changes()
        return cls(
            label=_payload_str(payload, "label", "Base Case"),
            token=_payload_str(payload, "token", "BC"),
            include_in_case_name=_payload_bool(payload, "include_in_case_name"),
            changes=changes,
        )


@dataclass
class Project:
    name: str = "Untitled Project"
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    mm_blocks: MMBlocks = field(default_factory=MMBlocks)
    base_case: BaseCase = field(default_factory=BaseCase)
    case_parts: list[CasePart] = field(default_factory=list)
    conditional_rules: list[ConditionalRule] = field(default_factory=list)
    exclusions: list[ExclusionCombination] = field(default_factory=list)
    selected_case_lists: list[SelectedCaseList] = field(default_factory=list)
    schema_version: int = PROJECT_SCHEMA_VERSION

    def to_dict(self) -> dict:
        settings = self.settings.to_dict()
        settings["case_name_order"] = self.stored_case_name_order_ids()
        return {
            "schema_version": PROJECT_SCHEMA_VERSION,
            "name": self.name,
            "settings": settings,
            "mm_blocks": self.mm_blocks.to_dict(),
            "base_case": self.base_case.to_dict(),
            "case_parts": [item.to_dict() for item in self.case_parts],
            "conditional_rules": [item.to_dict() for item in self.conditional_rules],
            "exclusions": [item.to_dict() for item in self.exclusions],
            "selected_case_lists": [item.to_dict() for item in self.selected_case_lists],
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "Project":
        payload = _payload_dict(payload)
        project = cls(
            schema_version=_payload_int(payload, "schema_version", 1),
            name=_payload_str(payload, "name", "Untitled Project"),
            settings=ProjectSettings.from_dict(payload.get("settings")),
            mm_blocks=MMBlocks.from_dict(payload.get("mm_blocks")),
            base_case=BaseCase.from_dict(payload.get("base_case")),
            case_parts=[CasePart.from_dict(item) for item in _payload_list(payload, "case_parts")],
            conditional_rules=[ConditionalRule.from_dict(item) for item in _payload_list(payload, "conditional_rules")],
            exclusions=[ExclusionCombination.from_dict(item) for item in _payload_list(payload, "exclusions")],
            selected_case_lists=[SelectedCaseList.from_dict(item) for item in _payload_list(payload, "selected_case_lists")],
        )
        if project.schema_version < PROJECT_SCHEMA_VERSION:
            _prune_legacy_same_as_base_cb_overrides(project)
        return project

    def find_case_part(self, case_part_id: str) -> CasePart | None:
        for case_part in self.case_parts:
            if case_part.id == case_part_id:
                return case_part
        return None

    def case_parts_in_name_order(self) -> list[CasePart]:
        current_ids = [case_part.id for case_part in self.case_parts]
        if not self.settings.case_name_order:
            return list(self.case_parts)

        by_id = {case_part.id: case_part for case_part in self.case_parts}
        ordered_ids = [case_part_id for case_part_id in self.settings.case_name_order if case_part_id in by_id]
        ordered_ids.extend(case_part_id for case_part_id in current_ids if case_part_id not in ordered_ids)
        return [by_id[case_part_id] for case_part_id in ordered_ids]

    def stored_case_name_order_ids(self) -> list[str]:
        current_ids = [case_part.id for case_part in self.case_parts]
        ordered_ids = [case_part.id for case_part in self.case_parts_in_name_order()]
        return [] if ordered_ids == current_ids else ordered_ids

    def find_value(self, case_part_id: str, value_id: str) -> CaseValue | None:
        case_part = self.find_case_part(case_part_id)
        if case_part is None:
            return None
        for value in case_part.values:
            if value.id == value_id:
                return value
        return None


def _prune_legacy_same_as_base_cb_overrides(project: Project) -> None:
    """Pre-v2 UI stored same-as-base CB chips locally while showing them inherited."""
    base_state = cb_state_map(project.base_case.changes.cb)
    if not base_state:
        return

    for case_part in project.case_parts:
        for value in case_part.values:
            _remove_same_as_base_tokens(value.changes.cb, base_state)


def cb_state_map(changes: CBChanges) -> dict[str, str]:
    state_by_token: dict[str, str] = {}
    for state_key, tokens in (("off", changes.off), ("switch", changes.switch), ("on", changes.on)):
        for token in tokens:
            normalized = str(token).strip()
            if normalized:
                state_by_token[normalized] = state_key
    return state_by_token


def _remove_same_as_base_tokens(changes: CBChanges, base_state: dict[str, str]) -> None:
    for state_key, attr_name in (("off", "off"), ("switch", "switch"), ("on", "on")):
        tokens = getattr(changes, attr_name)
        setattr(
            changes,
            attr_name,
            [token for token in tokens if base_state.get(str(token).strip()) != state_key],
        )
