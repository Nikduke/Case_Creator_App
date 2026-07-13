import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore, QtWidgets

from case_builder_app.models import CBChanges, LayerChange, ParameterChange, Project, ValueChanges
from case_builder_app.ui.changes_editor import ChangesEditor


def _app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def editor():
    _app()
    widget = ChangesEditor()
    yield widget
    widget.close()
    widget.deleteLater()
    QtWidgets.QApplication.processEvents()


def test_changes_editor_shows_base_inherited_and_local_parameter_overrides(editor: ChangesEditor) -> None:
    base = ValueChanges(
        use_parameters=True,
        parameters=[
            ParameterChange(definition="Main", parameter="P", value="1"),
            ParameterChange(definition="Main", parameter="Q", value="2"),
        ],
    )
    local = ValueChanges(
        use_parameters=True,
        parameters=[
            ParameterChange(definition="Main", parameter="P", value="9"),
            ParameterChange(definition="Extra", parameter="R", value="5"),
        ],
    )

    editor.set_context(base_changes=base, is_base_case=False)
    editor.set_changes(local)

    assert editor.parameter_table.item(0, 0).text() == "Main"
    assert editor.parameter_table.item(0, 1).text() == "P"
    assert editor.parameter_table.item(0, 2).text() == "9"
    assert bool(editor.parameter_table.item(0, 0).flags() & QtCore.Qt.ItemIsEditable)
    assert editor.parameter_table.item(1, 2).text() == "2"
    assert editor.parameter_table.item(2, 0).text() == "Extra"
    assert editor.parameter_table.item(2, 1).text() == "R"
    assert editor.parameter_table.item(2, 2).text() == "5"

    changes = editor.get_changes()
    assert len(changes.parameters) == 2
    assert changes.parameters[0].base_row_id == base.parameters[0].id
    assert (changes.parameters[0].definition, changes.parameters[0].parameter, changes.parameters[0].value) == ("", "", "9")
    assert (changes.parameters[1].definition, changes.parameters[1].parameter, changes.parameters[1].value) == ("Extra", "R", "5")


def test_cb_board_renders_resolved_base_and_local_states_but_keeps_local_storage(editor: ChangesEditor) -> None:
    base = ValueChanges(use_cb=True, cb=CBChanges(off=["CB_A"], on=["CB_B"]))
    local = ValueChanges(use_cb=True, cb=CBChanges(on=["CB_A"], switch=["CB_C"]))

    editor.set_context(base_changes=base, is_base_case=False)
    editor.set_changes(local)

    assert editor.cb_board._lanes["off"].tokens() == []
    assert editor.cb_board._lanes["switch"].tokens() == ["CB_C"]
    assert editor.cb_board._lanes["on"].tokens() == ["CB_A", "CB_B"]

    changes = editor.get_changes()
    assert changes.cb.off == []
    assert changes.cb.switch == ["CB_C"]
    assert changes.cb.on == ["CB_A"]


def test_cb_add_list_is_base_case_only_and_defaults_new_cbs_to_on(editor: ChangesEditor) -> None:
    editor.set_context(base_changes=ValueChanges(use_cb=True), is_base_case=True)
    editor.set_changes(ValueChanges(use_cb=True))

    assert editor.cb_board.add_edit.isHidden() is False
    editor.cb_board.add_edit.setPlainText("CB_230_A\nCB_66_B")
    editor.cb_board.add_button.click()

    assert editor.cb_board._lanes["on"].tokens() == ["CB_230_A", "CB_66_B"]
    assert editor.cb_board._lanes["on"].item(0).text() == "230 kV"
    assert editor.cb_board._lanes["on"].item(2).text() == "66 kV"
    assert editor.get_changes().cb.on == ["CB_230_A", "CB_66_B"]

    base = ValueChanges(use_cb=True, cb=CBChanges(on=["CB_230_A"]))
    editor.set_context(base_changes=base, is_base_case=False)
    editor.set_changes(ValueChanges(use_cb=True))

    assert editor.cb_board.add_edit.isHidden() is True
    assert editor.cb_board.add_button.isHidden() is True
    editor.cb_board._handle_tokens_dropped("off", ["CB_66_UNKNOWN"], None)
    assert editor.get_changes().cb.off == []


def test_project_starts_with_default_base_case_metadata() -> None:
    project = Project()

    assert project.base_case.label == "Base Case"
    assert project.base_case.token == "BC"
    assert project.base_case.include_in_case_name is False
    assert project.base_case.changes.use_cb is True
    assert project.base_case.changes.use_parameters is True
    assert project.base_case.changes.use_fault_level is True
    assert project.base_case.changes.use_layers is True


def test_layer_override_follows_base_row_identity_and_allows_full_row_edit(editor: ChangesEditor) -> None:
    base_row = LayerChange(section="Sweep_Components", layer_type="Extra", target="FS_OSSHV1", state="Enable")
    base = ValueChanges(use_layers=True, layers=[base_row])
    local = ValueChanges(
        use_layers=True,
        layers=[LayerChange(base_row_id=base_row.id, section="", layer_type="", target="", state="Disable")],
    )

    editor.set_context(base_changes=base, is_base_case=False)
    editor.set_changes(local)

    for col in range(4):
        assert bool(editor.layer_table.item(0, col).flags() & QtCore.Qt.ItemIsEditable)

    assert [editor.layer_table.item(0, col).text() for col in range(4)] == [
        "Sweep_Components",
        "Extra",
        "FS_OSSHV1",
        "Disable",
    ]

    updated_base = ValueChanges(
        use_layers=True,
        layers=[LayerChange(id=base_row.id, section="Sweep_Components", layer_type="Main", target="FS_OSSLV1", state="Enable")],
    )
    editor.set_context(base_changes=updated_base, is_base_case=False)
    editor.set_changes(local)

    assert [editor.layer_table.item(0, col).text() for col in range(4)] == [
        "Sweep_Components",
        "Main",
        "FS_OSSLV1",
        "Disable",
    ]


def test_editing_inherited_layer_row_creates_sparse_base_row_override(editor: ChangesEditor) -> None:
    base_row = LayerChange(section="Sweep_Components", layer_type="Extra", target="FS_OSSHV1", state="Enable")
    base = ValueChanges(use_layers=True, layers=[base_row])

    editor.set_context(base_changes=base, is_base_case=False)
    editor.set_changes(ValueChanges(use_layers=True))

    editor.layer_checkbox.setChecked(True)
    editor.layer_table.item(0, 1).setText("Main")
    editor.layer_table.item(0, 3).setText("Disable")

    changes = editor.get_changes()

    assert len(changes.layers) == 1
    override = changes.layers[0]
    assert override.base_row_id == base_row.id
    assert override.section == ""
    assert override.layer_type == "Main"
    assert override.target == ""
    assert override.state == "Disable"
