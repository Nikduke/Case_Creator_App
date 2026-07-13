import os
from copy import deepcopy
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtGui, QtWidgets

from case_builder_app.models import INPUT_DATA_SWITCHING, CasePart, CaseValue, InputDataSettings, Project, ValueChanges
from case_builder_app.services.generator import GeneratedCase
from case_builder_app.ui import main_window as main_window_module
from case_builder_app.ui.cb_state_board import CBChipDelegate
from case_builder_app.ui.main_window import MainWindow


def _app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def window():
    _app()
    widget = MainWindow()
    yield widget
    widget._set_dirty(False)
    widget.close()
    widget.deleteLater()
    QtWidgets.QApplication.processEvents()


def test_base_case_uses_edit_buttons_for_name_and_token(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    assert window._is_base_selected() is True
    assert window.edit_case_part_button.isEnabled() is True
    assert window.edit_value_button.isEnabled() is True
    assert window.add_value_button.isEnabled() is False

    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *args, **kwargs: ("Reenergisation", True))

    class StubTokenDialog:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def exec(self) -> int:
            return QtWidgets.QDialog.Accepted

        def tokens(self) -> list[str]:
            return ["C72"]

    monkeypatch.setattr(main_window_module, "TokenDialog", StubTokenDialog)

    window._edit_case_part()
    window._edit_value()

    assert window.project.base_case.label == "Reenergisation"
    assert window.project.base_case.token == "C72"
    assert window.case_parts_list.item(0).text() == "Reenergisation"
    assert 'Include "C72" in case names' == window.base_case_include_checkbox.text()


def test_selector_choices_sync_across_all_values_in_same_case_part(window: MainWindow) -> None:
    project = Project(
        case_parts=[
            CasePart(
                label="VSR",
                values=[
                    CaseValue(token="V1"),
                    CaseValue(token="V2", changes=ValueChanges(use_cb=True)),
                    CaseValue(token="V3", changes=ValueChanges(use_layers=True)),
                ],
            )
        ]
    )
    window.project = project
    window._refresh_case_parts()
    window.case_parts_list.setCurrentRow(1)
    window._refresh_values()
    window.values_list.setCurrentRow(0)

    updated = deepcopy(project.case_parts[0].values[0].changes)
    updated.use_cb = True
    updated.use_parameters = True
    updated.use_layers = True

    window.changes_editor.get_changes = lambda: updated  # type: ignore[method-assign]
    window._on_changes_changed()

    assert [value.changes.use_cb for value in project.case_parts[0].values] == [True, True, True]
    assert [value.changes.use_parameters for value in project.case_parts[0].values] == [True, True, True]
    assert [value.changes.use_layers for value in project.case_parts[0].values] == [True, True, True]


def test_save_shortcut_and_project_notice(window: MainWindow) -> None:
    assert window.save_action.shortcut().matches(QtGui.QKeySequence.Save) == QtGui.QKeySequence.ExactMatch
    assert [action.text() for action in window.menuBar().actions()] == ["File"]
    assert "Export Selected Cases..." in [action.text() for action in window.file_menu.actions()]
    assert window.project_name_edit.maximumWidth() == 420
    assert window.project_options_group.title() == "Project Options"
    assert window.project_name_edit.parent() is window.project_options_frame
    assert window.project_path_label.parent() is window.project_status_frame
    assert window.project_options_frame.parent() is window.project_options_group
    assert window.project_status_frame.parent() is window.project_options_group
    assert window.changes_editor.selector_bar.parent() is window.changes_editor
    project_options_layout = window.project_options_frame.layout()
    assert [
        project_options_layout.indexOf(widget)
        for widget in (
            window.project_name_edit,
            window.exclusions_button,
            window.input_data_button,
            window.mm_blocks_button,
            window.simple_export_checkbox,
            window.base_case_include_checkbox,
            window.case_name_order_button,
            window.case_name_preview_title_label,
            window.base_case_preview_label,
            window.project_notice_label,
        )
    ] == [1, *range(2, 11)]
    assert window.project_status_frame.layout().indexOf(window.project_path_label) == 1
    assert window.case_name_preview_title_label.text() == "Preview"
    assert window.project_path_label.objectName() == "projectPathLabel"
    assert window.export_button.objectName() == "primaryExportButton"

    window._show_project_notice("Project saved", timeout_ms=0)
    assert window.project_notice_label.text() == "Project saved"
    assert window.project_notice_label.isHidden() is False

    window._clear_project_notice()
    assert window.project_notice_label.text() == ""
    assert window.project_notice_label.isHidden() is True


def test_default_project_stem_uses_project_name_with_fallback(window: MainWindow) -> None:
    window.project_name_edit.setText("My Project 01")
    assert window.document_controller.default_project_stem() == "My_Project_01"

    window.project_name_edit.setText('Name: A/B*C?')
    assert window.document_controller.default_project_stem() == "Name_A_B_C"

    window.project_name_edit.setText("")
    window.project.name = ""
    assert window.document_controller.default_project_stem() == "Untitled_Project"


