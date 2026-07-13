from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from math import prod

from case_builder_app.models import (
    CBChanges,
    ConditionalRule,
    ExclusionCombination,
    FluxChange,
    LayerChange,
    ParameterChange,
    Project,
    ValueChanges,
)


@dataclass
class GenerationStats:
    total_combinations: int = 0
    excluded_combinations: int = 0
    final_cases: int = 0


@dataclass
class ResolvedWrite:
    value: str
    source: str
    priority: int | None = None


@dataclass
class ResolvedRowWrite:
    row: object
    source: str
    priority: int | None = None


@dataclass
class GeneratedCase:
    name: str
    selected_value_ids: dict[str, str]
    cb_states: dict[str, str] = field(default_factory=dict)
    parameters: dict[tuple[str, str], str] = field(default_factory=dict)
    fault_level: dict[str, str] = field(default_factory=dict)
    layer_changes: dict[tuple[str, str, str], str] = field(default_factory=dict)
    flux_changes: dict[tuple[str, str], str] = field(default_factory=dict)


class GenerationError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


class GenerationService:
    def generate(self, project: Project) -> tuple[list[GeneratedCase], GenerationStats]:
        stats = GenerationStats()
        if not project.case_parts:
            return [], stats
        if any(not case_part.values for case_part in project.case_parts):
            return [], stats

        value_lists = [case_part.values for case_part in project.case_parts]
        stats.total_combinations = prod(len(values) for values in value_lists)
        ordered_rules = sorted(project.conditional_rules, key=lambda item: item.priority)
        res_flux_enabled = project.settings.input_data.uses_residual_flux()

        generated_cases: list[GeneratedCase] = []
        errors: list[str] = []
        seen_names: set[str] = set()

        for combo in product(*value_lists):
            selected_value_ids = {case_part.id: value.id for case_part, value in zip(project.case_parts, combo, strict=True)}
            if self._is_excluded(project.exclusions, selected_value_ids):
                stats.excluded_combinations += 1
                continue

            selected_values = {case_part.id: value for case_part, value in zip(project.case_parts, combo, strict=True)}
            combo_tokens = [
                selected_values[case_part.id].token
                for case_part in project.case_parts_in_name_order()
                if case_part.id in selected_values
            ]
            if project.base_case.include_in_case_name and project.base_case.token.strip():
                combo_tokens.insert(0, project.base_case.token.strip())
            case_name = "_".join(combo_tokens)
            if case_name in seen_names:
                errors.append(f"Duplicate generated case name: {case_name}")
                continue
            seen_names.add(case_name)

            cb_states: dict[str, ResolvedWrite] = {}
            parameter_rows: dict[str, ResolvedRowWrite] = {}
            parameters: dict[tuple[str, str], ResolvedWrite] = {}
            fault_level: dict[str, ResolvedWrite] = {}
            layer_rows: dict[str, ResolvedRowWrite] = {}
            layer_changes: dict[tuple[str, str, str], ResolvedWrite] = {}
            flux_rows: dict[str, ResolvedRowWrite] = {}
            flux_changes: dict[tuple[str, str], ResolvedWrite] = {}
            self._apply_changes(
                changes=project.base_case.changes,
                res_flux_enabled=res_flux_enabled,
                case_name=case_name,
                errors=errors,
                cb_states=cb_states,
                parameter_rows=parameter_rows,
                fault_level=fault_level,
                layer_rows=layer_rows,
                flux_rows=flux_rows,
                source="direct",
                priority=None,
            )

            for value in combo:
                self._apply_changes(
                    changes=value.changes,
                    res_flux_enabled=res_flux_enabled,
                    case_name=case_name,
                    errors=errors,
                    cb_states=cb_states,
                    parameter_rows=parameter_rows,
                    fault_level=fault_level,
                    layer_rows=layer_rows,
                    flux_rows=flux_rows,
                    source="direct",
                    priority=None,
                )

            for rule in ordered_rules:
                if self._rule_matches(rule, selected_value_ids):
                    self._apply_changes(
                        changes=rule.changes,
                        res_flux_enabled=res_flux_enabled,
                        case_name=case_name,
                        errors=errors,
                        cb_states=cb_states,
                        parameter_rows=parameter_rows,
                        fault_level=fault_level,
                        layer_rows=layer_rows,
                        flux_rows=flux_rows,
                        source="conditional",
                        priority=rule.priority,
                    )

            self._materialize_parameter_rows(parameter_rows, parameters, case_name, errors)
            self._materialize_layer_rows(layer_rows, layer_changes, case_name, errors)
            self._materialize_flux_rows(flux_rows, flux_changes, case_name, errors)

            if fault_level and any(field_name not in fault_level for field_name in ("Rpos", "Xpos", "Rzero", "Xzero")):
                errors.append(f"Incomplete resolved fault-level values for case '{case_name}'.")
                continue

            generated_cases.append(
                GeneratedCase(
                    name=case_name,
                    selected_value_ids=selected_value_ids,
                    cb_states={key: item.value for key, item in cb_states.items()},
                    parameters={key: item.value for key, item in parameters.items()},
                    fault_level={key: item.value for key, item in fault_level.items()},
                    layer_changes={key: item.value for key, item in layer_changes.items()},
                    flux_changes={key: item.value for key, item in flux_changes.items()},
                )
            )

        if errors:
            raise GenerationError(errors)

        stats.final_cases = len(generated_cases)
        return generated_cases, stats

    def _is_excluded(self, exclusions: list[ExclusionCombination], selected_value_ids: dict[str, str]) -> bool:
        for combination in exclusions:
            if combination.clauses and all(selected_value_ids.get(clause.case_part_id) == clause.value_id for clause in combination.clauses):
                return True
        return False

    def _rule_matches(self, rule: ConditionalRule, selected_value_ids: dict[str, str]) -> bool:
        matches = [selected_value_ids.get(clause.case_part_id) == clause.value_id for clause in rule.clauses]
        if not matches:
            return False
        if rule.match_mode == "ANY":
            return any(matches)
        return all(matches)

    def _apply_changes(
        self,
        *,
        changes: ValueChanges,
        res_flux_enabled: bool,
        case_name: str,
        errors: list[str],
        cb_states: dict[str, ResolvedWrite],
        parameter_rows: dict[str, ResolvedRowWrite],
        fault_level: dict[str, ResolvedWrite],
        layer_rows: dict[str, ResolvedRowWrite],
        flux_rows: dict[str, ResolvedRowWrite],
        source: str,
        priority: int | None,
    ) -> None:
        if changes.use_cb:
            self._apply_cb_changes(changes.cb, case_name, errors, cb_states, source, priority)

        if changes.use_parameters:
            for item in changes.parameters:
                self._set_row(parameter_rows, self._row_identity(item, (item.definition.strip(), item.parameter.strip())), item, case_name, errors, source, priority)

        if changes.use_fault_level and not changes.fault_level.is_empty():
            for key, value in {
                "Rpos": changes.fault_level.rpos.strip(),
                "Xpos": changes.fault_level.xpos.strip(),
                "Rzero": changes.fault_level.rzero.strip(),
                "Xzero": changes.fault_level.xzero.strip(),
            }.items():
                self._set_value(fault_level, key, value, case_name, errors, source, priority)

        if changes.use_layers:
            for item in changes.layers:
                self._set_row(
                    layer_rows,
                    self._row_identity(item, (item.section.strip(), item.layer_type.strip(), item.target.strip())),
                    item,
                    case_name,
                    errors,
                    source,
                    priority,
                )

        if changes.use_flux and res_flux_enabled:
            for item in changes.flux:
                self._set_row(flux_rows, self._row_identity(item, (item.layer.strip(), item.transformer.strip())), item, case_name, errors, source, priority)

    def _apply_cb_changes(
        self,
        cb_changes: CBChanges,
        case_name: str,
        errors: list[str],
        target: dict[str, ResolvedWrite],
        source: str,
        priority: int | None,
    ) -> None:
        for state, items in (("OFF", cb_changes.off), ("SWITCH", cb_changes.switch), ("ON", cb_changes.on)):
            for name in items:
                cb_name = name.strip()
                if not cb_name:
                    continue
                self._set_value(target, cb_name, state, case_name, errors, source, priority)

    def _set_value(
        self,
        target: dict,
        key,
        value: str,
        case_name: str,
        errors: list[str],
        source: str,
        priority: int | None,
    ) -> None:
        if not value:
            return

        existing = target.get(key)
        incoming = ResolvedWrite(value=value, source=source, priority=priority)
        if existing is None or not self._keep_existing_write(
            existing,
            value,
            source,
            priority,
            case_name,
            key,
            errors,
        ):
            target[key] = incoming

    def _keep_existing_write(
        self,
        existing: ResolvedWrite | ResolvedRowWrite,
        incoming_value: object,
        source: str,
        priority: int | None,
        case_name: str,
        key: object,
        errors: list[str],
    ) -> bool:
        existing_value = existing.value if isinstance(existing, ResolvedWrite) else existing.row
        if existing_value == incoming_value:
            if source == "conditional" and existing.source == "conditional" and priority is not None:
                existing.priority = max(existing.priority or priority, priority)
            return True

        if existing.source == "conditional" and source == "conditional":
            if existing.priority == priority:
                errors.append(f"Conflicting same-priority conditional changes for case '{case_name}' on target '{key}'.")
                return True
            return (priority or 0) <= (existing.priority or 0)

        return False

    def _row_identity(self, item, fallback_key) -> str:  # noqa: ANN001
        base_row_id = getattr(item, "base_row_id", "").strip()
        row_id = getattr(item, "id", "").strip()
        if base_row_id:
            return base_row_id
        if row_id:
            return row_id
        return f"tuple:{fallback_key!r}"

    def _set_row(
        self,
        target: dict[str, ResolvedRowWrite],
        key: str,
        row,
        case_name: str,
        errors: list[str],
        source: str,
        priority: int | None,
    ) -> None:
        existing = target.get(key)
        merged_row = self._merge_row(existing.row, row) if existing is not None else row
        incoming = ResolvedRowWrite(row=merged_row, source=source, priority=priority)
        if existing is None or not self._keep_existing_write(
            existing,
            merged_row,
            source,
            priority,
            case_name,
            key,
            errors,
        ):
            target[key] = incoming

    def _merge_row(self, existing_row, new_row):  # noqa: ANN001
        if isinstance(existing_row, ParameterChange) and isinstance(new_row, ParameterChange):
            return ParameterChange(
                id=new_row.id or existing_row.id,
                base_row_id=new_row.base_row_id or existing_row.base_row_id,
                definition=new_row.definition or existing_row.definition,
                parameter=new_row.parameter or existing_row.parameter,
                value=new_row.value or existing_row.value,
            )
        if isinstance(existing_row, LayerChange) and isinstance(new_row, LayerChange):
            return LayerChange(
                id=new_row.id or existing_row.id,
                base_row_id=new_row.base_row_id or existing_row.base_row_id,
                section=new_row.section or existing_row.section,
                layer_type=new_row.layer_type or existing_row.layer_type,
                target=new_row.target or existing_row.target,
                state=new_row.state or existing_row.state,
            )
        if isinstance(existing_row, FluxChange) and isinstance(new_row, FluxChange):
            return FluxChange(
                id=new_row.id or existing_row.id,
                base_row_id=new_row.base_row_id or existing_row.base_row_id,
                layer=new_row.layer or existing_row.layer,
                transformer=new_row.transformer or existing_row.transformer,
                value=new_row.value or existing_row.value,
            )
        return new_row

    def _materialize_parameter_rows(
        self,
        rows: dict[str, ResolvedRowWrite],
        target: dict[tuple[str, str], ResolvedWrite],
        case_name: str,
        errors: list[str],
    ) -> None:
        for resolved in rows.values():
            row = resolved.row
            key = (row.definition.strip(), row.parameter.strip())
            self._set_value(target, key, row.value.strip(), case_name, errors, resolved.source, resolved.priority)

    def _materialize_layer_rows(
        self,
        rows: dict[str, ResolvedRowWrite],
        target: dict[tuple[str, str, str], ResolvedWrite],
        case_name: str,
        errors: list[str],
    ) -> None:
        for resolved in rows.values():
            row = resolved.row
            key = (row.section.strip(), row.layer_type.strip(), row.target.strip())
            self._set_value(target, key, row.state.strip(), case_name, errors, resolved.source, resolved.priority)

    def _materialize_flux_rows(
        self,
        rows: dict[str, ResolvedRowWrite],
        target: dict[tuple[str, str], ResolvedWrite],
        case_name: str,
        errors: list[str],
    ) -> None:
        for resolved in rows.values():
            row = resolved.row
            key = (row.layer.strip(), row.transformer.strip())
            self._set_value(target, key, row.value.strip(), case_name, errors, resolved.source, resolved.priority)
