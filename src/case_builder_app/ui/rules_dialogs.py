from __future__ import annotations

from copy import deepcopy

from PySide6 import QtCore, QtWidgets

from case_builder_app.models import ExclusionCombination, Project, RuleClause
from case_builder_app.services.exclusion_parser import parse_exclusion_text
from case_builder_app.ui.table_helpers import EDITOR_TABLE_STYLESHEET, create_editor_table


class ExclusionsDialog(QtWidgets.QDialog):
    def __init__(self, project: Project, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.combinations = deepcopy(project.exclusions)
        self.setWindowTitle("Excluded Combinations")
        self.resize(1080, 620)
        self.setStyleSheet(EDITOR_TABLE_STYLESHEET)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        hint = QtWidgets.QLabel(
            "Each row is one excluded combination. Fill the case-part values that must be present; leave other cells blank.",
            self,
        )
        hint.setWordWrap(True)
        hint.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        layout.addWidget(hint)

        import_row = QtWidgets.QHBoxLayout()
        import_row.setSpacing(10)
        self.entry_edit = QtWidgets.QPlainTextEdit(self)
        self.entry_edit.setPlaceholderText(
            "Paste one or more exclusions. Use spaces, commas, semicolons, tabs, or new lines.\n"
            "Examples: S1 V1 V3   or   S1, V1, V3, S2, V2, V3"
        )
        self.entry_edit.setFixedHeight(64)
        self.import_button = QtWidgets.QPushButton("Add Pasted", self)
        import_row.addWidget(self.entry_edit, 1)
        import_row.addWidget(self.import_button)
        layout.addLayout(import_row)

        self.table = create_editor_table(
            self,
            [case_part.label for case_part in self.project.case_parts],
            editable=True,
            expand_on_paste=True,
        )
        self.table.setMinimumHeight(300)
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
        if len(self.project.case_parts) <= 6:
            self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
            self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        else:
            self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        layout.addWidget(self.table, 1)

        buttons_row = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton("Add Row", self)
        self.remove_button = QtWidgets.QPushButton("Delete Selected", self)
        self.import_button.clicked.connect(self._add_from_text)
        self.add_button.clicked.connect(self._add_blank_row)
        self.remove_button.clicked.connect(self._remove_selected_rows)
        buttons_row.addWidget(self.add_button)
        buttons_row.addWidget(self.remove_button)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        dlg_buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        dlg_buttons.accepted.connect(self._accept_if_valid)
        dlg_buttons.rejected.connect(self.reject)
        layout.addWidget(dlg_buttons)

        self.table.itemSelectionChanged.connect(self._update_actions)
        self.entry_edit.textChanged.connect(self._update_actions)
        self._refresh()
        self._update_actions()

    def _refresh(self) -> None:
        self.table.setRowCount(len(self.combinations))
        for row, combination in enumerate(self.combinations):
            values_by_case_part = {clause.case_part_id: self._token_for_clause(clause) for clause in combination.clauses}
            for column, case_part in enumerate(self.project.case_parts):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem(values_by_case_part.get(case_part.id, "")))
        self.table.resizeRowsToContents()
        self._update_actions()

    def _show_error(self, message: str) -> None:
        QtWidgets.QMessageBox.warning(self, "Invalid Exclusion", message)

    def _add_from_text(self) -> None:
        try:
            combinations = parse_exclusion_text(self.project, self.entry_edit.toPlainText())
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self.combinations.extend(combinations)
        self.entry_edit.clear()
        self._refresh()
        if self.combinations:
            self.table.selectRow(len(self.combinations) - 1)

    def _add_blank_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column in range(self.table.columnCount()):
            self.table.setItem(row, column, QtWidgets.QTableWidgetItem(""))
        self.table.setCurrentCell(row, 0)
        self._update_actions()

    def _remove_selected_rows(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for row in rows:
            self.table.removeRow(row)
        self._update_actions()

    def _accept_if_valid(self) -> None:
        try:
            self.combinations = self._read_table()
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self.accept()

    def _update_actions(self) -> None:
        has_text = bool(self.entry_edit.toPlainText().strip())
        has_selection = bool(self.table.selectedIndexes())
        self.import_button.setEnabled(has_text)
        self.add_button.setEnabled(bool(self.project.case_parts))
        self.remove_button.setEnabled(has_selection)

    def get_combinations(self) -> list[ExclusionCombination]:
        return self.combinations

    def _read_table(self) -> list[ExclusionCombination]:
        combinations: list[ExclusionCombination] = []
        for row in range(self.table.rowCount()):
            clauses: list[RuleClause] = []
            for column, case_part in enumerate(self.project.case_parts):
                token = self._cell_text(row, column)
                if not token:
                    continue
                value = next((item for item in case_part.values if item.token == token), None)
                if value is None:
                    raise ValueError(f"Unknown value '{token}' for case part '{case_part.label}' on row {row + 1}.")
                clauses.append(RuleClause(case_part_id=case_part.id, value_id=value.id))
            if clauses:
                combinations.append(ExclusionCombination(clauses=clauses))
        return combinations

    def _cell_text(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""

    def _token_for_clause(self, clause: RuleClause) -> str:
        value = self.project.find_value(clause.case_part_id, clause.value_id)
        return value.token if value is not None else ""
