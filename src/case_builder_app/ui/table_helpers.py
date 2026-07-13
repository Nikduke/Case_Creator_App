from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from PySide6 import QtCore, QtGui, QtWidgets


EDITOR_TABLE_STYLESHEET = """
QTableWidget#editorTable {
    background: #ffffff;
    border: 1px solid #d7e0e6;
    border-radius: 6px;
    gridline-color: #e5ebf0;
    selection-background-color: #d8e8f5;
    selection-color: #24343d;
}
QTableWidget#editorTable::item {
    padding: 6px 8px;
}
QHeaderView::section {
    background: #f4f7f9;
    color: #31424d;
    font-weight: 600;
    padding: 8px 10px;
    border-top: 0px;
    border-left: 0px;
    border-right: 1px solid #dbe4ea;
    border-bottom: 2px solid #c8d4dc;
}
QTableWidget QHeaderView::section:vertical {
    background: #f7f9fb;
    color: #5c6c77;
    border-right: 1px solid #dbe4ea;
    border-bottom: 1px solid #dbe4ea;
}
QTableCornerButton::section {
    background: #f4f7f9;
    border-top: 0px;
    border-left: 0px;
    border-right: 1px solid #dbe4ea;
    border-bottom: 2px solid #c8d4dc;
}
"""


@dataclass
class DisplayRow:
    values: list[str]
    status: str = "plain"
    editable_columns: set[int] | None = None
    base_values: list[str] | None = None
    row_id: str = ""
    base_row_id: str = ""

    def is_editable(self, column: int) -> bool:
        if self.editable_columns is None:
            return True
        return column in self.editable_columns


class ComboBoxDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, options: list[str], parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.options = options

    def createEditor(self, parent, option, index):  # noqa: ANN001
        editor = QtWidgets.QComboBox(parent)
        editor.addItems(self.options)
        persistent_index = QtCore.QPersistentModelIndex(index)
        QtCore.QTimer.singleShot(0, editor.showPopup)
        editor.activated.connect(lambda _index: self._commit_combo(editor, persistent_index))
        return editor

    def setEditorData(self, editor, index):  # noqa: ANN001
        if not isinstance(editor, QtWidgets.QComboBox):
            return
        value = str(index.data() or "")
        current_index = editor.findText(value)
        if current_index >= 0:
            editor.setCurrentIndex(current_index)

    def setModelData(self, editor, model, index):  # noqa: ANN001
        if not isinstance(editor, QtWidgets.QComboBox):
            return
        model.setData(index, editor.currentText())

    def _commit_combo(self, editor: QtWidgets.QComboBox, index: QtCore.QPersistentModelIndex) -> None:
        model = index.model()
        if model is not None and index.isValid():
            model.setData(index, editor.currentText(), QtCore.Qt.EditRole)
        self.closeEditor.emit(editor, QtWidgets.QAbstractItemDelegate.NoHint)


class SuggestionDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, suggestions_getter, parent: QtWidgets.QWidget | None = None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.suggestions_getter = suggestions_getter

    def createEditor(self, parent, option, index):  # noqa: ANN001
        editor = QtWidgets.QLineEdit(parent)
        suggestions = self.suggestions_getter(index)
        completer = QtWidgets.QCompleter(suggestions, editor)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setFilterMode(QtCore.Qt.MatchContains)
        editor.setCompleter(completer)
        return editor

    def setEditorData(self, editor, index):  # noqa: ANN001
        if isinstance(editor, QtWidgets.QLineEdit):
            editor.setText(str(index.data() or ""))

    def setModelData(self, editor, model, index):  # noqa: ANN001
        if isinstance(editor, QtWidgets.QLineEdit):
            model.setData(index, editor.text())


