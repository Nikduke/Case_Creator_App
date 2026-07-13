import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtTest, QtWidgets

from case_builder_app.models import INPUT_DATA_FAULT, INPUT_DATA_SWITCHING, InputDataSettings, ProjectSettings, SelectedCaseList
from case_builder_app.ui.export_dialogs import SelectedCasesExportDialog
from case_builder_app.ui.input_data_dialog import InputDataDialog
from case_builder_app.ui.table_helpers import ComboBoxDelegate, create_editor_table


def _app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_selected_cases_export_dialog_validates_missing_and_duplicates() -> None:
    _app()
    dialog = SelectedCasesExportDialog(["A1", "B2"], [], simple_export_enabled=True)

    assert dialog.simple_export_enabled() is True

    dialog.names_edit.setPlainText("B2, A1 A1 MISSING")
    dialog._validate()

    assert dialog.selected_names() == ["B2", "A1"]
    assert dialog.export_button.isEnabled() is True
    assert dialog.missing_group.isHidden() is False
    assert dialog.summary_label.text() == "Matched: 2 | Missing: 1 | Duplicates ignored: 1"
    assert dialog.missing_text.toPlainText() == "MISSING"

    dialog.names_edit.setPlainText("B2; A1; B2")
    dialog._validate()

    assert dialog.selected_names() == ["B2", "A1"]
    assert dialog.export_button.isEnabled() is True
    assert dialog.summary_label.text() == "Matched: 2 | Missing: 0 | Duplicates ignored: 1"

    dialog.close()
    dialog.deleteLater()
    QtWidgets.QApplication.processEvents()


def test_selected_cases_export_dialog_saves_updates_and_loads_lists(monkeypatch) -> None:  # noqa: ANN001
    _app()
    saved = SelectedCaseList(name="Report", case_names=["A1"])
    dialog = SelectedCasesExportDialog(["A1", "B2", "C3"], [saved], simple_export_enabled=False)

    assert dialog.names_edit.toPlainText() == "A1"

    dialog.names_edit.setPlainText("C3 B2 B2")
    dialog._save_current_list()

    assert dialog.saved_lists_changed() is True
    updated = dialog.selected_case_lists()[0]
    assert updated.name == "Report"
    assert updated.case_names == ["C3", "B2"]

    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", lambda *args, **kwargs: ("Second", True))
    dialog.names_edit.setPlainText("A1 C3")
    dialog._save_current_list_as()

    lists = dialog.selected_case_lists()
    assert [item.name for item in lists] == ["Report", "Second"]
    assert lists[1].case_names == ["A1", "C3"]

    dialog.close()
    dialog.deleteLater()
    QtWidgets.QApplication.processEvents()


def test_input_data_dialog_enforces_study_selection_and_saves_fields() -> None:
    _app()
    settings = ProjectSettings(
        input_data=InputDataSettings(studies=[INPUT_DATA_SWITCHING, INPUT_DATA_FAULT], frequency="50"),
    )
    dialog = InputDataDialog(settings)

    assert dialog.frequency_sweep_checkbox.isChecked() is False
    assert dialog.switching_checkbox.isChecked() is True
    assert dialog.fault_checkbox.isChecked() is True
    assert dialog.switching_group.isHidden() is False
    assert dialog.fault_group.isHidden() is False
    assert "Final duration" in _table_labels(dialog._tables["common"])
    assert "Final duration" not in _table_labels(dialog._tables["frequency_sweep"])

    dialog.frequency_sweep_checkbox.setChecked(True)
    assert dialog.switching_checkbox.isChecked() is False
    assert dialog.fault_checkbox.isChecked() is False

    dialog.switching_checkbox.setChecked(True)
    common = dialog._tables["common"]
    switching = dialog._tables["switching"]
    common.item(0, 1).setText("60")
    _set_table_value(switching, "N points over wave", "30")
    saved = dialog.input_data_settings()

    assert saved.normalized_studies() == [INPUT_DATA_SWITCHING]
    assert saved.frequency == "60"
    assert saved.residual_flux == "No"
    assert saved.points_over_wave == "30"

    dialog.close()
    dialog.deleteLater()
    QtWidgets.QApplication.processEvents()


def test_input_data_dialog_switching_rows_follow_operation_and_type() -> None:
    _app()
    dialog = InputDataDialog(
        ProjectSettings(input_data=InputDataSettings(studies=[INPUT_DATA_SWITCHING], switch_operation="On", switch_type="Sequential"))
    )

    assert "2nd Switch delay" not in _table_labels(dialog._tables["switching"])
    assert "None" in dialog._tables["switching"].itemDelegateForRow(2).options

    _set_table_value(dialog._tables["switching"], "Switch operation", "On-Off")
    assert "2nd Switch delay" in _table_labels(dialog._tables["switching"])

    _set_table_value(dialog._tables["switching"], "Switch type", "Stochastic 3-pole")
    labels = _table_labels(dialog._tables["switching"])
    assert "N1R" in labels
    assert "N2R" in labels
    assert "N3R" in labels
    assert "Min1R" in labels
    assert "Max1R" in labels
    assert "Min2R" not in labels
    assert "Max2R" not in labels
    assert "Switch start" not in labels

    _set_table_value(dialog._tables["switching"], "Switch type", "Stochastic single-pole")
    labels = _table_labels(dialog._tables["switching"])
    assert "Min2R" in labels
    assert "Max2R" in labels
    assert "Min3R" in labels
    assert "Max3R" in labels

    dialog.close()
    dialog.deleteLater()
    QtWidgets.QApplication.processEvents()


def test_dropdown_table_cells_open_on_single_click() -> None:
    _app()
    dialog = InputDataDialog(ProjectSettings(input_data=InputDataSettings(studies=[INPUT_DATA_SWITCHING])))
    table = dialog._tables["switching"]
    index = table.model().index(0, 1)

    table.scrollTo(index)
    QtTest.QTest.mouseClick(table.viewport(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, table.visualRect(index).center())
    QtWidgets.QApplication.processEvents()

    assert table.findChild(QtWidgets.QComboBox) is not None

    dialog.close()
    dialog.deleteLater()
    QtWidgets.QApplication.processEvents()


def test_combo_delegate_commits_each_selection_without_focus_change() -> None:
    _app()
    table = create_editor_table(None, ["Value"], editable=True)
    table.setRowCount(1)
    table.setItem(0, 0, QtWidgets.QTableWidgetItem("A"))
    table.setItemDelegateForColumn(0, ComboBoxDelegate(["A", "B", "C"], table))

    _select_combo_value(table, 0, 0, "B")
    assert table.item(0, 0).text() == "B"

    _select_combo_value(table, 0, 0, "C")
    assert table.item(0, 0).text() == "C"

    table.close()
    table.deleteLater()
    QtWidgets.QApplication.processEvents()


def _table_labels(table) -> list[str]:  # noqa: ANN001
    return [table.item(row, 0).text() for row in range(table.rowCount())]


def _set_table_value(table, label: str, value: str) -> None:  # noqa: ANN001
    for row in range(table.rowCount()):
        if table.item(row, 0).text() == label:
            table.item(row, 1).setText(value)
            return
    raise AssertionError(f"Missing table row: {label}")


def _select_combo_value(table, row: int, column: int, value: str) -> None:  # noqa: ANN001
    index = table.model().index(row, column)
    table.edit(index)
    QtWidgets.QApplication.processEvents()
    editor = table.findChild(QtWidgets.QComboBox)
    assert editor is not None
    editor.setCurrentText(value)
    editor.activated.emit(editor.currentIndex())
    QtWidgets.QApplication.processEvents()