def test_export_normalizes_xlsx_suffix(window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class StubExportService:
        def __init__(self) -> None:
            self.path = None
            self.notice_during_export = None

        def export(self, project, generated_cases, path) -> None:  # noqa: ANN001
            self.path = Path(path)
            self.notice_during_export = window.project_notice_label.text()

    stub = StubExportService()
    window.export_service = stub
    window._is_checked = True
    window.generated_cases = [object()]

    target = tmp_path / "my_export"
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(target), "Excel Files (*.xlsx)"))

    window._export_excel()

    assert stub.path == target.with_suffix(".xlsx")
    assert stub.notice_during_export == "Exporting..."
    assert window.project_notice_label.text() == "Export done"
    assert window.project_notice_label.isHidden() is False


def test_export_selected_cases_uses_pasted_order(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from case_builder_app.ui import export_dialogs

    class StubExportService:
        def __init__(self) -> None:
            self.path = None
            self.case_names = []
            self.simple_export_enabled = None

        def export(self, project, generated_cases, path) -> None:  # noqa: ANN001
            self.path = Path(path)
            self.case_names = [case.name for case in generated_cases]
            self.simple_export_enabled = project.settings.simple_export_enabled

    class StubSelectedCasesExportDialog:
        def __init__(self, available_names, *args, **kwargs) -> None:  # noqa: ANN001
            self.available_names = available_names

        def exec(self) -> int:
            return QtWidgets.QDialog.Accepted

        def selected_names(self) -> list[str]:
            return ["C3", "A1"]

        def simple_export_enabled(self) -> bool:
            return True

        def saved_lists_changed(self) -> bool:
            return False

        def selected_case_lists(self) -> list:
            return []

    stub = StubExportService()
    window.export_service = stub
    window._is_checked = True
    window.generated_cases = [
        GeneratedCase(name="A1", selected_value_ids={}),
        GeneratedCase(name="B2", selected_value_ids={}),
        GeneratedCase(name="C3", selected_value_ids={}),
    ]

    target = tmp_path / "selected_export"
    monkeypatch.setattr(export_dialogs, "SelectedCasesExportDialog", StubSelectedCasesExportDialog)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(target), "Excel Files (*.xlsx)"))

    window._export_selected_cases()

    assert stub.path == target.with_suffix(".xlsx")
    assert stub.case_names == ["C3", "A1"]
    assert stub.simple_export_enabled is True
    assert window.project.settings.simple_export_enabled is False
    assert window.project_notice_label.text() == "Export done"


def test_project_name_change_marks_window_dirty(window: MainWindow) -> None:
    assert window._is_dirty is False

    window.project_name_edit.setText("Changed Project")

    assert window._is_dirty is True