class EditableCellTable(QtWidgets.QTableWidget):
    def __init__(self, *args, expand_on_paste: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.expand_on_paste = expand_on_paste

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.matches(QtGui.QKeySequence.Cut):
            self.copy_selected_cells()
            self.clear_selected_cells()
            event.accept()
            return
        if event.matches(QtGui.QKeySequence.Copy):
            self.copy_selected_cells()
            event.accept()
            return
        if event.matches(QtGui.QKeySequence.Paste):
            self.paste_cells_from_clipboard()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        index = self.indexAt(event.position().toPoint())
        super().mousePressEvent(event)
        if not index.isValid() or event.button() != QtCore.Qt.LeftButton:
            return
        if not self._is_cell_editable(index.row(), index.column()):
            return
        delegate = self._delegate_for_index(index)
        if isinstance(delegate, ComboBoxDelegate):
            self.edit(index)

    def copy_selected_cells(self) -> None:
        selected = self.selectedIndexes()
        if selected:
            selected_coords = {(index.row(), index.column()) for index in selected}
            min_row = min(index.row() for index in selected)
            max_row = max(index.row() for index in selected)
            min_col = min(index.column() for index in selected)
            max_col = max(index.column() for index in selected)
        elif self.currentRow() >= 0 and self.currentColumn() >= 0:
            selected_coords = {(self.currentRow(), self.currentColumn())}
            min_row = max_row = self.currentRow()
            min_col = max_col = self.currentColumn()
        else:
            return

        clipboard_rows = []
        for row in range(min_row, max_row + 1):
            values = []
            for col in range(min_col, max_col + 1):
                values.append(self._cell_text(row, col) if (row, col) in selected_coords else "")
            clipboard_rows.append("\t".join(values))
        QtWidgets.QApplication.clipboard().setText("\n".join(clipboard_rows))

    def paste_cells_from_clipboard(self) -> None:
        text = QtWidgets.QApplication.clipboard().text()
        if not text.strip():
            return

        parsed_rows = [line.split("\t") for line in text.splitlines()]
        if not parsed_rows:
            return

        current = self.currentIndex()
        if current.isValid():
            start_row = current.row()
            start_col = current.column()
        else:
            selected = self.selectedIndexes()
            if selected:
                start_row = min(index.row() for index in selected)
                start_col = min(index.column() for index in selected)
            else:
                start_row = 0
                start_col = 0

        for row_offset, values in enumerate(parsed_rows):
            row = start_row + row_offset
            if row >= self.rowCount() and not self.expand_on_paste:
                break
            self._ensure_row_exists(row)
            for col_offset, value in enumerate(values):
                col = start_col + col_offset
                if col >= self.columnCount():
                    continue
                if not self._is_cell_editable(row, col):
                    continue
                self._set_item_text(row, col, value.strip())

    def clear_selected_cells(self) -> None:
        selected = self.selectedIndexes()
        if not selected and self.currentRow() >= 0 and self.currentColumn() >= 0:
            selected = [self.model().index(self.currentRow(), self.currentColumn())]
        for index in selected:
            if not self._is_cell_editable(index.row(), index.column()):
                continue
            self._set_item_text(index.row(), index.column(), "")

    def _ensure_row_exists(self, row: int) -> None:
        if not self.expand_on_paste:
            return
        while self.rowCount() <= row:
            self.insertRow(self.rowCount())

    def _is_cell_editable(self, row: int, col: int) -> bool:
        item = self.item(row, col)
        if item is None:
            return True
        return bool(item.flags() & QtCore.Qt.ItemIsEditable)

    def _set_item_text(self, row: int, col: int, value: str) -> None:
        item = self.item(row, col)
        if item is None:
            item = QtWidgets.QTableWidgetItem()
            self.setItem(row, col, item)
        item.setText(value)

    def _cell_text(self, row: int, col: int) -> str:
        item = self.item(row, col)
        return item.text().strip() if item is not None else ""

    def _delegate_for_index(self, index: QtCore.QModelIndex) -> QtWidgets.QAbstractItemDelegate | None:
        return self.itemDelegateForRow(index.row()) or self.itemDelegateForColumn(index.column())


def create_editor_table(
    parent: QtWidgets.QWidget,
    headers: list[str],
    *,
    editable: bool = False,
    default_widths: list[int] | None = None,
    expand_on_paste: bool = True,
    show_row_header: bool = False,
) -> QtWidgets.QTableWidget:
    if editable:
        table = EditableCellTable(0, len(headers), parent, expand_on_paste=expand_on_paste)
    else:
        table = QtWidgets.QTableWidget(0, len(headers), parent)
    table.setHorizontalHeaderLabels(headers)
    vertical_header = table.verticalHeader()
    vertical_header.setVisible(show_row_header)
    vertical_header.setDefaultAlignment(QtCore.Qt.AlignCenter)
    vertical_header.setSectionsClickable(True)
    if show_row_header:
        vertical_header.setFixedWidth(30)
    table.setObjectName("editorTable")
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems if editable else QtWidgets.QAbstractItemView.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection if editable else QtWidgets.QAbstractItemView.SingleSelection)
    if editable:
        table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.EditKeyPressed
            | QtWidgets.QAbstractItemView.AnyKeyPressed
        )
    else:
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    header = table.horizontalHeader()
    header.setStretchLastSection(True)
    header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
    header.setMinimumSectionSize(90)
    vertical_header.setDefaultSectionSize(34)
    vertical_header.setMinimumSectionSize(34)
    table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    if default_widths is not None:
        for column, width in enumerate(default_widths):
            table.setColumnWidth(column, width)
    return table


RowItemT = TypeVar("RowItemT")


def _normalize_values(values: list[str]) -> list[str]:
    return [value.strip() for value in values]


def _normalized_key(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value.strip() for value in values)


