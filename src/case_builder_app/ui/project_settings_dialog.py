from __future__ import annotations

from copy import deepcopy

from PySide6 import QtCore, QtWidgets

from case_builder_app.models import MMBlocks, MMLimit, Project
from case_builder_app.services.equipment import sort_equipment_names, sort_voltage_tokens, voltage_token
from case_builder_app.services.text_tokens import parse_token_text
from case_builder_app.ui.table_helpers import EDITOR_TABLE_STYLESHEET, create_editor_table
from case_builder_app.ui.token_list import TokenHistory, token_matches_filter


class ProjectSettingsDialog(QtWidgets.QDialog):
    def __init__(self, project: Project, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Project Settings")
        self.resize(920, 680)
        self._elements = sort_equipment_names(project.mm_blocks.elements)
        self._history = TokenHistory[list[str]]()
        self._loading = False

        self._limits_by_voltage = {
            item.voltage.strip(): deepcopy(item)
            for item in project.mm_blocks.limits_by_voltage
            if item.voltage.strip()
        }

        layout = QtWidgets.QVBoxLayout(self)
        tabs = QtWidgets.QTabWidget(self)
        tabs.addTab(self._build_mm_tab(tabs), "MM Blocks")
        layout.addWidget(tabs, 1)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._apply_styles()
        self._reset_history()
        self._refresh_all()

    def _build_mm_tab(self, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
        tab = QtWidgets.QWidget(parent)
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setSpacing(12)

        filter_row = QtWidgets.QHBoxLayout()
        self.include_edit = QtWidgets.QLineEdit(tab)
        self.include_edit.setPlaceholderText("Show only MM elements containing...")
        self.exclude_edit = QtWidgets.QLineEdit(tab)
        self.exclude_edit.setPlaceholderText("Hide MM elements containing...")
        filter_row.addWidget(QtWidgets.QLabel("Include", tab))
        filter_row.addWidget(self.include_edit, 1)
        filter_row.addWidget(QtWidgets.QLabel("Exclude", tab))
        filter_row.addWidget(self.exclude_edit, 1)
        layout.addLayout(filter_row)

        self.tree = QtWidgets.QTreeWidget(tab)
        self.tree.setHeaderLabels(["MM elements by voltage"])
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.tree, 2)

        controls = QtWidgets.QHBoxLayout()
        self.add_edit = QtWidgets.QPlainTextEdit(tab)
        self.add_edit.setPlaceholderText("Add MM element/list")
        self.add_edit.setFixedHeight(46)
        self.add_button = QtWidgets.QPushButton("Add", tab)
        self.delete_button = QtWidgets.QPushButton("Delete Selected", tab)
        self.undo_button = QtWidgets.QPushButton("Undo", tab)
        self.redo_button = QtWidgets.QPushButton("Redo", tab)
        controls.addWidget(self.add_edit, 2)
        controls.addWidget(self.add_button)
        controls.addStretch(1)
        controls.addWidget(self.undo_button)
        controls.addWidget(self.redo_button)
        controls.addWidget(self.delete_button)
        layout.addLayout(controls)

        self.limits_table = create_editor_table(
            tab,
            ["Voltage", "Un", "Um", "SDPF_LG", "SDPF_LL", "SIWL_LG", "SIWL_LL", "LIWL"],
            editable=True,
            default_widths=[110, 90, 90, 110, 110, 110, 110, 90],
            expand_on_paste=False,
        )
        self.limits_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.limits_table, 1)

        self.include_edit.textChanged.connect(self._apply_filter)
        self.exclude_edit.textChanged.connect(self._apply_filter)
        self.add_edit.textChanged.connect(self._update_actions)
        self.tree.itemSelectionChanged.connect(self._update_actions)
        self.add_button.clicked.connect(self._add_entered_elements)
        self.delete_button.clicked.connect(self._delete_selected)
        self.undo_button.clicked.connect(self._undo)
        self.redo_button.clicked.connect(self._redo)
        self.limits_table.itemChanged.connect(self._store_limit_table_values)
        return tab

    def _apply_styles(self) -> None:
        self.setStyleSheet(EDITOR_TABLE_STYLESHEET)

    def get_mm_blocks(self) -> MMBlocks:
        self._store_limit_table_values()
        return MMBlocks(
            elements=sort_equipment_names(self._elements),
            limits_by_voltage=[
                self._limits_by_voltage[voltage]
                for voltage in sort_voltage_tokens(list(self._limits_by_voltage))
                if self._limit_is_used_or_filled(voltage)
            ],
        )

    def _add_entered_elements(self) -> None:
        tokens = parse_token_text(self.add_edit.toPlainText())
        if not tokens:
            return
        existing = set(self._elements)
        changed = False
        for token in tokens:
            if token not in existing:
                self._elements.append(token)
                existing.add(token)
                changed = True
        if changed:
            self.add_edit.clear()
            self._elements = sort_equipment_names(self._elements)
            self._push_history()
            self._refresh_all()

    def _delete_selected(self) -> None:
        selected = [
            item.data(0, QtCore.Qt.UserRole)
            for item in self.tree.selectedItems()
            if item.data(0, QtCore.Qt.UserRole)
        ]
        if not selected:
            return
        to_remove = set(str(item) for item in selected)
        self._elements = [item for item in self._elements if item not in to_remove]
        self._push_history()
        self._refresh_all()

    def _refresh_all(self) -> None:
        self._refresh_tree()
        self._refresh_limit_table()
        self._update_actions()

    def _refresh_tree(self) -> None:
        self.tree.clear()
        grouped: dict[str, list[str]] = {}
        for element in sort_equipment_names(self._elements):
            grouped.setdefault(voltage_token(element) or "Unknown", []).append(element)

        for voltage in sort_voltage_tokens(list(grouped)):
            parent = QtWidgets.QTreeWidgetItem([f"{voltage} ({len(grouped[voltage])})"])
            parent.setFlags(parent.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.tree.addTopLevelItem(parent)
            for element in grouped[voltage]:
                child = QtWidgets.QTreeWidgetItem([element])
                child.setData(0, QtCore.Qt.UserRole, element)
                parent.addChild(child)
            parent.setExpanded(True)
        self._apply_filter()

    def _refresh_limit_table(self) -> None:
        self._store_limit_table_values()
        self._loading = True
        try:
            voltages = sort_voltage_tokens(list({voltage_token(item) for item in self._elements if voltage_token(item)}))
            self.limits_table.setRowCount(len(voltages))
            for row, voltage in enumerate(voltages):
                limit = self._limits_by_voltage.setdefault(voltage, MMLimit(voltage=voltage))
                values = [
                    limit.voltage,
                    limit.un,
                    limit.um,
                    limit.sdpf_lg,
                    limit.sdpf_ll,
                    limit.siwl_lg,
                    limit.siwl_ll,
                    limit.liwl,
                ]
                for column, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    if column == 0:
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                    self.limits_table.setItem(row, column, item)
            self.limits_table.resizeRowsToContents()
        finally:
            self._loading = False

    def _store_limit_table_values(self) -> None:
        if self._loading:
            return
        for row in range(self.limits_table.rowCount()):
            values = [self._table_text(row, column) for column in range(self.limits_table.columnCount())]
            voltage = values[0]
            if not voltage:
                continue
            self._limits_by_voltage[voltage] = MMLimit(
                voltage=voltage,
                un=values[1],
                um=values[2],
                sdpf_lg=values[3],
                sdpf_ll=values[4],
                siwl_lg=values[5],
                siwl_ll=values[6],
                liwl=values[7],
            )

    def _table_text(self, row: int, column: int) -> str:
        item = self.limits_table.item(row, column)
        return item.text().strip() if item is not None else ""

    def _apply_filter(self) -> None:
        include_value = self.include_edit.text()
        exclude_value = self.exclude_edit.text()
        for parent_index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(parent_index)
            visible_children = 0
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                visible = token_matches_filter(child.text(0), include_value, exclude_value)
                child.setHidden(not visible)
                if visible:
                    visible_children += 1
            parent.setHidden(visible_children == 0)

    def _reset_history(self) -> None:
        self._history.reset(list(self._elements))

    def _push_history(self) -> None:
        self._history.push(list(self._elements))
        self._update_actions()

    def _undo(self) -> None:
        snapshot = self._history.undo()
        if snapshot is None:
            return
        self._elements = snapshot
        self._refresh_all()

    def _redo(self) -> None:
        snapshot = self._history.redo()
        if snapshot is None:
            return
        self._elements = snapshot
        self._refresh_all()

    def _update_actions(self) -> None:
        has_selected_element = any(item.data(0, QtCore.Qt.UserRole) for item in self.tree.selectedItems())
        self.add_button.setEnabled(bool(parse_token_text(self.add_edit.toPlainText())))
        self.delete_button.setEnabled(has_selected_element)
        self.undo_button.setEnabled(self._history.can_undo)
        self.redo_button.setEnabled(self._history.can_redo)

    def _limit_is_used_or_filled(self, voltage: str) -> bool:
        if voltage in {voltage_token(item) for item in self._elements}:
            return True
        limit = self._limits_by_voltage[voltage]
        return any(
            value.strip()
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
