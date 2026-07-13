from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6 import QtCore, QtWidgets

from case_builder_app.models import CBChanges, CasePart, CaseValue, cb_state_map
from case_builder_app.ui.cb_state_board import CBPreviewRow, CBPreviewValue

if TYPE_CHECKING:
    from case_builder_app.ui.main_window import MainWindow


class ProjectSelectionController:
    def __init__(self, window: MainWindow) -> None:
        self.window = window

    def selected_case_part_index(self) -> int | None:
        row = self.window.case_parts_list.currentRow() - 1
        if row < 0 or row >= len(self.window.project.case_parts):
            return None
        return row

    def selected_case_part(self) -> CasePart | None:
        index = self.selected_case_part_index()
        if index is None:
            return None
        return self.window.project.case_parts[index]

    def is_base_selected(self) -> bool:
        return self.window.case_parts_list.currentRow() == 0 and self.window.case_parts_list.count() > 0

    def selected_value(self) -> CaseValue | None:
        case_part = self.selected_case_part()
        if case_part is None:
            return None
        row = self.window.values_list.currentRow()
        if row < 0 or row >= len(case_part.values):
            return None
        return case_part.values[row]

    def refresh_case_parts(self) -> None:
        current_row = self.window.case_parts_list.currentRow()
        with QtCore.QSignalBlocker(self.window.case_parts_list):
            self.window.case_parts_list.clear()
            base_item = QtWidgets.QListWidgetItem(self.window.project.base_case.label or "Base Case")
            font = base_item.font()
            font.setBold(True)
            base_item.setFont(font)
            self.window.case_parts_list.addItem(base_item)
            for case_part in self.window.project.case_parts:
                self.window.case_parts_list.addItem(f"{case_part.label} ({len(case_part.values)})")
            if self.window.case_parts_list.count():
                self.window.case_parts_list.setCurrentRow(
                    min(max(current_row, 0), self.window.case_parts_list.count() - 1)
                )

    def refresh_values(self) -> None:
        current_row = self.window.values_list.currentRow()
        with QtCore.QSignalBlocker(self.window.values_list):
            self.window.values_list.clear()
            if self.is_base_selected():
                self.window.values_list.addItem(self.window.project.base_case.token or "BC")
                self.window.values_list.setCurrentRow(0)
            else:
                case_part = self.selected_case_part()
                if case_part is not None:
                    for value in case_part.values:
                        self.window.values_list.addItem(value.token)
                    if case_part.values:
                        self.window.values_list.setCurrentRow(min(max(current_row, 0), len(case_part.values) - 1))

        self.on_value_selected(self.window.values_list.currentRow())
        self.refresh_selection_actions()

    def on_case_part_selected(self, _row: int) -> None:
        self.refresh_values()

    def on_value_selected(self, _row: int) -> None:
        self.window._loading_value = True
        if self.is_base_selected():
            self.window.changes_group.setTitle(
                f"{self.window.project.base_case.label or 'Base Case'} [{self.window.project.base_case.token or 'BC'}]"
            )
            self.window.changes_editor.setEnabled(True)
            self.window.changes_editor.set_context(
                base_changes=self.window.project.base_case.changes,
                is_base_case=True,
            )
            self.window.changes_editor.set_cb_preview_rows([])
            self.window.changes_editor.set_changes(self.window.project.base_case.changes)
        else:
            value = self.selected_value()
            case_part_index = self.selected_case_part_index()
            if value is None:
                self.window.changes_group.setTitle("Changes for [No Selection]")
                self.window.changes_editor.set_cb_preview_rows([])
                self.window.changes_editor.clear()
                self.window.changes_editor.setEnabled(False)
            else:
                self.window.changes_group.setTitle(f"Changes for [{value.token}]")
                self.window.changes_editor.setEnabled(True)
                self.window.changes_editor.set_context(
                    base_changes=self.window.project.base_case.changes,
                    is_base_case=False,
                )
                self.window.changes_editor.set_cb_preview_rows(self._cb_preview_rows(case_part_index or 0))
                self.window.changes_editor.set_cb_base_changes(
                    self._resolved_cb_preview_base(case_part_index or 0),
                    refresh=False,
                )
                self.window.changes_editor.set_changes(value.changes)
        self.window._loading_value = False

    def refresh_cb_preview_context(self) -> None:
        if self.is_base_selected():
            return
        case_part_index = self.selected_case_part_index()
        if case_part_index is None or self.selected_value() is None:
            return
        self.window.changes_editor.set_cb_preview_rows(self._cb_preview_rows(case_part_index))
        self.window.changes_editor.set_cb_base_changes(self._resolved_cb_preview_base(case_part_index))

    def _cb_preview_rows(self, case_part_index: int) -> list[CBPreviewRow]:
        rows: list[CBPreviewRow] = []
        for case_part in self.window.project.case_parts[:case_part_index]:
            if not self._case_part_has_cb_changes(case_part):
                continue
            rows.append(
                CBPreviewRow(
                    case_part_id=case_part.id,
                    label=case_part.label,
                    values=tuple(CBPreviewValue(id=value.id, token=value.token) for value in case_part.values),
                )
            )
        return rows

    def _resolved_cb_preview_base(self, case_part_index: int) -> CBChanges:
        state_by_token = cb_state_map(self.window.project.base_case.changes.cb)
        selection = self.window.changes_editor.cb_preview_selection()
        for case_part in self.window.project.case_parts[:case_part_index]:
            if not self._case_part_has_cb_changes(case_part):
                continue
            selected_value_id = selection.get(case_part.id)
            selected_value = next((value for value in case_part.values if value.id == selected_value_id), None)
            if selected_value is None:
                selected_value = case_part.values[0] if case_part.values else None
            if selected_value is None or not selected_value.changes.use_cb:
                continue
            state_by_token.update(cb_state_map(selected_value.changes.cb))
        return self._cb_changes_from_state(state_by_token)

    def _case_part_has_cb_changes(self, case_part: CasePart) -> bool:
        return any(value.changes.use_cb and not value.changes.cb.is_empty() for value in case_part.values)

    def _cb_changes_from_state(self, state_by_token: dict[str, str]) -> CBChanges:
        changes = CBChanges()
        for token, state_key in state_by_token.items():
            getattr(changes, state_key).append(token)
        return changes

    def update_base_case_preview(self) -> None:
        token = self.window.project.base_case.token.strip() or "BC"
        self.window.base_case_include_checkbox.setText(f'Include "{token}" in case names')
        preview_tokens: list[str] = []
        if self.window.project.base_case.include_in_case_name and token:
            preview_tokens.append(token)
        preview_tokens.extend(
            case_part.values[0].token for case_part in self.window.project.case_parts_in_name_order() if case_part.values
        )
        self.window.base_case_preview_label.setText(
            "_".join(preview_tokens) if preview_tokens else "(no generated case parts yet)"
        )

    def refresh_selection_actions(self) -> None:
        base_selected = self.is_base_selected()
        has_case_part = self.selected_case_part() is not None
        has_value = self.selected_value() is not None

        self.window.add_case_part_button.setEnabled(True)
        self.window.edit_case_part_button.setEnabled(base_selected or has_case_part)
        self.window.duplicate_case_part_button.setEnabled(has_case_part and not base_selected)
        self.window.delete_case_part_button.setEnabled(has_case_part and not base_selected)
        self.window.move_case_part_up_button.setEnabled(
            has_case_part and not base_selected and self.window.case_parts_list.currentRow() > 1
        )
        self.window.move_case_part_down_button.setEnabled(
            has_case_part
            and not base_selected
            and self.window.case_parts_list.currentRow() < self.window.case_parts_list.count() - 1
        )

        self.window.add_value_button.setEnabled(has_case_part and not base_selected)
        self.window.edit_value_button.setEnabled(
            (base_selected and self.window.values_list.count() > 0) or (has_value and not base_selected)
        )
        self.window.delete_value_button.setEnabled(has_value and not base_selected)
        self.window.move_value_up_button.setEnabled(
            has_value and not base_selected and self.window.values_list.currentRow() > 0
        )
        self.window.move_value_down_button.setEnabled(
            has_value
            and not base_selected
            and self.window.values_list.currentRow() < self.window.values_list.count() - 1
        )