def build_inherited_rows(
    *,
    is_base_case: bool,
    base_items: list[RowItemT],
    local_items: list[RowItemT],
    values_for_item: Callable[[RowItemT], list[str]],
    key_for_item: Callable[[RowItemT], tuple[str, ...]],
    row_id_for_item: Callable[[RowItemT], str],
    base_row_id_for_item: Callable[[RowItemT], str],
    editable_columns: set[int],
) -> list[DisplayRow]:
    if is_base_case:
        return [
            DisplayRow(values_for_item(item), status="base", row_id=row_id_for_item(item))
            for item in local_items
        ]

    rows: list[DisplayRow] = []
    base_keys = {_normalized_key(key_for_item(item)) for item in base_items}
    base_ids = {row_id_for_item(item) for item in base_items}
    local_map = {
        _normalized_key(key_for_item(item)): item
        for item in local_items
        if any(_normalize_values(values_for_item(item)))
    }
    local_by_base = {
        base_row_id_for_item(item): item
        for item in local_items
        if base_row_id_for_item(item).strip()
    }

    for base_item in base_items:
        base_values = values_for_item(base_item)
        local_entry = local_by_base.get(row_id_for_item(base_item)) or local_map.get(_normalized_key(key_for_item(base_item)))
        if local_entry is None:
            current_values = list(base_values)
        else:
            current_values = [
                local_value or base_value
                for local_value, base_value in zip(values_for_item(local_entry), base_values)
            ]
        status = "overridden" if current_values != base_values else "inherited"
        rows.append(
            DisplayRow(
                current_values,
                status=status,
                editable_columns=editable_columns,
                base_values=base_values,
                row_id=row_id_for_item(local_entry) if local_entry is not None else row_id_for_item(base_item),
                base_row_id=row_id_for_item(base_item),
            )
        )

    for item in local_items:
        base_row_id = base_row_id_for_item(item).strip()
        if base_row_id and base_row_id in base_ids:
            continue
        if _normalized_key(key_for_item(item)) in base_keys:
            continue
        values = values_for_item(item)
        if not any(_normalize_values(values)):
            continue
        rows.append(
            DisplayRow(
                values,
                status="added",
                editable_columns=editable_columns,
                row_id=row_id_for_item(item),
            )
        )

    return rows


def refresh_inherited_table_statuses(
    *,
    table: QtWidgets.QTableWidget,
    rows_meta: list[DisplayRow],
    column_count: int,
    apply_item_style: Callable[[QtWidgets.QTableWidgetItem, str], None],
) -> None:
    for row in range(table.rowCount()):
        meta = rows_meta[row] if row < len(rows_meta) else DisplayRow([""] * column_count, status="plain")
        current_values = []
        for col in range(column_count):
            item = table.item(row, col)
            current_values.append(item.text().strip() if item is not None else "")
        if meta.base_values is not None:
            status = "overridden" if current_values != meta.base_values else "inherited"
        elif any(current_values):
            status = "added"
        else:
            status = "plain"
        meta.status = status
        for col in range(column_count):
            item = table.item(row, col)
            if item is not None:
                apply_item_style(item, status)


def read_inherited_rows(
    *,
    is_base_case: bool,
    table: QtWidgets.QTableWidget,
    rows_meta: list[DisplayRow],
    column_count: int,
    base_items: list[RowItemT],
    values_for_item: Callable[[RowItemT], list[str]],
    key_for_item: Callable[[RowItemT], tuple[str, ...]],
    row_id_for_item: Callable[[RowItemT], str],
    create_row: Callable[[str, str, list[str], list[str] | None], RowItemT],
    new_row_id: Callable[[], str],
) -> list[RowItemT]:
    def current_values_for_row(row: int) -> list[str]:
        values: list[str] = []
        for col in range(column_count):
            item = table.item(row, col)
            values.append(item.text().strip() if item is not None else "")
        return values

    rows: list[RowItemT] = []
    if is_base_case:
        for row in range(table.rowCount()):
            meta = rows_meta[row] if row < len(rows_meta) else DisplayRow([""] * column_count, status="plain")
            values = current_values_for_row(row)
            if not any(values):
                continue
            rows.append(create_row(meta.row_id or new_row_id(), "", values, None))
        return rows

    base_items_by_key = {_normalized_key(key_for_item(item)): item for item in base_items}
    for row in range(table.rowCount()):
        meta = rows_meta[row] if row < len(rows_meta) else DisplayRow([""] * column_count, status="plain")
        values = current_values_for_row(row)
        if meta.base_values is not None:
            if values != meta.base_values:
                rows.append(create_row(meta.row_id or new_row_id(), meta.base_row_id, values, meta.base_values))
            continue

        if not any(values):
            continue

        base_match = base_items_by_key.get(_normalized_key(tuple(values)))
        if base_match is not None:
            base_values = values_for_item(base_match)
            if values != base_values:
                rows.append(create_row(meta.row_id or new_row_id(), row_id_for_item(base_match), values, base_values))
            continue

        rows.append(create_row(meta.row_id or new_row_id(), "", values, None))

    return rows
