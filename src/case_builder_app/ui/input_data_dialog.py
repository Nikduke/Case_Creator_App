from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from PySide6 import QtCore, QtWidgets

from case_builder_app.models import (
    INPUT_DATA_FAULT,
    INPUT_DATA_FREQUENCY_SWEEP,
    INPUT_DATA_SWITCHING,
    InputDataSettings,
    ProjectSettings,
)
from case_builder_app.services.input_data import input_data_timing_values
from case_builder_app.ui.table_helpers import ComboBoxDelegate, EDITOR_TABLE_STYLESHEET, create_editor_table


YES_NO_OPTIONS = ["Yes", "No"]
SWITCH_OPERATION_OPTIONS = ["On", "Off", "On-Off", "Off-On"]
SWITCH_TYPE_OPTIONS = ["Sequential", "Stochastic single-pole", "Stochastic 3-pole", "None"]
PSCAD_VERSION_OPTIONS = ["5.0.1", "5.0.2"]
FORTRAN_OPTIONS = [
    "Intel 16.0.207",
    "Intel 16.0.110",
    "Intel 19.2.978",
    "GFortran 8.1",
    "GFortran 8.1 (64-bit)",
    "Intel 16.0.207 (64-bit)",
    "GFortran 4.2.1",
    "Intel 16.0.110 (64-bit)",
    "Intel 19.2.978 (64-bit)",
    "Intel 2024.2 (64-bit)",
    "GFortran 4.6.2",
]


@dataclass(frozen=True)
class SettingRow:
    key: str
    label: str
    units: str = ""
    options: tuple[str, ...] = ()
    editable: bool = True


