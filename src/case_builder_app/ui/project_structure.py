from __future__ import annotations

from copy import deepcopy

from case_builder_app.models import CasePart, CaseValue, Project, ValueChanges


class ProjectStructureController:
    @staticmethod
    def copy_selector_flags(target: ValueChanges, source: ValueChanges) -> None:
        target.use_cb = source.use_cb
        target.use_parameters = source.use_parameters
        target.use_fault_level = source.use_fault_level
        target.use_layers = source.use_layers
        target.use_flux = source.use_flux

    def case_part_selector_template(self, case_part: CasePart) -> ValueChanges:
        source = case_part.values[0].changes if case_part.values else ValueChanges()
        template = ValueChanges()
        self.copy_selector_flags(template, source)
        return template

    def sync_case_part_selectors(self, case_part: CasePart, source: ValueChanges) -> None:
        for case_value in case_part.values:
            self.copy_selector_flags(case_value.changes, source)

    def normalize_case_part_selectors(self, project: Project) -> None:
        for case_part in project.case_parts:
            if not case_part.values:
                continue
            self.sync_case_part_selectors(case_part, case_part.values[0].changes)

    def add_case_part(self, project: Project, label: str, tokens: list[str]) -> int:
        case_part = CasePart(label=label, values=[CaseValue(token=item) for item in tokens])
        project.case_parts.append(case_part)
        return len(project.case_parts) - 1

    @staticmethod
    def rename_base_case(project: Project, label: str) -> None:
        project.base_case.label = label

    def edit_case_part(self, case_part: CasePart, label: str, tokens: list[str]) -> None:
        existing_by_token = {item.token: item for item in case_part.values}
        case_part.label = label
        selector_template = self.case_part_selector_template(case_part)
        new_values: list[CaseValue] = []
        for token in tokens:
            if token in existing_by_token:
                new_values.append(existing_by_token[token])
            else:
                new_values.append(CaseValue(token=token, changes=deepcopy(selector_template)))
        case_part.values = new_values

    def duplicate_case_part(self, project: Project, case_part: CasePart) -> int:
        clone = CasePart(label=f"{case_part.label}_copy")
        for value in case_part.values:
            clone.values.append(CaseValue(token=value.token, changes=deepcopy(value.changes)))
        project.case_parts.append(clone)
        return len(project.case_parts) - 1

    @staticmethod
    def delete_case_part(project: Project, index: int) -> None:
        del project.case_parts[index]

    @staticmethod
    def move_case_part(project: Project, index: int, direction: int) -> int | None:
        target = index + direction
        if target < 0 or target >= len(project.case_parts):
            return None
        project.case_parts[index], project.case_parts[target] = project.case_parts[target], project.case_parts[index]
        return target

    @staticmethod
    def set_case_name_order(project: Project, ordered_ids: list[str]) -> bool:
        current_ids = [case_part.id for case_part in project.case_parts]
        valid_order = [case_part_id for case_part_id in ordered_ids if case_part_id in current_ids]
        valid_order.extend(case_part_id for case_part_id in current_ids if case_part_id not in valid_order)
        stored_order = [] if valid_order == current_ids else valid_order
        if project.settings.case_name_order == stored_order:
            return False
        project.settings.case_name_order = stored_order
        return True

    def add_values(self, case_part: CasePart, tokens: list[str]) -> int:
        selector_template = self.case_part_selector_template(case_part)
        start_index = len(case_part.values)
        for token in tokens:
            case_part.values.append(CaseValue(token=token, changes=deepcopy(selector_template)))
        return start_index

    @staticmethod
    def set_base_case_token(project: Project, token: str) -> None:
        project.base_case.token = token

    def edit_value(self, case_part: CasePart, row: int, value: CaseValue, tokens: list[str]) -> None:
        selector_template = self.case_part_selector_template(case_part)
        replacement_values = [CaseValue(token=tokens[0], id=value.id, changes=value.changes)]
        replacement_values.extend(CaseValue(token=token, changes=deepcopy(selector_template)) for token in tokens[1:])
        case_part.values[row : row + 1] = replacement_values

    @staticmethod
    def delete_value(case_part: CasePart, row: int) -> None:
        del case_part.values[row]

    @staticmethod
    def move_value(case_part: CasePart, row: int, direction: int) -> int | None:
        target = row + direction
        if row < 0 or target < 0 or target >= len(case_part.values):
            return None
        case_part.values[row], case_part.values[target] = case_part.values[target], case_part.values[row]
        return target