def test_mm_blocks_button_opens_limits_dialog(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    from case_builder_app.models import MMBlocks, MMLimit
    from case_builder_app.ui import project_settings_dialog

    assert window.mm_blocks_button.text() == "MM_blocks"

    updated_blocks = MMBlocks(
        elements=["MM_230_A"],
        limits_by_voltage=[MMLimit(voltage="230", un="230", um="245", sdpf_lg="460", sdpf_ll="460", siwl_lg="850", siwl_ll="850", liwl="1050")],
    )

    class StubProjectSettingsDialog:
        def __init__(self, project, parent=None) -> None:  # noqa: ANN001
            assert project is window.project
            assert parent is window

        def exec(self) -> int:
            return QtWidgets.QDialog.Accepted

        def get_mm_blocks(self) -> MMBlocks:
            return updated_blocks

    monkeypatch.setattr(project_settings_dialog, "ProjectSettingsDialog", StubProjectSettingsDialog)

    window._edit_project_settings()

    assert window.project.mm_blocks.elements == ["MM_230_A"]
    assert window._is_dirty is True


def test_simple_export_checkbox_updates_project_setting(window: MainWindow) -> None:
    assert window.simple_export_checkbox.text() == "Simple export"
    assert window.project.settings.simple_export_enabled is False

    window.simple_export_checkbox.setChecked(True)

    assert window.project.settings.simple_export_enabled is True
    assert window._is_dirty is True


def test_input_data_button_opens_settings_dialog(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    from case_builder_app.ui import input_data_dialog

    assert window.input_data_button.text() == "Input_Data"

    updated_settings = InputDataSettings(studies=[INPUT_DATA_SWITCHING], frequency="50", residual_flux="Yes")

    class StubInputDataDialog:
        def __init__(self, settings, parent=None) -> None:  # noqa: ANN001
            assert settings is window.project.settings
            assert parent is window

        def exec(self) -> int:
            return QtWidgets.QDialog.Accepted

        def input_data_settings(self) -> InputDataSettings:
            return updated_settings

    monkeypatch.setattr(input_data_dialog, "InputDataDialog", StubInputDataDialog)

    window._edit_input_data_settings()

    assert window.project.settings.input_data.frequency == "50"
    assert window.project.settings.input_data.uses_residual_flux() is True
    assert window.input_data_button.text() == "Input_Data"
    assert window._is_dirty is True


def test_cb_preview_branch_changes_inherited_state_without_editing_current_value(window: MainWindow) -> None:
    part_iac = CasePart(label="IAC state")
    a1 = CaseValue(token="A1")
    a3 = CaseValue(token="A3")
    a3.changes.use_cb = True
    a3.changes.cb.on = ["CB_66_A"]
    part_iac.values = [a1, a3]

    part_run = CasePart(label="Running arrangement")
    c23 = CaseValue(token="C23")
    c23.changes.use_cb = True
    part_run.values = [c23]

    window.project = Project(case_parts=[part_iac, part_run])
    window.project.base_case.changes.use_cb = True
    window.project.base_case.changes.cb.off = ["CB_66_A"]
    window.refresh_project_view()

    window.case_parts_list.setCurrentRow(2)
    window.values_list.setCurrentRow(0)

    board = window.changes_editor.cb_board
    assert board.preview_frame.isHidden() is False
    assert _lane_token_status(board._lanes["off"], "CB_66_A") == "inherited"

    a3_button = next(button for button in board.preview_frame.findChildren(QtWidgets.QPushButton) if button.text() == "A3")
    a3_button.click()

    assert _lane_token_status(board._lanes["on"], "CB_66_A") == "inherited"
    assert c23.changes.cb.off == []
    assert c23.changes.cb.on == []


def test_case_name_order_dialog_updates_preview_and_marks_dirty(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    part_a = CasePart(label="A", values=[CaseValue(token="A1")])
    part_ex = CasePart(label="Ex", values=[CaseValue(token="F")])
    window.project = Project(case_parts=[part_a, part_ex])
    window.refresh_project_view()

    class StubCaseNameOrderDialog:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def exec(self) -> int:
            return QtWidgets.QDialog.Accepted

        def get_order(self) -> list[str]:
            return [part_ex.id, part_a.id]

    monkeypatch.setattr(main_window_module, "CaseNameOrderDialog", StubCaseNameOrderDialog)

    window._edit_case_name_order()

    assert window.project.settings.case_name_order == [part_ex.id, part_a.id]
    assert window.base_case_preview_label.text() == "F_A1"
    assert window._is_dirty is True


def test_adding_case_part_updates_preview(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    class StubCasePartDialog:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def exec(self) -> int:
            return QtWidgets.QDialog.Accepted

        def get_data(self) -> tuple[str, list[str]]:
            return "Ex", ["F"]

    monkeypatch.setattr(main_window_module, "CasePartDialog", StubCasePartDialog)

    assert window.base_case_preview_label.text() == "(no generated case parts yet)"

    window._add_case_part()

    assert window.base_case_preview_label.text() == "F"


def _lane_token_status(lane: QtWidgets.QListWidget, token: str) -> str:
    for row in range(lane.count()):
        item = lane.item(row)
        if bool(item.data(CBChipDelegate.GROUP_ROLE)):
            continue
        if item.text() == token:
            return str(item.data(CBChipDelegate.STATUS_ROLE))
    raise AssertionError(f"Missing token {token}")


def test_save_project_clears_dirty_state(window: MainWindow, tmp_path: Path) -> None:
    project_path = tmp_path / "saved_project.casebuilder.json"
    window.project_path = project_path
    window.project_name_edit.setText("Changed Project")

    assert window._is_dirty is True
    assert window._save_project() is True
    assert project_path.exists()
    assert window._is_dirty is False


def test_new_project_cancelled_by_unsaved_prompt_keeps_current_project(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.project_name_edit.setText("Keep Me")
    assert window._is_dirty is True

    monkeypatch.setattr(window, "_confirm_save_if_dirty", lambda action: False)

    window._new_project()

    assert window.project_name_edit.text() == "Keep Me"
    assert window.project.name == "Keep Me"


def test_open_project_cancelled_by_unsaved_prompt_skips_file_dialog(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.project_name_edit.setText("Unsaved")
    assert window._is_dirty is True

    monkeypatch.setattr(window, "_confirm_save_if_dirty", lambda action: False)

    def fail_open(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("Open dialog should not be shown when the unsaved prompt is cancelled.")

    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName", fail_open)

    window._open_project()


def test_close_event_respects_unsaved_prompt_result(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    window.project_name_edit.setText("Unsaved")
    assert window._is_dirty is True

    monkeypatch.setattr(window, "_confirm_save_if_dirty", lambda action: False)
    reject_event = QtGui.QCloseEvent()
    window.closeEvent(reject_event)
    assert reject_event.isAccepted() is False

    monkeypatch.setattr(window, "_confirm_save_if_dirty", lambda action: True)
    accept_event = QtGui.QCloseEvent()
    window.closeEvent(accept_event)
    assert accept_event.isAccepted() is True
