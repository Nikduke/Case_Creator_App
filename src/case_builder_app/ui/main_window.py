from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from case_builder_app.models import CasePart, CaseValue, Project
from case_builder_app.services.generator import GenerationService, GeneratedCase, GenerationStats
from case_builder_app.services.persistence import PersistenceService
from case_builder_app.services.validation import ValidationService
from case_builder_app.ui.changes_editor import ChangesEditor
from case_builder_app.ui.common import CaseNameOrderDialog, CasePartDialog, TokenDialog
from case_builder_app.ui.project_document import ProjectDocumentController
from case_builder_app.ui.project_selection import ProjectSelectionController
from case_builder_app.ui.project_structure import ProjectStructureController


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent: QtWidgets.QWidget | None = None, app_icon: QtGui.QIcon | None = None) -> None:
        super().__init__(parent)
        self.project = Project()
        self.project_path: Path | None = None
        self.generated_cases: list[GeneratedCase] = []
        self.generation_stats = GenerationStats()
        self._loading_value = False
        self._is_checked = False
        self._is_dirty = False
        self._project_notice_timer = QtCore.QTimer(self)
        self._project_notice_timer.setSingleShot(True)
        self._project_notice_timer.timeout.connect(self._clear_project_notice)

        self.persistence_service = PersistenceService()
        self.validation_service = ValidationService()
        self.generation_service = GenerationService()
        self.export_service = None
        self.document_controller = ProjectDocumentController(
            self,
            persistence_service=self.persistence_service,
            validation_service=self.validation_service,
            generation_service=self.generation_service,
        )
        self.selection_controller = ProjectSelectionController(self)
        self.structure_controller = ProjectStructureController()
        self.app_icon = app_icon

        self.setWindowTitle("Case_Creator_App[*]")
        self.resize(1600, 920)
        if self.app_icon is not None:
            self.setWindowIcon(self.app_icon)
        self._build_ui()
        self.project_name_edit.setText(self.project.name)
        self._refresh_case_parts()
        self._refresh_values()
        self.base_case_include_checkbox.setChecked(self.project.base_case.include_in_case_name)
        self.simple_export_checkbox.setChecked(self.project.settings.simple_export_enabled)
        self._update_base_case_preview()
        self._refresh_counts()
        self._connect_signals()
        self._set_dirty(False)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._confirm_save_if_dirty("closing the application"):
            event.accept()
            return
        event.ignore()

    def _build_ui(self) -> None:
        self._build_actions()

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.project_options_group = QtWidgets.QGroupBox("Project Options", self)
        project_options_group_layout = QtWidgets.QVBoxLayout(self.project_options_group)
        project_options_group_layout.setSpacing(6)
        self.project_options_frame = QtWidgets.QFrame(self.project_options_group)
        project_options_layout = QtWidgets.QHBoxLayout(self.project_options_frame)
        project_options_layout.setContentsMargins(0, 0, 0, 0)
        project_options_layout.setSpacing(12)
        self.project_status_frame = QtWidgets.QFrame(self.project_options_group)
        project_status_layout = QtWidgets.QHBoxLayout(self.project_status_frame)
        project_status_layout.setContentsMargins(0, 0, 0, 0)
        project_status_layout.setSpacing(8)
        self.project_name_edit = QtWidgets.QLineEdit(self.project_options_frame)
        self.project_name_edit.setPlaceholderText("Project name")
        self.project_name_edit.setMaximumWidth(420)
        self.exclusions_button = QtWidgets.QPushButton("Exclusions", self.project_options_frame)
        self.base_case_include_checkbox = QtWidgets.QCheckBox(self.project_options_frame)
        self.input_data_button = QtWidgets.QPushButton("Input_Data", self.project_options_frame)
        self.mm_blocks_button = QtWidgets.QPushButton("MM_blocks", self.project_options_frame)
        self.simple_export_checkbox = QtWidgets.QCheckBox("Simple export", self.project_options_frame)
        self.case_name_order_button = QtWidgets.QPushButton("Name order", self.project_options_frame)
        self.case_name_preview_title_label = QtWidgets.QLabel("Preview", self.project_options_frame)
        self.base_case_preview_label = QtWidgets.QLabel(self.project_options_frame)
        self.project_path_label = QtWidgets.QLabel("Unsaved project", self.project_options_frame)
        self.project_path_label.setObjectName("projectPathLabel")
        self.project_notice_label = QtWidgets.QLabel(self.project_options_frame)
        self.project_notice_label.setObjectName("projectNoticeLabel")
        self.project_options_group.setStyleSheet(
            """
            QLabel#projectPathLabel {
                color: #45545f;
                background: #f2f5f7;
                border: 1px solid #cfd8de;
                border-radius: 8px;
                padding: 3px 10px;
                font-weight: 600;
            }
            QLabel#projectNoticeLabel {
                color: #2f6b4f;
                background: #eef7f2;
                border: 1px solid #bdd4c5;
                border-radius: 8px;
                padding: 3px 10px;
                font-weight: 600;
            }
            """
        )
        self.project_path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.project_notice_label.setVisible(False)
        project_options_layout.addWidget(QtWidgets.QLabel("Name", self.project_options_frame))
        project_options_layout.addWidget(self.project_name_edit)
        project_options_layout.addWidget(self.exclusions_button)
        project_options_layout.addWidget(self.input_data_button)
        project_options_layout.addWidget(self.mm_blocks_button)
        project_options_layout.addWidget(self.simple_export_checkbox)
        project_options_layout.addWidget(self.base_case_include_checkbox)
        project_options_layout.addWidget(self.case_name_order_button)
        project_options_layout.addWidget(self.case_name_preview_title_label)
        project_options_layout.addWidget(self.base_case_preview_label, 1)
        project_options_layout.addWidget(self.project_notice_label)
        project_options_group_layout.addWidget(self.project_options_frame)
        project_status_layout.addWidget(QtWidgets.QLabel("Project file", self.project_status_frame))
        project_status_layout.addWidget(self.project_path_label)
        project_status_layout.addStretch(1)
        project_options_group_layout.addWidget(self.project_status_frame)
        layout.addWidget(self.project_options_group)

        splitter = QtWidgets.QSplitter(self)
        layout.addWidget(splitter, 1)

        left_panel = QtWidgets.QWidget(splitter)
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.addWidget(QtWidgets.QLabel("Case Parts", left_panel))
        self.case_parts_list = QtWidgets.QListWidget(left_panel)
        left_layout.addWidget(self.case_parts_list, 1)
        left_buttons = QtWidgets.QGridLayout()
        self.add_case_part_button = QtWidgets.QPushButton("Add", left_panel)
        self.edit_case_part_button = QtWidgets.QPushButton("Edit", left_panel)
        self.duplicate_case_part_button = QtWidgets.QPushButton("Duplicate", left_panel)
        self.delete_case_part_button = QtWidgets.QPushButton("Delete", left_panel)
        self.move_case_part_up_button = QtWidgets.QPushButton("Up", left_panel)
        self.move_case_part_down_button = QtWidgets.QPushButton("Down", left_panel)
        left_buttons.addWidget(self.add_case_part_button, 0, 0)
        left_buttons.addWidget(self.edit_case_part_button, 0, 1)
        left_buttons.addWidget(self.duplicate_case_part_button, 1, 0)
        left_buttons.addWidget(self.delete_case_part_button, 1, 1)
        left_buttons.addWidget(self.move_case_part_up_button, 2, 0)
        left_buttons.addWidget(self.move_case_part_down_button, 2, 1)
        left_layout.addLayout(left_buttons)

        middle_panel = QtWidgets.QWidget(splitter)
        middle_layout = QtWidgets.QVBoxLayout(middle_panel)
        middle_layout.addWidget(QtWidgets.QLabel("Values", middle_panel))
        self.values_list = QtWidgets.QListWidget(middle_panel)
        middle_layout.addWidget(self.values_list, 1)
        value_buttons = QtWidgets.QGridLayout()
        self.add_value_button = QtWidgets.QPushButton("Add", middle_panel)
        self.edit_value_button = QtWidgets.QPushButton("Edit", middle_panel)
        self.delete_value_button = QtWidgets.QPushButton("Delete", middle_panel)
        self.move_value_up_button = QtWidgets.QPushButton("Up", middle_panel)
        self.move_value_down_button = QtWidgets.QPushButton("Down", middle_panel)
        value_buttons.addWidget(self.add_value_button, 0, 0)
        value_buttons.addWidget(self.edit_value_button, 0, 1)
        value_buttons.addWidget(self.delete_value_button, 1, 0)
        value_buttons.addWidget(self.move_value_up_button, 2, 0)
        value_buttons.addWidget(self.move_value_down_button, 2, 1)
        middle_layout.addLayout(value_buttons)

        right_panel = QtWidgets.QWidget(splitter)
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        self.changes_group = QtWidgets.QGroupBox("Changes for [No Selection]", right_panel)
        changes_layout = QtWidgets.QVBoxLayout(self.changes_group)
        self.changes_editor = ChangesEditor(self.changes_group)
        changes_layout.addWidget(self.changes_editor)
        right_layout.addWidget(self.changes_group, 1)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 5)

        footer = QtWidgets.QHBoxLayout()
        self.total_count_label = QtWidgets.QLabel("Total: 0", self)
        self.excluded_count_label = QtWidgets.QLabel("Excluded: 0", self)
        self.final_count_label = QtWidgets.QLabel("Final: 0", self)
        self.check_status_label = QtWidgets.QLabel("Needs check", self)
        self.check_button = QtWidgets.QPushButton("Check", self)
        self.export_button = QtWidgets.QPushButton("Export Excel", self)
        self.export_button.setObjectName("primaryExportButton")
        export_font = self.export_button.font()
        export_font.setBold(True)
        self.export_button.setFont(export_font)
        export_palette = self.export_button.palette()
        export_palette.setColor(QtGui.QPalette.Button, QtGui.QColor("#e4f1e8"))
        self.export_button.setPalette(export_palette)
        self.export_button.setAutoFillBackground(True)
        footer.addWidget(self.total_count_label)
        footer.addWidget(self.excluded_count_label)
        footer.addWidget(self.final_count_label)
        footer.addWidget(self.check_status_label)
        footer.addStretch(1)
        footer.addWidget(self.check_button)
        footer.addWidget(self.export_button)
        layout.addLayout(footer)

        self.setStatusBar(QtWidgets.QStatusBar(self))
        self.changes_editor.set_res_flux_enabled(self.project.settings.input_data.uses_residual_flux())
        self.changes_editor.setEnabled(False)
        self.export_button.setEnabled(False)
        self.project_options_frame.setVisible(True)

    def _build_actions(self) -> None:
        menu = self.menuBar()
        self.file_menu = menu.addMenu("File")

        self.new_action = QtGui.QAction("New Project", self)
        self.open_action = QtGui.QAction("Open Project", self)
        self.save_action = QtGui.QAction("Save Project", self)
        self.save_as_action = QtGui.QAction("Save Project As", self)
        self.export_selected_action = QtGui.QAction("Export Selected Cases...", self)
        self.exit_action = QtGui.QAction("Exit", self)
        self.save_action.setShortcut(QtGui.QKeySequence.Save)
        self.save_as_action.setShortcut(QtGui.QKeySequence.SaveAs)
        self.file_menu.addAction(self.new_action)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_as_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.export_selected_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

    def _connect_signals(self) -> None:
        self.new_action.triggered.connect(self._new_project)
        self.open_action.triggered.connect(self._open_project)
        self.save_action.triggered.connect(self._save_project)
        self.save_as_action.triggered.connect(self._save_project_as)
        self.export_selected_action.triggered.connect(self._export_selected_cases)
        self.exit_action.triggered.connect(self.close)
        self.exclusions_button.clicked.connect(self._edit_exclusions)

        self.project_name_edit.textChanged.connect(self._on_project_name_changed)
        self.mm_blocks_button.clicked.connect(self._edit_project_settings)
        self.input_data_button.clicked.connect(self._edit_input_data_settings)
        self.simple_export_checkbox.toggled.connect(self._on_simple_export_toggled)
        self.base_case_include_checkbox.toggled.connect(self._on_base_case_include_toggled)
        self.case_name_order_button.clicked.connect(self._edit_case_name_order)
        self.case_parts_list.currentRowChanged.connect(self._on_case_part_selected)
        self.values_list.currentRowChanged.connect(self._on_value_selected)
        self.changes_editor.changed.connect(self._on_changes_changed)
        self.changes_editor.cb_preview_changed.connect(self._on_cb_preview_changed)

        self.add_case_part_button.clicked.connect(self._add_case_part)
        self.edit_case_part_button.clicked.connect(self._edit_case_part)
        self.duplicate_case_part_button.clicked.connect(self._duplicate_case_part)
        self.delete_case_part_button.clicked.connect(self._delete_case_part)
        self.move_case_part_up_button.clicked.connect(lambda: self._move_case_part(-1))
        self.move_case_part_down_button.clicked.connect(lambda: self._move_case_part(1))

        self.add_value_button.clicked.connect(self._add_value)
        self.edit_value_button.clicked.connect(self._edit_value)
        self.delete_value_button.clicked.connect(self._delete_value)
        self.move_value_up_button.clicked.connect(lambda: self._move_value(-1))
        self.move_value_down_button.clicked.connect(lambda: self._move_value(1))

        self.check_button.clicked.connect(self._check_project)
        self.export_button.clicked.connect(self._export_excel)

    def _selected_case_part(self) -> CasePart | None:
        return self.selection_controller.selected_case_part()

    def _selected_case_part_index(self) -> int | None:
        return self.selection_controller.selected_case_part_index()

    def _is_base_selected(self) -> bool:
        return self.selection_controller.is_base_selected()

    def _selected_value(self) -> CaseValue | None:
        return self.selection_controller.selected_value()

    def _on_project_name_changed(self, text: str) -> None:
        normalized = text.strip() or "Untitled Project"
        if self.project.name == normalized:
            return
        self.project.name = normalized
        self._mark_dirty()

    def _on_simple_export_toggled(self, checked: bool) -> None:
        if self.project.settings.simple_export_enabled == checked:
            return
        self.project.settings.simple_export_enabled = checked
        self._mark_dirty()

    def _on_base_case_include_toggled(self, checked: bool) -> None:
        if self.project.base_case.include_in_case_name == checked:
            return
        self.project.base_case.include_in_case_name = checked
        self._update_base_case_preview()
        self._invalidate_generation()

    def _edit_case_name_order(self) -> None:
        dialog = CaseNameOrderDialog(self.project, self)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        if self.structure_controller.set_case_name_order(self.project, dialog.get_order()):
            self._update_base_case_preview()
            self._invalidate_generation()

    def _refresh_case_parts(self) -> None:
        self.selection_controller.refresh_case_parts()

    def _refresh_values(self) -> None:
        self.selection_controller.refresh_values()

    def _refresh_counts(self) -> None:
        self.total_count_label.setText(f"Total: {self.generation_stats.total_combinations}")
        self.excluded_count_label.setText(f"Excluded: {self.generation_stats.excluded_combinations}")
        self.final_count_label.setText(f"Final: {self.generation_stats.final_cases}")
        if self._is_checked:
            self.check_status_label.setText("Checked")
        else:
            self.check_status_label.setText("Needs check")
        self.export_button.setEnabled(self._is_checked and bool(self.generated_cases))

    def _on_case_part_selected(self, _row: int) -> None:
        self.selection_controller.on_case_part_selected(_row)

    def _on_value_selected(self, _row: int) -> None:
        self.selection_controller.on_value_selected(_row)

    def _update_base_case_preview(self) -> None:
        self.selection_controller.update_base_case_preview()

    def _show_project_notice(self, message: str, timeout_ms: int = 1500) -> None:
        self.project_notice_label.setText(message)
        self.project_notice_label.setVisible(True)
        if timeout_ms > 0:
            self._project_notice_timer.start(timeout_ms)

    def _clear_project_notice(self) -> None:
        self.project_notice_label.clear()
        self.project_notice_label.setVisible(False)

    def _show_feedback(
        self,
        status_message: str,
        *,
        notice_message: str | None = None,
        status_timeout_ms: int = 5000,
        notice_timeout_ms: int = 1500,
    ) -> None:
        if notice_message:
            self._show_project_notice(notice_message, notice_timeout_ms)
        self.statusBar().showMessage(status_message, status_timeout_ms)

    def _set_dirty(self, dirty: bool) -> None:
        self._is_dirty = dirty
        self.setWindowModified(dirty)

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    @property
    def is_checked(self) -> bool:
        return self._is_checked

    def set_checked(self, checked: bool) -> None:
        self._is_checked = checked

    def set_dirty(self, dirty: bool) -> None:
        self._set_dirty(dirty)

    def normalize_case_part_selectors(self) -> None:
        self.structure_controller.normalize_case_part_selectors(self.project)

    def refresh_project_view(self) -> None:
        self._refresh_case_parts()
        self._refresh_values()
        self._update_base_case_preview()
        self._refresh_counts()

    def refresh_counts(self) -> None:
        self._refresh_counts()

    def confirm_save_if_dirty(self, action: str) -> bool:
        return self._confirm_save_if_dirty(action)

    def show_feedback(
        self,
        status_message: str,
        *,
        notice_message: str | None = None,
        status_timeout_ms: int = 5000,
        notice_timeout_ms: int = 1500,
    ) -> None:
        self._show_feedback(
            status_message,
            notice_message=notice_message,
            status_timeout_ms=status_timeout_ms,
            notice_timeout_ms=notice_timeout_ms,
        )

    def _mark_dirty(self) -> None:
        self._set_dirty(True)

    def _confirm_save_if_dirty(self, action: str) -> bool:
        return self.document_controller.confirm_save_if_dirty(action)

    def _on_changes_changed(self) -> None:
        if self._loading_value:
            return
        if self._is_base_selected():
            self.project.base_case.changes = self.changes_editor.get_changes()
        else:
            case_part = self._selected_case_part()
            value = self._selected_value()
            if case_part is None or value is None:
                return
            new_changes = self.changes_editor.get_changes()
            self.structure_controller.sync_case_part_selectors(case_part, new_changes)
            value.changes = new_changes
        self._invalidate_generation()

    def _on_cb_preview_changed(self) -> None:
        self.selection_controller.refresh_cb_preview_context()

    def _invalidate_generation(self) -> None:
        self.generated_cases = []
        self.generation_stats = GenerationStats()
        self._is_checked = False
        self._update_base_case_preview()
        self._mark_dirty()
        self._refresh_counts()

    def _add_case_part(self) -> None:
        dialog = CasePartDialog(self)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        label, tokens = dialog.get_data()
        added_index = self.structure_controller.add_case_part(self.project, label, tokens)
        self._refresh_case_parts()
        self.case_parts_list.setCurrentRow(added_index + 1)
        self._invalidate_generation()

    def _edit_case_part(self) -> None:
        if self._is_base_selected():
            label, accepted = QtWidgets.QInputDialog.getText(
                self,
                "Edit Base Case Name",
                "Case part name",
                text=self.project.base_case.label,
            )
            if not accepted:
                return
            label = label.strip()
            if not label:
                return
            self.structure_controller.rename_base_case(self.project, label)
            self._refresh_case_parts()
            self.case_parts_list.setCurrentRow(0)
            self._update_base_case_preview()
            self._mark_dirty()
            return

        case_part = self._selected_case_part()
        if case_part is None:
            return
        dialog = CasePartDialog(self, case_part)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        label, tokens = dialog.get_data()
        self.structure_controller.edit_case_part(case_part, label, tokens)
        self._refresh_case_parts()
        self._refresh_values()
        self._invalidate_generation()

    def _duplicate_case_part(self) -> None:
        case_part = self._selected_case_part()
        if case_part is None:
            return
        added_index = self.structure_controller.duplicate_case_part(self.project, case_part)
        self._refresh_case_parts()
        self.case_parts_list.setCurrentRow(added_index + 1)
        self._invalidate_generation()

    def _delete_case_part(self) -> None:
        index = self._selected_case_part_index()
        if index is None:
            return
        self.structure_controller.delete_case_part(self.project, index)
        self._refresh_case_parts()
        self._refresh_values()
        self._invalidate_generation()

    def _move_case_part(self, direction: int) -> None:
        index = self._selected_case_part_index()
        if index is None:
            return
        target = self.structure_controller.move_case_part(self.project, index, direction)
        if target is None:
            return
        self._refresh_case_parts()
        self.case_parts_list.setCurrentRow(target + 1)
        self._invalidate_generation()

    def _add_value(self) -> None:
        case_part = self._selected_case_part()
        if case_part is None:
            return
        dialog = TokenDialog("Add Value", "Value", parent=self)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        tokens = dialog.tokens()
        if not tokens:
            return
        start_index = self.structure_controller.add_values(case_part, tokens)
        self._refresh_values()
        self.values_list.setCurrentRow(start_index)
        self._refresh_case_parts()
        self._invalidate_generation()

    def _edit_value(self) -> None:
        if self._is_base_selected():
            dialog = TokenDialog("Edit Base Value", "Value", self.project.base_case.token, self)
            if dialog.exec() != QtWidgets.QDialog.Accepted:
                return
            tokens = dialog.tokens()
            if not tokens:
                return
            self.structure_controller.set_base_case_token(self.project, tokens[0])
            self._refresh_values()
            self.values_list.setCurrentRow(0)
            self._update_base_case_preview()
            self._invalidate_generation()
            return

        case_part = self._selected_case_part()
        value = self._selected_value()
        row = self.values_list.currentRow()
        if case_part is None or value is None or row < 0:
            return
        dialog = TokenDialog("Edit Value", "Value", value.token, self)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        tokens = dialog.tokens()
        if not tokens:
            return
        self.structure_controller.edit_value(case_part, row, value, tokens)
        self._refresh_values()
        self.values_list.setCurrentRow(row)
        self._invalidate_generation()

    def _delete_value(self) -> None:
        case_part = self._selected_case_part()
        row = self.values_list.currentRow()
        if case_part is None or row < 0:
            return
        self.structure_controller.delete_value(case_part, row)
        self._refresh_values()
        self._refresh_case_parts()
        self._invalidate_generation()

    def _move_value(self, direction: int) -> None:
        case_part = self._selected_case_part()
        row = self.values_list.currentRow()
        if case_part is None:
            return
        target = self.structure_controller.move_value(case_part, row, direction)
        if target is None:
            return
        self._refresh_values()
        self.values_list.setCurrentRow(target)
        self._invalidate_generation()

    def _edit_exclusions(self) -> None:
        from case_builder_app.ui.rules_dialogs import ExclusionsDialog

        dialog = ExclusionsDialog(self.project, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.project.exclusions = dialog.get_combinations()
            self._invalidate_generation()

    def _edit_project_settings(self) -> None:
        from case_builder_app.ui.project_settings_dialog import ProjectSettingsDialog

        dialog = ProjectSettingsDialog(self.project, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.project.mm_blocks = dialog.get_mm_blocks()
            self._invalidate_generation()

    def _edit_input_data_settings(self) -> None:
        from case_builder_app.ui.input_data_dialog import InputDataDialog

        dialog = InputDataDialog(self.project.settings, self)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        old_res_flux_enabled = self.project.settings.input_data.uses_residual_flux()
        self.project.settings.input_data = dialog.input_data_settings()
        new_res_flux_enabled = self.project.settings.input_data.uses_residual_flux()
        self.changes_editor.set_res_flux_enabled(new_res_flux_enabled)
        if old_res_flux_enabled != new_res_flux_enabled:
            self._invalidate_generation()
        else:
            self._mark_dirty()

    def _check_project(self) -> None:
        self.document_controller.check_project()

    def _export_excel(self) -> None:
        self.document_controller.export_excel()

    def _export_selected_cases(self) -> None:
        self.document_controller.export_selected_cases()

    def _new_project(self) -> None:
        self.document_controller.new_project()

    def _open_project(self) -> None:
        self.document_controller.open_project()

    def _save_project(self) -> bool:
        return self.save_project()

    def _save_project_as(self) -> bool:
        return self.save_project_as()

    def save_project(self) -> bool:
        return self.document_controller.save_project()

    def save_project_as(self) -> bool:
        return self.document_controller.save_project_as()
