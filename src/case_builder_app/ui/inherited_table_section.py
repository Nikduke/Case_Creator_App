from __future__ import annotations

from typing import Callable, TypeVar

from PySide6 import QtCore, QtWidgets

from case_builder_app.ui.table_helpers import (
    DisplayRow,
    build_inherited_rows,
    create_editor_table,
    read_inherited_rows,
    refresh_inherited_table_statuses,
)


RowItemT = TypeVar("RowItemT")


class InheritedTableSection:
    def __init__(
        self,
        *,
        parent: QtWidgets.QWidget,
        title: str,
        headers: list[str],
        default_widths: list[int],
        editable_columns: set[int],
        default_edit_rows: int,
        style_item: Callable[[QtWidgets.QTableWidgetItem, str], None],
        section_layout_configurer: Callable[[QtWidgets.QLayout], None],
        add_handler,
        remove_handler,
        revert_handler,
        add_label: str = "Add Row",
        remove_label: str = "Delete Selected Rows",
        revert_label: str = "Revert Selected",
    ) -> None:
        self._style_item = style_item
        self._editable_columns = editable_columns
        self._default_edit_rows = default_edit_rows
        self.rows_meta: list[DisplayRow] = []

        self.group = QtWidgets.QGroupBox(title, parent)
        self.group.setObjectName("sectionCard")
        layout = QtWidgets.QVBoxLayout(self.group)
        section_layout_configurer(layout)

        self.table = create_editor_table(
            parent,
            headers,
            editable=True,
            default_widths=default_widths,
            expand_on_paste=True,
            show_row_header=True,
        )
        layout.addWidget(self.table)
        layout.addSpacing(4)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setSpacing(8)
        buttons.setContentsMargins(0, 4, 0, 0)
        self.add_button = QtWidgets.QPushButton(add_label, self.group)
        self.remove_button = QtWidgets.QPushButton(remove_label, self.group)
        self.revert_button = QtWidgets.QPushButton(revert_label, self.group)
        self.add_button.clicked.connect(add_handler)
        self.remove_button.clicked.connect(remove_handler)
        self.revert_button.clicked.connect(revert_handler)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.revert_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

    def refresh_from_items(
        self,
        *,
        is_base_case: bool,
        base_items: list[RowItemT],
        local_items: list[RowItemT],
        values_for_item: Callable[[RowItemT], list[str]],
        key_for_item: Callable[[RowItemT], tuple[str, ...]],
        row_id_for_item: Callable[[RowItemT], str],
        base_row_id_for_item: Callable[[RowItemT], str],
    ) -> None:
        rows = build_inherited_rows(
            is_base_case=is_base_case,
            base_items=base_items,
            local_items=local_items,
            values_for_item=values_for_item,
            key_for_item=key_for_item,
            row_id_for_item=row_id_for_item,
            base_row_id_for_item=base_row_id_for_item,
            editable_columns=self._editable_columns,
        )
        self.rows_meta = rows
        row_count = len(rows) if rows else self._default_edit_rows
        self.table.setRowCount(row_count)
        blank_values = [""] * self.table.columnCount()
        for row in range(row_count):
            meta = rows[row] if row < len(rows) else DisplayRow(blank_values[:], status="plain")
            for col, value in enumerate(meta.values):
                self._set_table_item(row, col, value, editable=meta.is_editable(col), status=meta.status)
            self._set_row_header(row, row + 1)

    def refresh_statuses_from_current(self) -> None:
        refresh_inherited_table_statuses(
            table=self.table,
            rows_meta=self.rows_meta,
            column_count=self.table.columnCount(),
            apply_item_style=self._style_item,
        )

    def read_rows(
        self,
        *,
        is_base_case: bool,
        base_items: list[RowItemT],
        values_for_item: Callable[[RowItemT], list[str]],
        key_for_item: Callable[[RowItemT], tuple[str, ...]],
        row_id_for_item: Callable[[RowItemT], str],
        create_row,
        new_row_id,
    ) -> list[RowItemT]:
        return read_inherited_rows(
            is_base_case=is_base_case,
            table=self.table,
            rows_meta=self.rows_meta,
            column_count=self.table.columnCount(),
            base_items=base_items,
            values_for_item=values_for_item,
            key_for_item=key_for_item,
            row_id_for_item=row_id_for_item,
            create_row=create_row,
            new_row_id=new_row_id,
        )

    def add_blank_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col in range(self.table.columnCount()):
            self._set_table_item(row, col, "", editable=True, status="plain")
        self.rows_meta.append(DisplayRow([""] * self.table.columnCount(), status="plain"))
        self._set_row_header(row, row + 1)

    def remove_or_revert_selected(self) -> None:
        rows = self.selected_rows()
        if not rows:
            return
        updated_meta = list(self.rows_meta)
        for row in rows:
            meta = updated_meta[row] if row < len(updated_meta) else DisplayRow([""] * self.table.columnCount(), status="plain")
            if meta.base_values is not None:
                for col, value in enumerate(meta.base_values):
                    self._set_table_item(row, col, value, editable=meta.is_editable(col), status="inherited")
                updated_meta[row] = DisplayRow(
                    meta.base_values,
                    status="inherited",
                    editable_columns=self._editable_columns,
                    base_values=meta.base_values,
                    row_id=meta.row_id,
                    base_row_id=meta.base_row_id,
                )
                continue
            self.table.removeRow(row)
            if row < len(updated_meta):
                del updated_meta[row]
        self.rows_meta = updated_meta
        self._renumber_headers()

    def revert_selected(self) -> None:
        rows = self.selected_rows()
        if not rows:
            return
        updated_meta = list(self.rows_meta)
        for row in rows:
            meta = updated_meta[row] if row < len(updated_meta) else None
            if meta is None:
                continue
            if meta.base_values is not None:
                for col, value in enumerate(meta.base_values):
                    self._set_table_item(row, col, value, editable=meta.is_editable(col), status="inherited")
                meta.status = "inherited"
            else:
                self.table.removeRow(row)
                if row < len(updated_meta):
                    del updated_meta[row]
        self.rows_meta = updated_meta
        self._renumber_headers()

    def has_actionable_selection(self, *, allow_plain_rows: bool = True) -> bool:
        for row in self.selected_rows():
            meta = self.rows_meta[row] if row < len(self.rows_meta) else DisplayRow([""] * self.table.columnCount(), status="plain")
            if meta.base_values is None:
                if allow_plain_rows:
                    return True
                continue
            for col in self._editable_columns:
                if self.text(row, col) != meta.base_values[col]:
                    return True
        return False

    def selected_rows(self) -> list[int]:
        selected_indexes = self.table.selectedIndexes()
        if selected_indexes:
            return sorted({index.row() for index in selected_indexes}, reverse=True)
        rows = self.table.selectionModel().selectedRows()
        return sorted((item.row() for item in rows), reverse=True)

    def text(self, row: int, col: int) -> str:
        item = self.table.item(row, col)
        return item.text().strip() if item is not None else ""

    def adjust_height(self, *, visible_rows: int, allow_internal_scroll: bool = True) -> None:
        row_count = self.table.rowCount()
        if row_count <= 0:
            row_count = 1
        display_rows = min(row_count, visible_rows)
        self.table.resizeRowsToContents()
        header_height = self.table.horizontalHeader().height() if not self.table.horizontalHeader().isHidden() else 0
        rows_height = sum(self.table.rowHeight(row) for row in range(display_rows))
        frame_height = self.table.frameWidth() * 2
        padding = 4
        required_height = header_height + rows_height + frame_height + padding
        use_internal_scroll = allow_internal_scroll and self.table.rowCount() > visible_rows
        self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded if use_internal_scroll else QtCore.Qt.ScrollBarAlwaysOff)
        self.table.setFixedHeight(required_height)

    def _set_table_item(
        self,
        row: int,
        col: int,
        value: str,
        *,
        editable: bool = True,
        status: str = "plain",
    ) -> None:
        item = self.table.item(row, col)
        if item is None:
            item = QtWidgets.QTableWidgetItem()
            self.table.setItem(row, col, item)
        item.setText(value)
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if editable:
            flags |= QtCore.Qt.ItemIsEditable
        item.setFlags(flags)
        self._style_item(item, status)

    def _set_row_header(self, row: int, value: int) -> None:
        header_item = self.table.verticalHeaderItem(row)
        if header_item is None:
            header_item = QtWidgets.QTableWidgetItem()
            self.table.setVerticalHeaderItem(row, header_item)
        header_item.setText(str(value))

    def _renumber_headers(self) -> None:
        for row in range(self.table.rowCount()):
            self._set_row_header(row, row + 1)
