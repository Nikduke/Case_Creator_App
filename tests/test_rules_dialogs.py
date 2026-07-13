import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtWidgets

from case_builder_app.models import CasePart, CaseValue, Project
from case_builder_app.ui.project_settings_dialog import ProjectSettingsDialog
from case_builder_app.ui.rules_dialogs import ExclusionsDialog
from case_builder_app.ui.table_helpers import EditableCellTable


def _app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def project() -> Project:
    _app()
    return Project(
        case_parts=[
            CasePart(
                label="Strength",
                values=[CaseValue(token="S1"), CaseValue(token="S2")],
            ),
            CasePart(
                label="VSR",
                values=[CaseValue(token="V1"), CaseValue(token="V2")],
            ),
            CasePart(
                label="Fault",
                values=[CaseValue(token="F1"), CaseValue(token="F2")],
            ),
        ]
    )


def test_exclusions_dialog_buttons_follow_text_and_selection(project: Project) -> None:
    dialog = ExclusionsDialog(project)
    try:
        assert dialog.import_button.isEnabled() is False
        assert dialog.add_button.isEnabled() is True
        assert dialog.remove_button.isEnabled() is False

        dialog.entry_edit.setPlainText("S1 V1 F1")
        QtWidgets.QApplication.processEvents()
        assert dialog.import_button.isEnabled() is True
        assert dialog.add_button.isEnabled() is True
        assert dialog.remove_button.isEnabled() is False

        dialog._add_from_text()
        dialog.table.selectRow(0)
        QtWidgets.QApplication.processEvents()
        assert dialog.remove_button.isEnabled() is True
        assert [dialog.table.item(0, column).text() for column in range(dialog.table.columnCount())] == ["S1", "V1", "F1"]
        combinations = dialog._read_table()
        assert len(combinations) == 1
        assert len(combinations[0].clauses) == 3
    finally:
        dialog.close()
        dialog.deleteLater()


def test_project_settings_mm_limits_use_shared_editable_table(project: Project) -> None:
    dialog = ProjectSettingsDialog(project)
    try:
        assert isinstance(dialog.limits_table, EditableCellTable)
        assert dialog.limits_table.expand_on_paste is False
        assert dialog.limits_table.selectionBehavior() == QtWidgets.QAbstractItemView.SelectItems
    finally:
        dialog.close()
        dialog.deleteLater()


def test_project_settings_preserves_limit_edits_when_mm_elements_change(project: Project) -> None:
    dialog = ProjectSettingsDialog(project)
    try:
        dialog.add_edit.setPlainText("MM_230_OFT")
        dialog._add_entered_elements()
        dialog.limits_table.item(0, 1).setText("230")

        dialog.add_edit.setPlainText("MM_161_ONT")
        dialog._add_entered_elements()

        blocks = dialog.get_mm_blocks()
        limits = {item.voltage: item for item in blocks.limits_by_voltage}
        assert limits["230"].un == "230"
        assert "161" in limits
    finally:
        dialog.close()
        dialog.deleteLater()
