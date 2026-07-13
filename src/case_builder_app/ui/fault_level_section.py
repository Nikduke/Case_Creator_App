from __future__ import annotations

from typing import Callable

from PySide6 import QtCore, QtWidgets

from case_builder_app.models import FaultLevelChange
from case_builder_app.ui.table_helpers import create_editor_table


class FaultLevelSection:
    def __init__(
        self,
        *,
        parent: QtWidgets.QWidget,
        title: str,
        fields: list[tuple[str, str]],
        default_widths: list[int],
        style_item: Callable[[QtWidgets.QTableWidgetItem, str], None],
        section_layout_configurer: Callable[[QtWidgets.QLayout], None],
        revert_handler,
    ) -> None:
        self._fields = fields
        self._style_item = style_item
        self._is_base_case = False
        self._base_fault_level = FaultLevelChange()

        self.group = QtWidgets.QGroupBox(title, parent)
        self.group.setObjectName("sectionCard")
        layout = QtWidgets.QVBoxLayout(self.group)
        section_layout_configurer(layout)

        self.table = create_editor_table(
            parent,
            ["Field", "Value"],
            editable=True,
            default_widths=default_widths,
            expand_on_paste=False,
            show_row_header=False,
        )
        layout.addWidget(self.table)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setSpacing(8)
        buttons.setContentsMargins(0, 4, 0, 0)
        self.revert_button = QtWidgets.QPushButton("Revert Selected", self.group)
        self.revert_button.clicked.connect(revert_handler)
        buttons.addWidget(self.revert_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.table.setRowCount(len(self._fields))
        for row, (label, _key) in enumerate(self._fields):
            label_item = QtWidgets.QTableWidgetItem()
            label_item.setFlags(label_item.flags() & ~QtCore.Qt.ItemIsEditable)
            label_item.setText(label)
            self.table.setItem(row, 0, label_item)

    def set_context(self, *, base_fault_level: FaultLevelChange, is_base_case: bool) -> None:
        self._base_fault_level = base_fault_level
        self._is_base_case = is_base_case
        self.revert_button.setVisible(not is_base_case)

    def set_values(self, fault_level: FaultLevelChange) -> None:
        values_by_key = {
            "rpos": fault_level.rpos,
            "xpos": fault_level.xpos,
            "rzero": fault_level.rzero,
            "xzero": fault_level.xzero,
        }
        for row, (label, key) in enumerate(self._fields):
            label_item = self.table.item(row, 0)
            if label_item is None:
                label_item = QtWidgets.QTableWidgetItem()
                label_item.setFlags(label_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row, 0, label_item)
            label_item.setText(label)

            base_value = "" if self._is_base_case else getattr(self._base_fault_level, key)
            current_value = values_by_key[key].strip() if self._is_base_case else (values_by_key[key].strip() or base_value.strip())
            status = self._status_for_values(local_value=values_by_key[key].strip(), base_value=base_value.strip())
            self._set_value_item(row, current_value, status)
            self._style_item(label_item, status)

    def refresh_statuses_from_current(self) -> None:
        for row, (_label, key) in enumerate(self._fields):
            value_item = self.table.item(row, 1)
            label_item = self.table.item(row, 0)
            if value_item is None or label_item is None:
                continue
            status = self._status_for_values(
                local_value=value_item.text().strip(),
                base_value=getattr(self._base_fault_level, key).strip(),
                allow_inherited=not self._is_base_case,
            )
            self._style_item(value_item, status)
            self._style_item(label_item, status)

    def read_values(self) -> dict[str, str]:
        if self._is_base_case:
            return {
                key: self._table_text(row, 1)
                for row, (_label, key) in enumerate(self._fields)
            }

        values: dict[str, str] = {}
        for row, (_label, key) in enumerate(self._fields):
            current = self._table_text(row, 1)
            base = getattr(self._base_fault_level, key).strip()
            values[key] = current if current and current != base else ""
        return values

    def has_revertable_selection(self) -> bool:
        if self._is_base_case:
            return False
        selected_rows = {index.row() for index in self.table.selectedIndexes()}
        for row in selected_rows:
            if row < 0 or row >= len(self._fields):
                continue
            key = self._fields[row][1]
            if self._table_text(row, 1) != getattr(self._base_fault_level, key).strip():
                return True
        return False

    def revert_selected(self) -> None:
        selected = self.table.selectedIndexes()
        if not selected:
            return
        for index in selected:
            if index.column() != 1:
                continue
            key = self._fields[index.row()][1]
            value = getattr(self._base_fault_level, key) if not self._is_base_case else ""
            self._set_value_item(index.row(), value, "inherited")
            label_item = self.table.item(index.row(), 0)
            if label_item is not None:
                self._style_item(label_item, "inherited")

    def adjust_height(self) -> None:
        self.table.resizeRowsToContents()
        header_height = self.table.horizontalHeader().height() if not self.table.horizontalHeader().isHidden() else 0
        rows_height = sum(self.table.rowHeight(row) for row in range(len(self._fields)))
        frame_height = self.table.frameWidth() * 2
        padding = 4
        required_height = header_height + rows_height + frame_height + padding
        self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.table.setFixedHeight(required_height)

    def _status_for_values(self, *, local_value: str, base_value: str, allow_inherited: bool = True) -> str:
        if self._is_base_case:
            return "base"
        if allow_inherited and (not local_value or local_value == base_value):
            return "inherited"
        return "overridden"

    def _set_value_item(self, row: int, value: str, status: str) -> None:
        item = self.table.item(row, 1)
        if item is None:
            item = QtWidgets.QTableWidgetItem()
            self.table.setItem(row, 1, item)
        item.setText(value)
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        self._style_item(item, status)

    def _table_text(self, row: int, col: int) -> str:
        item = self.table.item(row, col)
        return item.text().strip() if item is not None else ""
