from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from case_builder_app.models import CasePart, Project
from case_builder_app.services.text_tokens import join_multiline, parse_token_text


class CasePartDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None, case_part: CasePart | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Case Part")
        self.resize(480, 360)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.label_edit = QtWidgets.QLineEdit(self)
        self.values_edit = QtWidgets.QPlainTextEdit(self)
        self.values_edit.setPlaceholderText("Enter values separated by commas, semicolons, tabs, or new lines.")
        form.addRow("Label", self.label_edit)
        form.addRow("Values", self.values_edit)
        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if case_part is not None:
            self.label_edit.setText(case_part.label)
            self.values_edit.setPlainText(join_multiline([item.token for item in case_part.values]))

    def get_data(self) -> tuple[str, list[str]]:
        return self.label_edit.text().strip(), parse_token_text(self.values_edit.toPlainText())


class TokenDialog(QtWidgets.QDialog):
    def __init__(self, title: str, label: str, initial: str = "", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 240)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.edit = QtWidgets.QPlainTextEdit(self)
        self.edit.setPlaceholderText("Enter one or more values separated by commas, semicolons, tabs, or new lines.")
        self.edit.setPlainText(initial)
        form.addRow(label, self.edit)
        layout.addLayout(form)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def tokens(self) -> list[str]:
        return parse_token_text(self.edit.toPlainText())


class CaseNameOrderDialog(QtWidgets.QDialog):
    def __init__(self, project: Project, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Case Name Order")
        self.resize(520, 420)

        layout = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "Move case parts to control generated case names only. Application order on the left stays unchanged.",
            self,
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.order_list = QtWidgets.QListWidget(self)
        self.order_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.order_list.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.order_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.order_list.model().rowsMoved.connect(lambda *_args: self._update_preview())
        layout.addWidget(self.order_list, 1)

        actions_layout = QtWidgets.QHBoxLayout()
        self.up_button = QtWidgets.QPushButton("Up", self)
        self.down_button = QtWidgets.QPushButton("Down", self)
        self.reset_button = QtWidgets.QPushButton("Reset to application order", self)
        actions_layout.addWidget(self.up_button)
        actions_layout.addWidget(self.down_button)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self.reset_button)
        layout.addLayout(actions_layout)

        self.preview_label = QtWidgets.QLabel(self)
        self.preview_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.preview_label)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.up_button.clicked.connect(lambda: self._move_selected(-1))
        self.down_button.clicked.connect(lambda: self._move_selected(1))
        self.reset_button.clicked.connect(self._reset_to_application_order)

        self._populate(self.project.case_parts_in_name_order())

    def get_order(self) -> list[str]:
        return [
            str(self.order_list.item(row).data(QtCore.Qt.UserRole))
            for row in range(self.order_list.count())
        ]

    def _populate(self, case_parts: list[CasePart]) -> None:
        self.order_list.clear()
        for case_part in case_parts:
            text = case_part.label.strip() or "(unnamed case part)"
            item = QtWidgets.QListWidgetItem(text)
            item.setData(QtCore.Qt.UserRole, case_part.id)
            self.order_list.addItem(item)
        if self.order_list.count():
            self.order_list.setCurrentRow(0)
        self._update_preview()

    def _move_selected(self, direction: int) -> None:
        row = self.order_list.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= self.order_list.count():
            return
        item = self.order_list.takeItem(row)
        self.order_list.insertItem(target, item)
        self.order_list.setCurrentRow(target)
        self._update_preview()

    def _reset_to_application_order(self) -> None:
        self._populate(self.project.case_parts)

    def _update_preview(self) -> None:
        token_by_case_part = {
            case_part.id: case_part.values[0].token.strip()
            for case_part in self.project.case_parts
            if case_part.values and case_part.values[0].token.strip()
        }
        tokens: list[str] = []
        base_token = self.project.base_case.token.strip()
        if self.project.base_case.include_in_case_name and base_token:
            tokens.append(base_token)
        tokens.extend(
            token_by_case_part[case_part_id]
            for case_part_id in self.get_order()
            if case_part_id in token_by_case_part
        )
        preview = "_".join(tokens) if tokens else "(no generated case parts yet)"
        self.preview_label.setText(f"Preview: {preview}")