class InputDataDialog(QtWidgets.QDialog):
    def __init__(self, project_settings: ProjectSettings, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Input_Data Settings")
        self.resize(900, 720)
        self._settings = deepcopy(project_settings.input_data)
        self._tables: dict[str, QtWidgets.QTableWidget] = {}
        self._table_rows: dict[str, list[SettingRow]] = {}
        self._plain_delegate = QtWidgets.QStyledItemDelegate(self)
        self._loading = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._build_study_group(self))

        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget(scroll)
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setSpacing(12)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        self.frequency_sweep_group = self._build_table_group(
            content,
            "Frequency sweep",
            "frequency_sweep",
            [
                SettingRow("client_workspace", "Client Workspace", "str"),
                SettingRow("auto_ctrl", "Auto_Ctrl", "List"),
                SettingRow("min_frequency", "Min Frequency", "Hz"),
                SettingRow("max_frequency", "Max Frequency", "Hz"),
                SettingRow("frequency_increment", "Frequency increment", "Hz"),
                SettingRow("increment_type", "Increment Type", "Int"),
                SettingRow("z_output_type", "Z output type", "Int"),
                SettingRow("frequency_units", "Frequency units", "Hz"),
                SettingRow("impedance_output_units", "Impedance output units", "Int"),
            ],
        )
        self.switching_group = self._build_table_group(
            content,
            "Switching",
            "switching",
            [
                SettingRow("residual_flux", "Residual Flux", "str", tuple(YES_NO_OPTIONS)),
                SettingRow("switch_operation", "Switch operation", "str", tuple(SWITCH_OPERATION_OPTIONS)),
                SettingRow("switch_type", "Switch type", "str", tuple(SWITCH_TYPE_OPTIONS)),
                SettingRow("points_over_wave", "N points over wave", "Int"),
                SettingRow("switch_start", "Switch start", "Real"),
                SettingRow("switch_increment", "Switch increment", "Real", editable=False),
                SettingRow("switch_points_to_check", "1st N points to check", "Int"),
                SettingRow("switch_stop", "Switch stop", "Real", editable=False),
                SettingRow("second_switch_delay", "2nd Switch delay", "Real"),
                SettingRow("n1r", "N1R", "Int"),
                SettingRow("n2r", "N2R", "Int"),
                SettingRow("n3r", "N3R", "Int"),
                SettingRow("min1r", "Min1R", "Real"),
                SettingRow("max1r", "Max1R", "Real"),
                SettingRow("min2r", "Min2R", "Real"),
                SettingRow("max2r", "Max2R", "Real"),
                SettingRow("min3r", "Min3R", "Real"),
                SettingRow("max3r", "Max3R", "Real"),
            ],
        )
        self.fault_group = self._build_table_group(
            content,
            "Fault",
            "fault",
            [
                SettingRow("points_over_wave", "N points over wave", "Int"),
                SettingRow("fault_start", "Fault start", "Real"),
                SettingRow("fault_increment", "Fault increment", "Real", editable=False),
                SettingRow("fault_points_to_check", "1st N points to check", "Int"),
                SettingRow("fault_end", "Fault end", "Real", editable=False),
            ],
        )
        self.common_group = self._build_table_group(
            content,
            "Common settings",
            "common",
            [
                SettingRow("frequency", "Frequency", "Hz"),
                SettingRow("initialisation_duration", "Initialisation duration", "s"),
                SettingRow("time_step", "Time step", "us"),
                SettingRow("plot_step", "Plot step", "us"),
                SettingRow("create_cases", "Create cases", "str", tuple(YES_NO_OPTIONS)),
                SettingRow("take_snapshot", "Take Snapshot", "str", tuple(YES_NO_OPTIONS)),
                SettingRow("adjust_names", "Adjust names", "str", tuple(YES_NO_OPTIONS)),
                SettingRow("snapshot_time", "Snapshot Time", "Real"),
                SettingRow("final_duration", "Final duration", "s"),
                SettingRow("mpe_workspace", "MPE Workspace", "str"),
                SettingRow("pscad_version", "PSCAD version", "str", tuple(PSCAD_VERSION_OPTIONS)),
                SettingRow("fortran_compiler", "FORTRAN Compiler", "str", tuple(FORTRAN_OPTIONS)),
                SettingRow("parallel_simulations", "Parallel simulations", "Int"),
                SettingRow("pscad_instances", "PSCAD instances", "Int"),
                SettingRow("number_of_cores", "Number of cores", "-"),
            ],
        )
        self.setup_group = self._build_table_group(
            content,
            "Case folder setup",
            "setup",
            [
                SettingRow("folders", "Folders"),
                SettingRow("libraries", "Libraries"),
                SettingRow("files_inside_cases", "Files inside cases"),
                SettingRow("files_in_case_folder", "Files in Case_folder"),
            ],
        )
        content_layout.addWidget(self.frequency_sweep_group)
        content_layout.addWidget(self.switching_group)
        content_layout.addWidget(self.fault_group)
        content_layout.addWidget(self.common_group)
        content_layout.addWidget(self.setup_group)
        content_layout.addStretch(1)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(EDITOR_TABLE_STYLESHEET)
        self._load_settings()
        self._refresh_visibility()

    def input_data_settings(self) -> InputDataSettings:
        self._store_tables()
        return deepcopy(self._settings)

    def _build_study_group(self, parent: QtWidgets.QWidget) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("Study selection", parent)
        layout = QtWidgets.QHBoxLayout(group)
        self.frequency_sweep_checkbox = QtWidgets.QCheckBox("Frequency sweep", group)
        self.switching_checkbox = QtWidgets.QCheckBox("Switching", group)
        self.fault_checkbox = QtWidgets.QCheckBox("Fault", group)
        layout.addWidget(self.frequency_sweep_checkbox)
        layout.addWidget(self.switching_checkbox)
        layout.addWidget(self.fault_checkbox)
        layout.addStretch(1)
        hint = QtWidgets.QLabel("Frequency sweep exclusive. Switching + Fault allowed.", group)
        hint.setStyleSheet("color: #60717d;")
        layout.addWidget(hint)
        self.frequency_sweep_checkbox.toggled.connect(self._on_study_toggled)
        self.switching_checkbox.toggled.connect(self._on_study_toggled)
        self.fault_checkbox.toggled.connect(self._on_study_toggled)
        return group

    def _build_table_group(
        self,
        parent: QtWidgets.QWidget,
        title: str,
        name: str,
        rows: list[SettingRow],
    ) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox(title, parent)
        layout = QtWidgets.QVBoxLayout(group)
        table = create_editor_table(
            group,
            ["Parameter", "Value", "Units"],
            editable=True,
            default_widths=[250, 260, 90],
            expand_on_paste=False,
        )
        table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        table.itemChanged.connect(self._on_table_changed)
        self._tables[name] = table
        self._table_rows[name] = rows
        layout.addWidget(table)
        return group

    def _load_settings(self) -> None:
        self._loading = True
        try:
            studies = set(self._settings.normalized_studies())
            self.frequency_sweep_checkbox.setChecked(INPUT_DATA_FREQUENCY_SWEEP in studies)
            self.switching_checkbox.setChecked(INPUT_DATA_SWITCHING in studies)
            self.fault_checkbox.setChecked(INPUT_DATA_FAULT in studies)
            self._refresh_tables()
        finally:
            self._loading = False

    def _refresh_tables(self) -> None:
        for name, table in self._tables.items():
            rows = self._visible_rows(name)
            table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                self._set_item(table, row_index, 0, row.label, editable=False)
                self._set_item(table, row_index, 1, self._value_for_row(row), editable=row.editable)
                self._set_item(table, row_index, 2, row.units, editable=False)
                if row.options:
                    table.setItemDelegateForRow(row_index, ComboBoxDelegate(list(row.options), table))
                else:
                    table.setItemDelegateForRow(row_index, self._plain_delegate)
            table.resizeRowsToContents()
            self._adjust_table_height(table)

    def _visible_rows(self, table_name: str) -> list[SettingRow]:
        rows = self._table_rows[table_name]
        studies = set(self._settings.normalized_studies())
        combined_sequential = (
            table_name == "fault"
            and INPUT_DATA_SWITCHING in studies
            and INPUT_DATA_FAULT in studies
            and self._settings.switch_type == "Sequential"
        )
        if table_name == "fault" and INPUT_DATA_SWITCHING in studies:
            hidden_keys = {"points_over_wave"}
            if combined_sequential:
                hidden_keys.add("fault_points_to_check")
            return [row for row in rows if row.key not in hidden_keys]
        if table_name != "switching":
            return rows
        switch_type = self._settings.switch_type
        switch_operation = self._settings.switch_operation
        visible: list[SettingRow] = []
        for row in rows:
            if row.key in {"points_over_wave", "switch_start", "switch_increment", "switch_points_to_check", "switch_stop"}:
                if switch_type != "Sequential":
                    continue
            if row.key == "second_switch_delay":
                if switch_operation not in {"On-Off", "Off-On"}:
                    continue
            if row.key in {"n1r", "n2r", "n3r", "min1r", "max1r"}:
                if not switch_type.startswith("Stochastic"):
                    continue
            if row.key in {"min2r", "max2r", "min3r", "max3r"}:
                if switch_type != "Stochastic single-pole":
                    continue
            visible.append(row)
        return visible

    def _set_item(self, table: QtWidgets.QTableWidget, row: int, column: int, value: str, *, editable: bool) -> None:
        item = QtWidgets.QTableWidgetItem(value)
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if editable:
            flags |= QtCore.Qt.ItemIsEditable
        item.setFlags(flags)
        table.setItem(row, column, item)

    def _on_study_toggled(self) -> None:
        if self._loading:
            return
        sender = self.sender()
        with QtCore.QSignalBlocker(self.frequency_sweep_checkbox), QtCore.QSignalBlocker(self.switching_checkbox), QtCore.QSignalBlocker(self.fault_checkbox):
            if sender is self.frequency_sweep_checkbox and self.frequency_sweep_checkbox.isChecked():
                self.switching_checkbox.setChecked(False)
                self.fault_checkbox.setChecked(False)
            elif sender in {self.switching_checkbox, self.fault_checkbox} and (self.switching_checkbox.isChecked() or self.fault_checkbox.isChecked()):
                self.frequency_sweep_checkbox.setChecked(False)
            elif not (self.frequency_sweep_checkbox.isChecked() or self.switching_checkbox.isChecked() or self.fault_checkbox.isChecked()):
                self.frequency_sweep_checkbox.setChecked(True)
        self._store_studies()
        self._refresh_visibility()

    def _on_table_changed(self, item: QtWidgets.QTableWidgetItem) -> None:
        if self._loading or item.column() != 1:
            return
        key = self._key_for_item(item)
        self._store_tables()
        if key in {
            "frequency",
            "points_over_wave",
            "switch_type",
            "switch_operation",
            "switch_start",
            "switch_points_to_check",
            "fault_start",
            "fault_points_to_check",
        }:
            self._reload_tables()

    def _store_studies(self) -> None:
        studies: list[str] = []
        if self.frequency_sweep_checkbox.isChecked():
            studies.append(INPUT_DATA_FREQUENCY_SWEEP)
        if self.switching_checkbox.isChecked():
            studies.append(INPUT_DATA_SWITCHING)
        if self.fault_checkbox.isChecked():
            studies.append(INPUT_DATA_FAULT)
        self._settings.studies = studies
        self._settings.studies = self._settings.normalized_studies()
        if INPUT_DATA_SWITCHING in self._settings.studies and INPUT_DATA_FAULT in self._settings.studies:
            self._settings.switch_type = "Sequential"

    def _store_tables(self) -> None:
        self._store_studies()
        seen_keys: set[str] = set()
        for table_name, table in self._tables.items():
            if not self._table_is_active(table_name):
                continue
            rows = self._visible_rows(table_name)
            for row_index, row in enumerate(rows):
                if row.key in seen_keys:
                    continue
                item = table.item(row_index, 1)
                if item is None or not row.editable:
                    continue
                setattr(self._settings, row.key, item.text().strip())
                seen_keys.add(row.key)

    def _table_is_active(self, table_name: str) -> bool:
        studies = set(self._settings.normalized_studies())
        if table_name == "frequency_sweep":
            return INPUT_DATA_FREQUENCY_SWEEP in studies
        if table_name == "switching":
            return INPUT_DATA_SWITCHING in studies
        if table_name == "fault":
            return INPUT_DATA_FAULT in studies
        return True

    def _refresh_visibility(self) -> None:
        self._store_studies()
        studies = set(self._settings.normalized_studies())
        self.frequency_sweep_group.setVisible(INPUT_DATA_FREQUENCY_SWEEP in studies)
        self.switching_group.setVisible(INPUT_DATA_SWITCHING in studies)
        self.fault_group.setVisible(INPUT_DATA_FAULT in studies)
        self._loading = True
        try:
            self._refresh_tables()
        finally:
            self._loading = False

    def _reload_tables(self) -> None:
        self._loading = True
        try:
            self._refresh_tables()
        finally:
            self._loading = False

    def _value_for_row(self, row: SettingRow) -> str:
        timing = input_data_timing_values(self._settings)
        if row.key == "switch_increment":
            return _format_float(timing["increment"])
        if row.key == "switch_stop":
            return _format_float(timing["switch_stop"])
        if row.key == "fault_increment":
            return _format_float(timing["increment"])
        if row.key == "fault_end":
            return _format_float(timing["fault_end"])
        return self._value_for_key(row.key)

    def _value_for_key(self, key: str) -> str:
        return str(getattr(self._settings, key, ""))

    def _key_for_item(self, item: QtWidgets.QTableWidgetItem) -> str:
        table = item.tableWidget()
        if table is None:
            return ""
        table_name = next((name for name, candidate in self._tables.items() if candidate is table), "")
        rows = self._visible_rows(table_name)
        if item.row() >= len(rows):
            return ""
        return rows[item.row()].key

    def _adjust_table_height(self, table: QtWidgets.QTableWidget) -> None:
        header_height = table.horizontalHeader().height()
        row_height = sum(table.rowHeight(row) for row in range(table.rowCount()))
        table.setFixedHeight(header_height + row_height + table.frameWidth() * 2 + 6)
        table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)


def _format_float(value: float) -> str:
    return f"{value:.9f}".rstrip("0").rstrip(".")
