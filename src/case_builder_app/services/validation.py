from __future__ import annotations

from dataclasses import dataclass, field

from case_builder_app.models import CBChanges, ConditionalRule, ExclusionCombination, Project, ValueChanges
from case_builder_app.services.equipment import voltage_token


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


class ValidationService:
    def validate_project(self, project: Project) -> ValidationResult:
        result = ValidationResult()
        self._validate_ids(project, result)
        self._validate_base_case(project, result)
        self._validate_case_parts(project, result)
        self._validate_exclusions(project.exclusions, result)
        self._validate_conditional_rules(
            project,
            project.conditional_rules,
            result,
            res_flux_enabled=project.settings.input_data.uses_residual_flux(),
        )
        self._validate_mm_blocks(project, result)
        return result

    def _validate_ids(self, project: Project, result: ValidationResult) -> None:
        self._validate_unique_ids("case part", project.case_parts, result)
        for case_part in project.case_parts:
            self._validate_unique_ids(f"value in case part '{case_part.label}'", case_part.values, result)
        self._validate_unique_ids("conditional rule", project.conditional_rules, result)
        self._validate_unique_ids("saved case list", project.selected_case_lists, result)

        case_part_ids = {case_part.id for case_part in project.case_parts}
        seen_order_ids: set[str] = set()
        for case_part_id in project.settings.case_name_order:
            if case_part_id in seen_order_ids:
                result.errors.append(f"Duplicate case-name order entry: {case_part_id}")
            elif case_part_id not in case_part_ids:
                result.errors.append(f"Unknown case-name order entry: {case_part_id}")
            seen_order_ids.add(case_part_id)

    @staticmethod
    def _validate_unique_ids(context: str, items: list, result: ValidationResult) -> None:  # noqa: ANN401
        seen: set[str] = set()
        for item in items:
            item_id = str(getattr(item, "id", "")).strip()
            if not item_id:
                result.errors.append(f"{context.capitalize()} IDs cannot be empty.")
            elif item_id in seen:
                result.errors.append(f"Duplicate {context} ID: {item_id}")
            seen.add(item_id)

    def _validate_base_case(self, project: Project, result: ValidationResult) -> None:
        if not project.base_case.label.strip():
            result.errors.append("Base-case label cannot be empty.")
        if not project.base_case.token.strip():
            result.errors.append("Base-case token cannot be empty.")
        self._validate_changes(
            "base case",
            project.base_case.changes,
            result,
            res_flux_enabled=project.settings.input_data.uses_residual_flux(),
            require_complete_fault_level=True,
        )

    def _validate_case_parts(self, project: Project, result: ValidationResult) -> None:
        seen_labels: set[str] = set()
        for case_part in project.case_parts:
            label = case_part.label.strip()
            if not label:
                result.errors.append("Case-part labels cannot be empty.")
            elif label in seen_labels:
                result.errors.append(f"Duplicate case-part label: {label}")
            seen_labels.add(label)

            seen_tokens: set[str] = set()
            for value in case_part.values:
                token = value.token.strip()
                if not token:
                    result.errors.append(f"Case part '{label}' contains an empty value.")
                elif token in seen_tokens:
                    result.errors.append(f"Case part '{label}' contains duplicate value '{token}'.")
                seen_tokens.add(token)
                self._validate_changes(
                    f"value '{token}' in case part '{label}'",
                    value.changes,
                    result,
                    res_flux_enabled=project.settings.input_data.uses_residual_flux(),
                    require_complete_fault_level=False,
                )

    def _validate_changes(
        self,
        context: str,
        changes: ValueChanges,
        result: ValidationResult,
        *,
        res_flux_enabled: bool,
        require_complete_fault_level: bool,
    ) -> None:
        if changes.use_cb:
            self._validate_cb_changes(context, changes.cb, result)

        if (
            require_complete_fault_level
            and changes.use_fault_level
            and not changes.fault_level.is_empty()
            and not changes.fault_level.is_complete()
        ):
            result.errors.append(f"Incomplete fault-level entry for {context}.")

        if changes.use_parameters:
            for item in changes.parameters:
                if not item.is_complete():
                    result.errors.append(f"Incomplete parameter change for {context}.")

        if changes.use_layers:
            for item in changes.layers:
                if not item.is_complete():
                    result.errors.append(f"Incomplete layer change for {context}.")

        if changes.use_flux and res_flux_enabled:
            for item in changes.flux:
                if not item.is_complete():
                    result.errors.append(f"Incomplete residual-flux change for {context}.")

    def _validate_cb_changes(self, context: str, cb_changes: CBChanges, result: ValidationResult) -> None:
        buckets = {
            "OFF": set(name.strip() for name in cb_changes.off if name.strip()),
            "SWITCH": set(name.strip() for name in cb_changes.switch if name.strip()),
            "ON": set(name.strip() for name in cb_changes.on if name.strip()),
        }
        duplicates = (buckets["OFF"] & buckets["SWITCH"]) | (buckets["OFF"] & buckets["ON"]) | (buckets["SWITCH"] & buckets["ON"])
        if duplicates:
            joined = ", ".join(sorted(duplicates))
            result.errors.append(f"Contradictory CB assignment for {context}: {joined}.")

    def _validate_exclusions(self, exclusions: list[ExclusionCombination], result: ValidationResult) -> None:
        for combination in exclusions:
            if not combination.is_complete():
                result.errors.append("Exclusions cannot contain incomplete combinations.")
                continue
            seen_case_parts: set[str] = set()
            for clause in combination.clauses:
                if clause.case_part_id in seen_case_parts:
                    result.errors.append("One excluded combination cannot contain the same case part more than once.")
                seen_case_parts.add(clause.case_part_id)

    def _validate_conditional_rules(
        self,
        project: Project,
        rules: list[ConditionalRule],
        result: ValidationResult,
        *,
        res_flux_enabled: bool,
    ) -> None:
        for rule in rules:
            if rule.match_mode not in {"ALL", "ANY"}:
                result.errors.append(f"Conditional rule '{rule.name or rule.id}' has an invalid match mode.")
            if not rule.clauses:
                result.errors.append("Conditional rules must contain at least one clause.")
            for clause in rule.clauses:
                if not clause.is_complete():
                    result.errors.append("Conditional rules cannot contain incomplete clauses.")
                    continue
                case_part = project.find_case_part(clause.case_part_id)
                if case_part is None:
                    result.errors.append(f"Conditional rule '{rule.name or rule.id}' references an unknown case part.")
                elif project.find_value(clause.case_part_id, clause.value_id) is None:
                    result.errors.append(f"Conditional rule '{rule.name or rule.id}' references an unknown value.")
            self._validate_changes(
                f"conditional rule '{rule.name or rule.id}'",
                rule.changes,
                result,
                res_flux_enabled=res_flux_enabled,
                require_complete_fault_level=False,
            )

    def _validate_mm_blocks(self, project: Project, result: ValidationResult) -> None:
        elements = [item.strip() for item in project.mm_blocks.elements if item.strip()]
        if not elements:
            return

        duplicate_elements = sorted({item for item in elements if elements.count(item) > 1})
        if duplicate_elements:
            result.errors.append(f"Duplicate MM element names: {', '.join(duplicate_elements)}.")

        missing_voltage = [item for item in elements if not voltage_token(item)]
        if missing_voltage:
            result.errors.append(f"Could not detect MM voltage token for: {', '.join(missing_voltage)}.")

        required_voltages = {voltage_token(item) for item in elements}
        required_voltages.discard("")
        limits_by_voltage = {item.voltage.strip(): item for item in project.mm_blocks.limits_by_voltage if item.voltage.strip()}
        for voltage in sorted(required_voltages):
            limit = limits_by_voltage.get(voltage)
            if limit is None:
                result.errors.append(f"Missing MM limit row for voltage '{voltage}'.")
            elif not limit.is_complete():
                result.errors.append(f"Incomplete MM limit row for voltage '{voltage}'.")
