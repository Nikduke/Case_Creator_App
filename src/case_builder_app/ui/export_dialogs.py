from __future__ import annotations

from copy import deepcopy

from PySide6 import QtCore, QtWidgets

from case_builder_app.models import SelectedCaseList
from case_builder_app.services.text_tokens import parse_token_text


class SelectedCasesExportDialog(QtWidgets.QDialog):
    def __init__(
        self,
        available_case_names: list[str],
        selected_case_lists: list[SelectedCaseList],
        *,
        simple_export_enabled: bool,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Selected Cases")
        self.resize(680, 520)
        self._available_case_names = list(available_case_names)
        self._available_case_name_set = set(available_case_names)
        self._saved_lists = deepcopy(selected_case_lists)
        self._selected_names: list[str] = []
        self._saved_lists_changed = False
        self._validation_timer = QtCore.QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.setInterval(200)

        layout = QtWidgets.QVBoxLayout(self)

        intro = QtWidgets.QLabel(
            "Paste case names from the current checked project. One workbook will be exported with matched cases in pasted order.",
            self,
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        saved_layout = QtWidgets.QHBoxLayout()
        saved_layout.addWidget(QtWidgets.QLabel("Saved list", self))
        self.saved_list_combo = QtWidgets.QComboBox(self)
        saved_layout.addWidget(self.saved_list_combo, 1)
        self.save_button = QtWidgets.QPushButton("Save/Update", self)
        self.save_as_button = QtWidgets.QPushButton("Save As...", self)
        self.delete_button = QtWidgets.QPushButton("Delete", self)
        saved_layout.addWidget(self.save_button)
        saved_layout.addWidget(self.save_as_button)
        saved_layout.addWidget(self.delete_button)
        layout.addLayout(saved_layout)

        self.names_edit = QtWidgets.QPlainTextEdit(self)
        self.names_edit.setPlaceholderText("Paste case names to export...")
        layout.addWidget(self.names_edit, 1)

        options_layout = QtWidgets.QHBoxLayout()
        self.simple_export_checkbox = QtWidgets.QCheckBox("Simple export", self)
        self.simple_export_checkbox.setChecked(simple_export_enabled)
        options_layout.addWidget(self.simple_export_checkbox)
        options_layout.addStretch(1)
        layout.addLayout(options_layout)

        self.summary_label = QtWidgets.QLabel("Matched: 0 | Missing: 0 | Duplicates ignored: 0", self)
        layout.addWidget(self.summary_label)

        self.missing_group = QtWidgets.QGroupBox("Missing case names", self)
        missing_layout = QtWidgets.QVBoxLayout(self.missing_group)
        self.missing_text = QtWidgets.QPlainTextEdit(self.missing_group)
        self.missing_text.setReadOnly(True)
        self.missing_text.setPlaceholderText("All pasted case names match the current checked project.")
        missing_layout.addWidget(self.missing_text)
        self.missing_group.setVisible(False)
        layout.addWidget(self.missing_group)

        buttons_row = QtWidgets.QHBoxLayout()
        self.check_button = QtWidgets.QPushButton("Check List", self)
        buttons_row.addWidget(self.check_button)
        buttons_row.addStretch(1)
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel, self)
        self.export_button = self.button_box.addButton("Export", QtWidgets.QDialogButtonBox.AcceptRole)
        self.export_button.setEnabled(False)
        buttons_row.addWidget(self.button_box)
        layout.addLayout(buttons_row)

        self.names_edit.textChanged.connect(lambda: self._validation_timer.start())
        self.saved_list_combo.currentIndexChanged.connect(self._load_selected_saved_list)
        self.save_button.clicked.connect(self._save_current_list)
        self.save_as_button.clicked.connect(self._save_current_list_as)
        self.delete_button.clicked.connect(self._delete_current_list)
        self.check_button.clicked.connect(self._validate)
        self._validation_timer.timeout.connect(self._validate)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self._populate_saved_list_combo()
        self._validate()

    def selected_names(self) -> list[str]:
        return list(self._selected_names)

    def simple_export_enabled(self) -> bool:
        return self.simple_export_checkbox.isChecked()

    def selected_case_lists(self) -> list[SelectedCaseList]:
        return deepcopy(self._saved_lists)

    def saved_lists_changed(self) -> bool:
        return self._saved_lists_changed

    def _validate(self) -> None:
        parsed_names = parse_token_text(self.names_edit.toPlainText())
        seen: set[str] = set()
        selected_names: list[str] = []
        missing_names: list[str] = []
        duplicate_count = 0

        for name in parsed_names:
            if name in seen:
                duplicate_count += 1
                continue
            seen.add(name)
            if name in self._available_case_name_set:
                selected_names.append(name)
            else:
                missing_names.append(name)

        self._selected_names = selected_names
        self.summary_label.setText(
            f"Matched: {len(selected_names)} | Missing: {len(missing_names)} | Duplicates ignored: {duplicate_count}"
        )
        self.missing_text.setPlainText("\n".join(missing_names))
        self.missing_group.setVisible(bool(missing_names))
        self.export_button.setEnabled(bool(selected_names))

    def accept(self) -> None:
        self._validate()
        if not self._selected_names:
            return
        super().accept()

    def _current_saved_list_id(self) -> str:
        return str(self.saved_list_combo.currentData() or "")

    def _find_saved_list(self, list_id: str) -> SelectedCaseList | None:
        return next((item for item in self._saved_lists if item.id == list_id), None)

    def _populate_saved_list_combo(self, selected_id: str = "") -> None:
        with QtCore.QSignalBlocker(self.saved_list_combo):
            self.saved_list_combo.clear()
            for saved_list in self._saved_lists:
                label = saved_list.name.strip() or "(unnamed list)"
                self.saved_list_combo.addItem(label, saved_list.id)
            if not self._saved_lists:
                self.saved_list_combo.addItem("(no saved lists)", "")
        self.delete_button.setEnabled(bool(self._saved_lists))
        self.save_button.setEnabled(bool(self._saved_lists))

        if self._saved_lists:
            ids = [item.id for item in self._saved_lists]
            target_id = selected_id if selected_id in ids else ids[0]
            self.saved_list_combo.setCurrentIndex(ids.index(target_id))
            self._load_selected_saved_list()

    def _load_selected_saved_list(self) -> None:
        saved_list = self._find_saved_list(self._current_saved_list_id())
        if saved_list is None:
            return
        self.names_edit.setPlainText("\n".join(saved_list.case_names))
        self._validate()

    def _unique_current_names(self) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        for name in parse_token_text(self.names_edit.toPlainText()):
            if name in seen:
                continue
            seen.add(name)
            names.append(name)
        return names

    def _save_current_list(self) -> None:
        saved_list = self._find_saved_list(self._current_saved_list_id())
        if saved_list is None:
            self._save_current_list_as()
            return
        saved_list.case_names = self._unique_current_names()
        self._saved_lists_changed = True
        self._populate_saved_list_combo(saved_list.id)

    def _save_current_list_as(self) -> None:
        name, accepted = QtWidgets.QInputDialog.getText(self, "Save Selected Case List", "List name")
        if not accepted:
            return
        name = name.strip()
        if not name:
            return
        saved_list = SelectedCaseList(name=name, case_names=self._unique_current_names())
        self._saved_lists.append(saved_list)
        self._saved_lists_changed = True
        self._populate_saved_list_combo(saved_list.id)

    def _delete_current_list(self) -> None:
        list_id = self._current_saved_list_id()
        saved_list = self._find_saved_list(list_id)
        if saved_list is None:
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            "Delete Saved List",
            f"Delete saved list '{saved_list.name}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if answer != QtWidgets.QMessageBox.Yes:
            return
        self._saved_lists = [item for item in self._saved_lists if item.id != list_id]
        self._saved_lists_changed = True
        self._populate_saved_list_combo()
