from __future__ import annotations

from copy import deepcopy

from PySide6 import QtCore, QtGui, QtWidgets

from case_builder_app.models import CBChanges, FluxChange, LayerChange, ParameterChange, ValueChanges, new_id
from case_builder_app.ui.cb_state_board import CBPreviewRow, CBStateBoard
from case_builder_app.ui.fault_level_section import FaultLevelSection
from case_builder_app.ui.inherited_table_section import InheritedTableSection
from case_builder_app.ui.table_helpers import (
    ComboBoxDelegate,
    EDITOR_TABLE_STYLESHEET,
    SuggestionDelegate,
)


class ChangesEditor(QtWidgets.QWidget):
    changed = QtCore.Signal()
    cb_preview_changed = QtCore.Signal()
    _DEFAULT_EDIT_ROWS = 3
    _FAULT_FIELDS = [("R+", "rpos"), ("X+", "xpos"), ("R0", "rzero"), ("X0", "xzero")]
    _FAULT_COLUMN_WIDTHS = [120, 220]
    _PARAMETER_COLUMN_WIDTHS = [220, 220, 160]
    _LAYER_COLUMN_WIDTHS = [240, 120, 280, 140]
    _FLUX_COLUMN_WIDTHS = [180, 240, 220]
    _TABLE_MAX_VISIBLE_ROWS = 8

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._loading = False
        self._res_flux_enabled = True
        self._is_base_case = True
        self._base_changes = ValueChanges()
        self._cb_base_changes = CBChanges()
        self._changes = ValueChanges()
        self._build_ui()
        self.clear()

    def _build_ui(self) -> None:
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.selector_bar = QtWidgets.QFrame(self)
        self.selector_bar.setObjectName("selectorBar")
        selector_layout = QtWidgets.QHBoxLayout(self.selector_bar)
        selector_layout.setContentsMargins(10, 10, 10, 10)
        selector_layout.setSpacing(8)
        self.cb_checkbox = self._create_selector_button("CB State", self.selector_bar)
        self.fault_checkbox = self._create_selector_button("Fault Level", self.selector_bar)
        self.parameter_checkbox = self._create_selector_button("Constants", self.selector_bar)
        self.layer_checkbox = self._create_selector_button("Layer", self.selector_bar)
        self.flux_checkbox = self._create_selector_button("Residual Flux", self.selector_bar)
        selector_layout.addWidget(self.cb_checkbox)
        selector_layout.addWidget(self.fault_checkbox)
        selector_layout.addWidget(self.parameter_checkbox)
        selector_layout.addWidget(self.layer_checkbox)
        selector_layout.addWidget(self.flux_checkbox)
        selector_layout.addStretch(1)
        outer.addWidget(self.selector_bar)

        self.scroll = QtWidgets.QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        outer.addWidget(self.scroll, 1)

        body = QtWidgets.QWidget(self.scroll)
        self.scroll.setWidget(body)
        layout = QtWidgets.QVBoxLayout(body)
        layout.setSpacing(14)

        self.cb_group = QtWidgets.QGroupBox("CB State", body)
        self.cb_group.setObjectName("sectionCard")
        cb_layout = QtWidgets.QVBoxLayout(self.cb_group)
        self._configure_section_layout(cb_layout)
        self.cb_board = CBStateBoard(self.cb_group)
        self.cb_board.preview_changed.connect(self.cb_preview_changed)
        cb_layout.addWidget(self.cb_board)
        layout.addWidget(self.cb_group)

        self.fault_section = FaultLevelSection(
            parent=self,
            title="Fault Level",
            fields=self._FAULT_FIELDS,
            default_widths=self._FAULT_COLUMN_WIDTHS,
            style_item=self._apply_item_style,
            section_layout_configurer=self._configure_section_layout,
            revert_handler=self._revert_fault_rows,
        )
        self.fault_group = self.fault_section.group
        self.fault_table = self.fault_section.table
        self.fault_revert_button = self.fault_section.revert_button
        layout.addWidget(self.fault_group)

        self.parameter_section = InheritedTableSection(
            parent=self,
            title="Constants",
            headers=["Definition", "Parameter", "Set Value"],
            default_widths=self._PARAMETER_COLUMN_WIDTHS,
            editable_columns={0, 1, 2},
            default_edit_rows=self._DEFAULT_EDIT_ROWS,
            style_item=self._apply_item_style,
            section_layout_configurer=self._configure_section_layout,
            add_handler=self._add_parameter_row,
            remove_handler=self._remove_parameter_rows,
            revert_handler=self._revert_parameter_rows,
        )
        self.parameter_group = self.parameter_section.group
        self.parameter_table = self.parameter_section.table
        self.parameter_add_button = self.parameter_section.add_button
        self.parameter_remove_button = self.parameter_section.remove_button
        self.parameter_revert_button = self.parameter_section.revert_button
        layout.addWidget(self.parameter_group)

        self.layer_section = InheritedTableSection(
            parent=self,
            title="Layer",
            headers=["Section", "Type", "Target", "State"],
            default_widths=self._LAYER_COLUMN_WIDTHS,
            editable_columns={0, 1, 2, 3},
            default_edit_rows=self._DEFAULT_EDIT_ROWS,
            style_item=self._apply_item_style,
            section_layout_configurer=self._configure_section_layout,
            add_handler=self._add_layer_row,
            remove_handler=self._remove_layer_rows,
            revert_handler=self._revert_layer_rows,
        )
        self.layer_group = self.layer_section.group
        self.layer_table = self.layer_section.table
        self.layer_add_button = self.layer_section.add_button
        self.layer_remove_button = self.layer_section.remove_button
        self.layer_revert_button = self.layer_section.revert_button
        self.layer_table.setItemDelegateForColumn(0, ComboBoxDelegate(["Layers", "Sweep_Components"], self.layer_table))
        self.layer_table.setItemDelegateForColumn(1, ComboBoxDelegate(["Extra", "Main"], self.layer_table))
        self.layer_table.setItemDelegateForColumn(3, ComboBoxDelegate(["Enable", "Disable"], self.layer_table))
        layout.addWidget(self.layer_group)

        self.flux_section = InheritedTableSection(
            parent=self,
            title="Residual Flux",
            headers=["Layer", "Transformer", "Flux Value"],
            default_widths=self._FLUX_COLUMN_WIDTHS,
            editable_columns={0, 1, 2},
            default_edit_rows=self._DEFAULT_EDIT_ROWS,
            style_item=self._apply_item_style,
            section_layout_configurer=self._configure_section_layout,
            add_handler=self._add_flux_row,
            remove_handler=self._remove_flux_rows,
            revert_handler=self._revert_flux_rows,
        )
        self.flux_group = self.flux_section.group
        self.flux_table = self.flux_section.table
        self.flux_add_button = self.flux_section.add_button
        self.flux_remove_button = self.flux_section.remove_button
        self.flux_revert_button = self.flux_section.revert_button
        layout.addWidget(self.flux_group)

        layout.addStretch(1)

        self.cb_board.changed.connect(self._notify_changed)
        self.fault_table.itemChanged.connect(self._notify_changed)
        self.parameter_table.itemChanged.connect(self._notify_changed)
        self.layer_table.itemChanged.connect(self._notify_changed)
        self.flux_table.itemChanged.connect(self._notify_changed)
        self.fault_table.itemSelectionChanged.connect(self._update_action_states)
        self.parameter_table.itemSelectionChanged.connect(self._update_action_states)
        self.layer_table.itemSelectionChanged.connect(self._update_action_states)
        self.flux_table.itemSelectionChanged.connect(self._update_action_states)
        self.cb_checkbox.toggled.connect(self._on_toggle_changed)
        self.parameter_checkbox.toggled.connect(self._on_toggle_changed)
        self.fault_checkbox.toggled.connect(self._on_toggle_changed)
        self.layer_checkbox.toggled.connect(self._on_toggle_changed)
        self.flux_checkbox.toggled.connect(self._on_toggle_changed)
        self.parameter_table.setItemDelegateForColumn(0, SuggestionDelegate(self._parameter_definition_suggestions, self.parameter_table))
        self.parameter_table.setItemDelegateForColumn(1, SuggestionDelegate(self._parameter_name_suggestions, self.parameter_table))
        self.layer_table.setItemDelegateForColumn(2, SuggestionDelegate(self._layer_target_suggestions, self.layer_table))
        self.flux_table.setItemDelegateForColumn(0, SuggestionDelegate(self._flux_layer_suggestions, self.flux_table))
        self.flux_table.setItemDelegateForColumn(1, SuggestionDelegate(self._flux_transformer_suggestions, self.flux_table))
        self._sync_section_visibility()
        self._apply_styles()
        self._update_action_states()

    def _create_selector_button(self, text: str, parent: QtWidgets.QWidget) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton(parent)
        button.setObjectName("selectorButton")
        button.setText(text)
        button.setCheckable(True)
        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        button.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        return button

    def _configure_section_layout(self, layout: QtWidgets.QLayout) -> None:
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#selectorBar {
                background: #f5f7f8;
                border: 1px solid #d8e0e4;
                border-radius: 10px;
            }
            QToolButton#selectorButton {
                background: #ffffff;
                border: 1px solid #cfd8de;
                border-radius: 16px;
                padding: 6px 12px;
                color: #23323b;
                font-weight: 600;
            }
            QToolButton#selectorButton:checked {
                background: #e7eef3;
                border-color: #8ea5b3;
            }
            QGroupBox#sectionCard {
                background: #fbfcfd;
                border: 1px solid #d8e0e4;
                border-radius: 10px;
                margin-top: 22px;
                padding: 12px;
                font-weight: 600;
            }
            QGroupBox#sectionCard::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px 4px 6px;
                color: #31424d;
            }
            QFrame#cbLaneFrame {
                border-radius: 8px;
            }
            QFrame#cbLaneFrame[accent="off"] {
                background: #f3faf4;
                border: 1px solid #bed8c2;
            }
            QFrame#cbLaneFrame[accent="off"][active="true"] {
                background: #e4f3e7;
                border: 1px solid #8fbe98;
            }
            QFrame#cbLaneFrame[accent="switch"] {
                background: #fffaf0;
                border: 1px solid #e2d19f;
            }
            QFrame#cbLaneFrame[accent="switch"][active="true"] {
                background: #fff3d9;
                border: 1px solid #d1b56a;
            }
            QFrame#cbLaneFrame[accent="on"] {
                background: #fff4f1;
                border: 1px solid #e3beb4;
            }
            QFrame#cbLaneFrame[accent="on"][active="true"] {
                background: #fde7e0;
                border: 1px solid #d59a8a;
            }
            QFrame#cbPreviewFrame {
                background: #f6f9fb;
                border: 1px solid #d9e2e7;
                border-radius: 8px;
            }
            QLabel#cbPreviewTitle {
                color: #465964;
                font-weight: 700;
            }
            QLabel#cbPreviewLabel {
                color: #52636d;
                font-weight: 600;
            }
            QPushButton#cbPreviewButton {
                background: #ffffff;
                border: 1px solid #cbd7de;
                border-radius: 12px;
                padding: 4px 10px;
                min-width: 44px;
            }
            QPushButton#cbPreviewButton:checked {
                background: #e4eef5;
                border-color: #8ba8ba;
                font-weight: 700;
            }
            QLabel#cbLaneTitle {
                color: #33424d;
                font-weight: 700;
            }
            QLineEdit {
                min-height: 28px;
            }
            """
            + EDITOR_TABLE_STYLESHEET
        )

    def set_res_flux_enabled(self, enabled: bool) -> None:
        self._res_flux_enabled = enabled
        self.flux_checkbox.setVisible(enabled)
        self._sync_section_visibility()
        self._refresh_dynamic_heights()

    def set_context(self, *, base_changes: ValueChanges, is_base_case: bool) -> None:
        self._base_changes = deepcopy(base_changes)
        self._cb_base_changes = deepcopy(base_changes.cb)
        self._is_base_case = is_base_case
        self.fault_section.set_context(
            base_fault_level=self._base_changes.fault_level,
            is_base_case=self._is_base_case,
        )

    def set_changes(self, changes: ValueChanges) -> None:
        self._loading = True
        self._changes = deepcopy(changes)
        self.cb_checkbox.setChecked(self._changes.use_cb)
        self.parameter_checkbox.setChecked(self._changes.use_parameters)
        self.fault_checkbox.setChecked(self._changes.use_fault_level)
        self.layer_checkbox.setChecked(self._changes.use_layers)
        self.flux_checkbox.setChecked(self._changes.use_flux)
        self.cb_board.set_changes(
            self._changes.cb,
            base_changes=None if self._is_base_case else self._cb_base_changes,
            is_base_case=self._is_base_case,
        )
        self._refresh_fault_table()
        self._refresh_parameter_table()
        self._refresh_layer_table()
        self._refresh_flux_table()
        self._sync_section_visibility()
        self._refresh_dynamic_heights()
        self._loading = False

    def set_cb_preview_rows(self, rows: list[CBPreviewRow]) -> None:
        self.cb_board.set_preview_rows(rows)

    def cb_preview_selection(self) -> dict[str, str]:
        return self.cb_board.preview_selection()

    def set_cb_base_changes(self, cb_changes: CBChanges, *, refresh: bool = True) -> None:
        self._cb_base_changes = deepcopy(cb_changes)
        if refresh and not self._is_base_case:
            self.cb_board.set_changes(
                self._changes.cb,
                base_changes=self._cb_base_changes,
                is_base_case=False,
            )

    def clear(self) -> None:
        self.set_changes(ValueChanges())

    def get_changes(self) -> ValueChanges:
        changes = deepcopy(self._changes)
        changes.use_cb = self.cb_checkbox.isChecked()
        changes.use_parameters = self.parameter_checkbox.isChecked()
        changes.use_fault_level = self.fault_checkbox.isChecked()
        changes.use_layers = self.layer_checkbox.isChecked()
        changes.use_flux = self.flux_checkbox.isChecked()
        cb_values = self.cb_board.get_changes()
        changes.cb = cb_values
        changes.parameters = self._read_parameter_rows()
        fault_level = self._read_fault_level()
        changes.fault_level.rpos = fault_level["rpos"]
        changes.fault_level.xpos = fault_level["xpos"]
        changes.fault_level.rzero = fault_level["rzero"]
        changes.fault_level.xzero = fault_level["xzero"]
        changes.layers = self._read_layer_rows()
        changes.flux = self._read_flux_rows()
        return changes

    def _notify_changed(self) -> None:
        if self._loading:
            return
        self._refresh_inline_statuses()
        self._refresh_dynamic_heights()
        self._update_action_states()
        self.changed.emit()

    def _on_toggle_changed(self) -> None:
        self._sync_section_visibility()
        self._notify_changed()

    def _sync_section_visibility(self) -> None:
        self.cb_group.setVisible(self.cb_checkbox.isChecked())
        self.parameter_group.setVisible(self.parameter_checkbox.isChecked())
        self.fault_group.setVisible(self.fault_checkbox.isChecked())
        self.layer_group.setVisible(self.layer_checkbox.isChecked())
        self.flux_group.setVisible(self._res_flux_enabled and self.flux_checkbox.isChecked())
        self.fault_revert_button.setVisible(not self._is_base_case)
        if self.parameter_revert_button is not None:
            self.parameter_revert_button.setVisible(not self._is_base_case)
        if self.layer_revert_button is not None:
            self.layer_revert_button.setVisible(not self._is_base_case)
        self.flux_revert_button.setVisible(not self._is_base_case)
        self._refresh_dynamic_heights()
        self._update_action_states()

    def _refresh_parameter_table(self) -> None:
        self.parameter_section.refresh_from_items(
            is_base_case=self._is_base_case,
            base_items=self._base_changes.parameters,
            local_items=self._changes.parameters,
            values_for_item=self._parameter_values,
            key_for_item=self._parameter_key,
            row_id_for_item=self._change_id,
            base_row_id_for_item=self._change_base_row_id,
        )

    def _refresh_fault_table(self) -> None:
        self.fault_section.set_context(
            base_fault_level=self._base_changes.fault_level,
            is_base_case=self._is_base_case,
        )
        self.fault_section.set_values(self._changes.fault_level)

    def _refresh_layer_table(self) -> None:
        self.layer_section.refresh_from_items(
            is_base_case=self._is_base_case,
            base_items=self._base_changes.layers,
            local_items=self._changes.layers,
            values_for_item=self._layer_values,
            key_for_item=self._layer_key,
            row_id_for_item=self._change_id,
            base_row_id_for_item=self._change_base_row_id,
        )

    def _refresh_flux_table(self) -> None:
        self.flux_section.refresh_from_items(
            is_base_case=self._is_base_case,
            base_items=self._base_changes.flux,
            local_items=self._changes.flux,
            values_for_item=self._flux_values,
            key_for_item=self._flux_key,
            row_id_for_item=self._change_id,
            base_row_id_for_item=self._change_base_row_id,
        )

    def _has_fault_revertable_selection(self) -> bool:
        return self.fault_section.has_revertable_selection()

    def _update_action_states(self) -> None:
        fault_selected = bool(self.fault_table.selectedIndexes())
        parameter_selected = bool(self.parameter_section.selected_rows())
        layer_selected = bool(self.layer_section.selected_rows())
        flux_selected = bool(self.flux_section.selected_rows())

        self.parameter_add_button.setEnabled(self.parameter_checkbox.isChecked())
        self.layer_add_button.setEnabled(self.layer_checkbox.isChecked())
        self.flux_add_button.setEnabled(self._res_flux_enabled and self.flux_checkbox.isChecked())

        parameter_actionable = self.parameter_section.has_actionable_selection()
        layer_actionable = self.layer_section.has_actionable_selection()
        flux_actionable = self.flux_section.has_actionable_selection()
        fault_actionable = self._has_fault_revertable_selection()

        self.parameter_remove_button.setEnabled(self.parameter_checkbox.isChecked() and parameter_selected and parameter_actionable)
        self.layer_remove_button.setEnabled(self.layer_checkbox.isChecked() and layer_selected and layer_actionable)
        self.flux_remove_button.setEnabled(self._res_flux_enabled and self.flux_checkbox.isChecked() and flux_selected and flux_actionable)

        self.fault_revert_button.setEnabled(self.fault_checkbox.isChecked() and not self._is_base_case and fault_selected and fault_actionable)
        if self.parameter_revert_button is not None:
            self.parameter_revert_button.setEnabled(self.parameter_checkbox.isChecked() and not self._is_base_case and parameter_selected and parameter_actionable)
        if self.layer_revert_button is not None:
            self.layer_revert_button.setEnabled(self.layer_checkbox.isChecked() and not self._is_base_case and layer_selected and layer_actionable)
        self.flux_revert_button.setEnabled(self._res_flux_enabled and self.flux_checkbox.isChecked() and not self._is_base_case and flux_selected and flux_actionable)

    def _apply_item_style(self, item: QtWidgets.QTableWidgetItem, status: str) -> None:
        status = status or "plain"
        foreground = QtGui.QBrush(QtGui.QColor("#24343d"))
        background = QtGui.QBrush(QtGui.QColor("#ffffff"))
        if status == "inherited":
            foreground = QtGui.QBrush(QtGui.QColor("#73818c"))
            background = QtGui.QBrush(QtGui.QColor("#f9fbfc"))
        elif status == "overridden":
            background = QtGui.QBrush(QtGui.QColor("#f4eef9"))
        elif status == "added":
            background = QtGui.QBrush(QtGui.QColor("#eef7f2"))
        item.setForeground(foreground)
        item.setBackground(background)

    @staticmethod
    def _parameter_values(item: ParameterChange) -> list[str]:
        return [item.definition, item.parameter, item.value]

    @staticmethod
    def _parameter_key(item: ParameterChange) -> tuple[str, ...]:
        return (item.definition, item.parameter)

    @staticmethod
    def _layer_values(item: LayerChange) -> list[str]:
        return [item.section, item.layer_type, item.target, item.state]

    @staticmethod
    def _layer_key(item: LayerChange) -> tuple[str, ...]:
        return (item.section, item.layer_type, item.target)

    @staticmethod
    def _flux_values(item: FluxChange) -> list[str]:
        return [item.layer, item.transformer, item.value]

    @staticmethod
    def _flux_key(item: FluxChange) -> tuple[str, ...]:
        return (item.layer, item.transformer)

    @staticmethod
    def _change_id(item) -> str:  # noqa: ANN001
        return item.id

    @staticmethod
    def _change_base_row_id(item) -> str:  # noqa: ANN001
        return item.base_row_id

    @staticmethod
    def _create_parameter_change(row_id: str, base_row_id: str, values: list[str], base_values: list[str] | None) -> ParameterChange:
        definition, parameter, value = values
        if base_values is None:
            return ParameterChange(id=row_id, base_row_id=base_row_id, definition=definition, parameter=parameter, value=value)
        return ParameterChange(
            id=row_id,
            base_row_id=base_row_id,
            definition=definition if definition != base_values[0] else "",
            parameter=parameter if parameter != base_values[1] else "",
            value=value if value != base_values[2] else "",
        )

    @staticmethod
    def _create_layer_change(row_id: str, base_row_id: str, values: list[str], base_values: list[str] | None) -> LayerChange:
        section, layer_type, target, state = values
        if base_values is None:
            return LayerChange(id=row_id, base_row_id=base_row_id, section=section, layer_type=layer_type, target=target, state=state)
        return LayerChange(
            id=row_id,
            base_row_id=base_row_id,
            section=section if section != base_values[0] else "",
            layer_type=layer_type if layer_type != base_values[1] else "",
            target=target if target != base_values[2] else "",
            state=state if state != base_values[3] else "",
        )

    @staticmethod
    def _create_flux_change(row_id: str, base_row_id: str, values: list[str], base_values: list[str] | None) -> FluxChange:
        layer, transformer, value = values
        if base_values is None:
            return FluxChange(id=row_id, base_row_id=base_row_id, layer=layer, transformer=transformer, value=value)
        return FluxChange(
            id=row_id,
            base_row_id=base_row_id,
            layer=layer if layer != base_values[0] else "",
            transformer=transformer if transformer != base_values[1] else "",
            value=value if value != base_values[2] else "",
        )

    def _refresh_inline_statuses(self) -> None:
        self.parameter_section.refresh_statuses_from_current()
        self.layer_section.refresh_statuses_from_current()
        self.flux_section.refresh_statuses_from_current()
        self.fault_section.refresh_statuses_from_current()

    def _table_text(self, table: QtWidgets.QTableWidget, row: int, col: int) -> str:
        item = table.item(row, col)
        return item.text().strip() if item is not None else ""

    def _read_parameter_rows(self) -> list[ParameterChange]:
        return self.parameter_section.read_rows(
            is_base_case=self._is_base_case,
            base_items=self._base_changes.parameters,
            values_for_item=self._parameter_values,
            key_for_item=self._parameter_key,
            row_id_for_item=self._change_id,
            create_row=self._create_parameter_change,
            new_row_id=new_id,
        )

    def _read_fault_level(self) -> dict[str, str]:
        return self.fault_section.read_values()

    def _read_layer_rows(self) -> list[LayerChange]:
        return self.layer_section.read_rows(
            is_base_case=self._is_base_case,
            base_items=self._base_changes.layers,
            values_for_item=self._layer_values,
            key_for_item=self._layer_key,
            row_id_for_item=self._change_id,
            create_row=self._create_layer_change,
            new_row_id=new_id,
        )

    def _read_flux_rows(self) -> list[FluxChange]:
        return self.flux_section.read_rows(
            is_base_case=self._is_base_case,
            base_items=self._base_changes.flux,
            values_for_item=self._flux_values,
            key_for_item=self._flux_key,
            row_id_for_item=self._change_id,
            create_row=self._create_flux_change,
            new_row_id=new_id,
        )

    def _parameter_definition_suggestions(self, _index: QtCore.QModelIndex) -> list[str]:
        values = {item.definition.strip() for item in self._base_changes.parameters if item.definition.strip()}
        return sorted(values)

    def _parameter_name_suggestions(self, index: QtCore.QModelIndex) -> list[str]:
        definition = self._table_text(self.parameter_table, index.row(), 0)
        values = {
            item.parameter.strip()
            for item in self._base_changes.parameters
            if item.definition.strip() == definition and item.parameter.strip()
        }
        return sorted(values)

    def _layer_target_suggestions(self, index: QtCore.QModelIndex) -> list[str]:
        section = self._table_text(self.layer_table, index.row(), 0)
        layer_type = self._table_text(self.layer_table, index.row(), 1)
        values = {
            item.target.strip()
            for item in self._base_changes.layers
            if item.section.strip() == section and item.layer_type.strip() == layer_type and item.target.strip()
        }
        return sorted(values)

    def _flux_layer_suggestions(self, _index: QtCore.QModelIndex) -> list[str]:
        values = {item.layer.strip() for item in self._base_changes.flux if item.layer.strip()}
        return sorted(values)

    def _flux_transformer_suggestions(self, index: QtCore.QModelIndex) -> list[str]:
        layer = self._table_text(self.flux_table, index.row(), 0)
        values = {
            item.transformer.strip()
            for item in self._base_changes.flux
            if item.layer.strip() == layer and item.transformer.strip()
        }
        return sorted(values)

    def _add_parameter_row(self) -> None:
        if not self.parameter_checkbox.isChecked():
            self.parameter_checkbox.setChecked(True)
        self.parameter_section.add_blank_row()
        self._notify_changed()

    def _remove_parameter_rows(self) -> None:
        self.parameter_section.remove_or_revert_selected()
        self._notify_changed()

    def _revert_parameter_rows(self) -> None:
        self.parameter_section.revert_selected()
        self._notify_changed()

    def _add_layer_row(self) -> None:
        if not self.layer_checkbox.isChecked():
            self.layer_checkbox.setChecked(True)
        self.layer_section.add_blank_row()
        self._notify_changed()

    def _remove_layer_rows(self) -> None:
        self.layer_section.remove_or_revert_selected()
        self._notify_changed()

    def _revert_layer_rows(self) -> None:
        self.layer_section.revert_selected()
        self._notify_changed()

    def _refresh_dynamic_heights(self) -> None:
        self.fault_section.adjust_height()
        self.parameter_section.adjust_height(visible_rows=self._TABLE_MAX_VISIBLE_ROWS)
        self.layer_section.adjust_height(visible_rows=self._TABLE_MAX_VISIBLE_ROWS)
        self.flux_section.adjust_height(visible_rows=self._TABLE_MAX_VISIBLE_ROWS)

    def _add_flux_row(self) -> None:
        if not self.flux_checkbox.isChecked():
            self.flux_checkbox.setChecked(True)
        self.flux_section.add_blank_row()
        self._notify_changed()

    def _remove_flux_rows(self) -> None:
        self.flux_section.remove_or_revert_selected()
        self._notify_changed()

    def _revert_flux_rows(self) -> None:
        self.flux_section.revert_selected()
        self._notify_changed()

    def _revert_fault_rows(self) -> None:
        self.fault_section.revert_selected()
        self._notify_changed()
