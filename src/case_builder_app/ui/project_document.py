from __future__ import annotations

from pathlib import Path
import re
from typing import TYPE_CHECKING

from PySide6 import QtWidgets

from case_builder_app.models import Project
from case_builder_app.services.generator import GenerationError, GenerationService, GenerationStats
from case_builder_app.services.persistence import PROJECT_FILE_SUFFIX, PersistenceService
from case_builder_app.services.validation import ValidationService

if TYPE_CHECKING:
    from case_builder_app.ui.main_window import MainWindow


class ProjectDocumentController:
    def __init__(
        self,
        window: MainWindow,
        *,
        persistence_service: PersistenceService,
        validation_service: ValidationService,
        generation_service: GenerationService,
    ) -> None:
        self.window = window
        self.persistence_service = persistence_service
        self.validation_service = validation_service
        self.generation_service = generation_service

    def confirm_save_if_dirty(self, action: str) -> bool:
        if not self.window.is_dirty:
            return True

        message = QtWidgets.QMessageBox(self.window)
        message.setIcon(QtWidgets.QMessageBox.Warning)
        message.setWindowTitle("Unsaved Changes")
        message.setText("The project has unsaved changes.")
        message.setInformativeText(f"Do you want to save your changes before {action}?")
        message.setStandardButtons(
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel
        )
        message.setDefaultButton(QtWidgets.QMessageBox.Save)
        choice = message.exec()

        if choice == QtWidgets.QMessageBox.Save:
            return self.save_project()
        if choice == QtWidgets.QMessageBox.Discard:
            return True
        return False

    def default_project_stem(self) -> str:
        raw_name = self.window.project_name_edit.text().strip() or self.window.project.name.strip() or "Untitled Project"
        normalized = re.sub(r"[\\/:*?\"<>|]+", "_", raw_name)
        normalized = re.sub(r"\s+", "_", normalized).strip("._ ")
        normalized = re.sub(r"_+", "_", normalized)
        return normalized or "Untitled_Project"

    @staticmethod
    def normalized_export_path(path: str | Path) -> Path:
        export_path = Path(path)
        if export_path.suffix.lower() == ".xlsx":
            return export_path
        if export_path.suffix:
            return export_path.with_suffix(".xlsx")
        return export_path.with_name(f"{export_path.name}.xlsx")

    def new_project(self) -> None:
        if not self.window.confirm_save_if_dirty("creating a new project"):
            return
        self.window.project = Project()
        self.window.normalize_case_part_selectors()
        self.window.project_path = None
        self.window.generated_cases = []
        self.window.generation_stats = GenerationStats()
        self.window.set_checked(False)
        self.window.project_name_edit.setText(self.window.project.name)
        self.window.base_case_include_checkbox.setChecked(self.window.project.base_case.include_in_case_name)
        self.window.changes_editor.set_res_flux_enabled(self.window.project.settings.input_data.uses_residual_flux())
        self.window.simple_export_checkbox.setChecked(False)
        self.window.project_path_label.setText("Unsaved project")
        self.window.refresh_project_view()
        self.window.set_dirty(False)

    def open_project(self) -> None:
        if not self.window.confirm_save_if_dirty("opening another project"):
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.window,
            "Open Project",
            str(Path.cwd()),
            f"Case Builder Project (*{PROJECT_FILE_SUFFIX});;JSON Files (*.json)",
        )
        if not path:
            return
        self.window.project = self.persistence_service.load_project(path)
        self.window.normalize_case_part_selectors()
        self.window.project_path = Path(path)
        self.window.project_name_edit.setText(self.window.project.name)
        self.window.base_case_include_checkbox.setChecked(self.window.project.base_case.include_in_case_name)
        self.window.changes_editor.set_res_flux_enabled(self.window.project.settings.input_data.uses_residual_flux())
        self.window.simple_export_checkbox.setChecked(self.window.project.settings.simple_export_enabled)
        self.window.project_path_label.setText(str(self.window.project_path))
        self.window.generated_cases = []
        self.window.generation_stats = GenerationStats()
        self.window.set_checked(False)
        self.window.refresh_project_view()
        self.window.set_dirty(False)
        self.window.show_feedback(f"Loaded {path}")

    def save_project(self) -> bool:
        if self.window.project_path is None:
            return self.save_project_as()
        self.window.project.name = self.window.project_name_edit.text().strip() or "Untitled Project"
        self.persistence_service.save_project(self.window.project_path, self.window.project)
        self.window.project_path_label.setText(str(self.window.project_path))
        self.window.set_dirty(False)
        self.window.show_feedback(f"Saved {self.window.project_path}", notice_message="Project saved")
        return True

    def save_project_as(self) -> bool:
        suggested = self.default_project_stem()
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window,
            "Save Project",
            str(Path.cwd() / f"{suggested}{PROJECT_FILE_SUFFIX}"),
            f"Case Builder Project (*{PROJECT_FILE_SUFFIX});;JSON Files (*.json)",
        )
        if not path:
            return False
        self.window.project_path = Path(path)
        return self.save_project()

    def show_errors(self, title: str, errors: list[str]) -> None:
        message = QtWidgets.QMessageBox(self.window)
        message.setIcon(QtWidgets.QMessageBox.Critical)
        message.setWindowTitle(title)
        message.setText(title)
        message.setDetailedText("\n".join(errors))
        message.setStandardButtons(QtWidgets.QMessageBox.Ok)
        message.exec()

    def _export_workbook(self, generated_cases, export_path: Path, success_message: str) -> bool:  # noqa: ANN001
        self.window.show_feedback("Exporting...", notice_message="Exporting...", status_timeout_ms=0, notice_timeout_ms=0)
        QtWidgets.QApplication.processEvents()
        try:
            if self.window.export_service is None:
                from case_builder_app.services.export_service import ExportService

                self.window.export_service = ExportService()
            self.window.export_service.export(self.window.project, generated_cases, export_path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self.window,
                "Export Error",
                f"Could not export the Excel file.\n\n{exc}",
            )
            self.window.show_feedback("Excel export failed.", notice_message="Export failed", status_timeout_ms=8000)
            return False
        self.window.show_feedback(success_message, notice_message="Export done", status_timeout_ms=8000)
        return True

    def check_project(self) -> None:
        self.window.project.name = self.window.project_name_edit.text().strip() or "Untitled Project"
        validation = self.validation_service.validate_project(self.window.project)
        if not validation.is_valid:
            self.window.set_checked(False)
            self.window.generated_cases = []
            self.window.generation_stats = GenerationStats()
            self.window.refresh_counts()
            self.show_errors("Validation Errors", validation.errors)
            return

        try:
            self.window.generated_cases, self.window.generation_stats = self.generation_service.generate(self.window.project)
        except GenerationError as exc:
            self.window.generated_cases = []
            self.window.generation_stats = GenerationStats()
            self.window.set_checked(False)
            self.window.refresh_counts()
            self.show_errors("Generation Errors", exc.errors)
            return

        self.window.set_checked(True)
        self.window.refresh_counts()
        self.window.show_feedback("Check completed. Definition is valid.")

    def export_excel(self) -> None:
        if not self.window.is_checked or not self.window.generated_cases:
            QtWidgets.QMessageBox.information(
                self.window,
                "Check Required",
                "Run Check after your latest changes before exporting.",
            )
            return

        suggested = (self.window.project_path.parent if self.window.project_path else Path.cwd()) / f"{self.default_project_stem()}.xlsx"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window,
            "Export Excel",
            str(suggested),
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        export_path = self.normalized_export_path(path)
        self._export_workbook(self.window.generated_cases, export_path, f"Exported {export_path}")

    def export_selected_cases(self) -> None:
        if not self.window.is_checked or not self.window.generated_cases:
            QtWidgets.QMessageBox.information(
                self.window,
                "Check Required",
                "Run Check after your latest changes before exporting.",
            )
            return

        from case_builder_app.ui.export_dialogs import SelectedCasesExportDialog

        dialog = SelectedCasesExportDialog(
            [case.name for case in self.window.generated_cases],
            self.window.project.selected_case_lists,
            simple_export_enabled=self.window.project.settings.simple_export_enabled,
            parent=self.window,
        )
        accepted = dialog.exec() == QtWidgets.QDialog.Accepted
        if dialog.saved_lists_changed():
            self.window.project.selected_case_lists = dialog.selected_case_lists()
            self.window.set_dirty(True)
        if not accepted:
            return

        names = dialog.selected_names()
        cases_by_name = {case.name: case for case in self.window.generated_cases}
        selected_cases = [cases_by_name[name] for name in names if name in cases_by_name]
        if not selected_cases:
            return

        suggested = (
            (self.window.project_path.parent if self.window.project_path else Path.cwd())
            / f"{self.default_project_stem()}_selected.xlsx"
        )
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window,
            "Export Selected Cases",
            str(suggested),
            "Excel Files (*.xlsx)",
        )
        if not path:
            return

        export_path = self.normalized_export_path(path)
        original_simple_export = self.window.project.settings.simple_export_enabled
        self.window.project.settings.simple_export_enabled = dialog.simple_export_enabled()
        try:
            self._export_workbook(
                selected_cases,
                export_path,
                f"Exported {len(selected_cases)} selected cases to {export_path}",
            )
        finally:
            self.window.project.settings.simple_export_enabled = original_simple_export
