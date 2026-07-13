import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from case_builder_app.models import ParameterChange, ValueChanges
from case_builder_app.ui.cb_state_board import CBChipDelegate
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


def test_parameter_and_layer_tables_support_inline_editing(editor: ChangesEditor) -> None:
    assert editor.parameter_table.rowCount() == 3
    assert editor.layer_table.rowCount() == 3
    assert editor.flux_table.rowCount() == 3

    editor.parameter_checkbox.setChecked(True)
    editor.parameter_table.item(0, 0).setText("Main")
    editor.parameter_table.item(0, 1).setText("Q_target")
    editor.parameter_table.item(0, 2).setText("1.0")

    editor._add_parameter_row()
    assert editor.parameter_table.rowCount() == 4

    parameters = editor.get_changes().parameters
    assert len(parameters) == 1
    assert parameters[0].definition == "Main"
    assert parameters[0].parameter == "Q_target"
    assert parameters[0].value == "1.0"

    editor.parameter_table.setCurrentCell(3, 0)
    editor.parameter_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(3, 0, 3, 2), True)
    editor._remove_parameter_rows()
    assert editor.parameter_table.rowCount() == 3

    editor.layer_checkbox.setChecked(True)
    editor.layer_table.item(0, 0).setText("Sweep_Components")
    editor.layer_table.item(0, 1).setText("Main")
    editor.layer_table.item(0, 2).setText("FS_OSSHV1")
    editor.layer_table.item(0, 3).setText("Enable")

    editor._add_layer_row()
    assert editor.layer_table.rowCount() == 4

    layers = editor.get_changes().layers
    assert len(layers) == 1
    assert layers[0].section == "Sweep_Components"
    assert layers[0].layer_type == "Main"
    assert layers[0].target == "FS_OSSHV1"
    assert layers[0].state == "Enable"

    editor.layer_table.setCurrentCell(3, 0)
    editor.layer_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(3, 0, 3, 3), True)
    editor._remove_layer_rows()
    assert editor.layer_table.rowCount() == 3

    editor.flux_checkbox.setChecked(True)
    editor.flux_table.item(0, 0).setText("Main")
    editor.flux_table.item(0, 1).setText("TR1")
    editor.flux_table.item(0, 2).setText("0.8,-0.4,-0.4")

    editor._add_flux_row()
    assert editor.flux_table.rowCount() == 4

    flux = editor.get_changes().flux
    assert len(flux) == 1
    assert flux[0].layer == "Main"
    assert flux[0].transformer == "TR1"
    assert flux[0].value == "0.8,-0.4,-0.4"

    editor.flux_table.setCurrentCell(3, 0)
    editor.flux_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(3, 0, 3, 2), True)
    editor._remove_flux_rows()
    assert editor.flux_table.rowCount() == 3


def test_default_table_rows_can_be_deleted(editor: ChangesEditor) -> None:
    editor.parameter_checkbox.setChecked(True)
    editor.parameter_table.item(0, 0).setText("Main")
    editor.parameter_table.item(0, 1).setText("Q_target")
    editor.parameter_table.item(0, 2).setText("1.0")
    editor.parameter_table.item(1, 0).setText("Main")
    editor.parameter_table.item(1, 1).setText("P_target")
    editor.parameter_table.item(1, 2).setText("2.0")
    editor.parameter_table.item(2, 0).setText("Main")
    editor.parameter_table.item(2, 1).setText("I_target")
    editor.parameter_table.item(2, 2).setText("3.0")

    editor.parameter_table.setCurrentCell(2, 0)
    editor.parameter_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(2, 0, 2, 2), True)
    editor._remove_parameter_rows()

    assert editor.parameter_table.rowCount() == 2
    parameters = editor.get_changes().parameters
    assert len(parameters) == 2
    assert [item.parameter for item in parameters] == ["Q_target", "P_target"]


def test_fault_level_table_accepts_direct_cell_paste(editor: ChangesEditor) -> None:
    assert editor.fault_table.rowCount() == 4
    assert [editor.fault_table.item(row, 0).text() for row in range(4)] == ["R+", "X+", "R0", "X0"]

    editor.fault_checkbox.setChecked(True)
    QtWidgets.QApplication.clipboard().setText("0.1\n0.2\n0.3\n0.4")
    editor.fault_table.setCurrentCell(0, 1)
    editor.fault_table.paste_cells_from_clipboard()

    changes = editor.get_changes()
    assert changes.fault_level.rpos == "0.1"
    assert changes.fault_level.xpos == "0.2"
    assert changes.fault_level.rzero == "0.3"
    assert changes.fault_level.xzero == "0.4"
    assert editor.fault_table.rowCount() == 4

    editor.fault_table.item(2, 1).setText("0.33")
    changes = editor.get_changes()
    assert changes.fault_level.rzero == "0.33"


def test_editable_tables_support_rectangular_copy_paste(editor: ChangesEditor) -> None:
    editor.parameter_checkbox.setChecked(True)
    editor.parameter_table.item(0, 0).setText("Main")
    editor.parameter_table.item(0, 1).setText("Q_target")
    editor.parameter_table.item(0, 2).setText("1.0")

    editor.parameter_table.setCurrentCell(0, 0)
    editor.parameter_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(0, 0, 0, 2), True)
    editor.parameter_table.copy_selected_cells()
    editor.parameter_table.setCurrentCell(1, 0)
    editor.parameter_table.paste_cells_from_clipboard()

    assert editor.parameter_table.item(1, 0).text() == "Main"
    assert editor.parameter_table.item(1, 1).text() == "Q_target"
    assert editor.parameter_table.item(1, 2).text() == "1.0"

    editor.layer_checkbox.setChecked(True)
    editor.layer_table.item(0, 0).setText("Sweep_Components")
    editor.layer_table.item(0, 1).setText("Main")
    editor.layer_table.item(0, 2).setText("FS_OSSHV1")
    editor.layer_table.item(0, 3).setText("Enable")

    editor.layer_table.setCurrentCell(0, 0)
    editor.layer_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(0, 0, 0, 3), True)
    editor.layer_table.copy_selected_cells()
    editor.layer_table.setCurrentCell(1, 0)
    editor.layer_table.paste_cells_from_clipboard()

    assert editor.layer_table.item(1, 0).text() == "Sweep_Components"
    assert editor.layer_table.item(1, 1).text() == "Main"
    assert editor.layer_table.item(1, 2).text() == "FS_OSSHV1"
    assert editor.layer_table.item(1, 3).text() == "Enable"

    editor.flux_checkbox.setChecked(True)
    editor.flux_table.item(0, 0).setText("Main")
    editor.flux_table.item(0, 1).setText("TR1")
    editor.flux_table.item(0, 2).setText("0.8,-0.4,-0.4")

    editor.flux_table.setCurrentCell(0, 0)
    editor.flux_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(0, 0, 0, 2), True)
    editor.flux_table.copy_selected_cells()
    editor.flux_table.setCurrentCell(1, 0)
    editor.flux_table.paste_cells_from_clipboard()

    assert editor.flux_table.item(1, 0).text() == "Main"
    assert editor.flux_table.item(1, 1).text() == "TR1"
    assert editor.flux_table.item(1, 2).text() == "0.8,-0.4,-0.4"


def test_editable_tables_support_cut_for_selected_cells(editor: ChangesEditor) -> None:
    editor.parameter_checkbox.setChecked(True)
    editor.parameter_table.item(0, 0).setText("Main")
    editor.parameter_table.item(0, 1).setText("Q_target")
    editor.parameter_table.item(0, 2).setText("1.0")

    editor.parameter_table.setCurrentCell(0, 0)
    editor.parameter_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(0, 0, 0, 2), True)
    cut_event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_X, QtCore.Qt.ControlModifier)
    editor.parameter_table.keyPressEvent(cut_event)

    assert QtWidgets.QApplication.clipboard().text() == "Main\tQ_target\t1.0"
    assert editor.parameter_table.item(0, 0).text() == ""
    assert editor.parameter_table.item(0, 1).text() == ""
    assert editor.parameter_table.item(0, 2).text() == ""

    editor.flux_checkbox.setChecked(True)
    editor.flux_table.item(0, 0).setText("Main")
    editor.flux_table.item(0, 1).setText("TR1")
    editor.flux_table.item(0, 2).setText("0.8,-0.4,-0.4")

    editor.flux_table.setCurrentCell(0, 0)
    editor.flux_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(0, 0, 0, 2), True)
    cut_event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_X, QtCore.Qt.ControlModifier)
    editor.flux_table.keyPressEvent(cut_event)

    assert QtWidgets.QApplication.clipboard().text() == "Main\tTR1\t0.8,-0.4,-0.4"
    assert editor.flux_table.item(0, 0).text() == ""
    assert editor.flux_table.item(0, 1).text() == ""
    assert editor.flux_table.item(0, 2).text() == ""


def test_editable_tables_use_interactive_headers_and_default_widths(editor: ChangesEditor) -> None:
    parameter_header = editor.parameter_table.horizontalHeader()
    layer_header = editor.layer_table.horizontalHeader()
    fault_header = editor.fault_table.horizontalHeader()
    flux_header = editor.flux_table.horizontalHeader()

    for column in range(editor.parameter_table.columnCount()):
        assert parameter_header.sectionResizeMode(column) == QtWidgets.QHeaderView.Interactive

    for column in range(editor.layer_table.columnCount()):
        assert layer_header.sectionResizeMode(column) == QtWidgets.QHeaderView.Interactive

    for column in range(editor.fault_table.columnCount()):
        assert fault_header.sectionResizeMode(column) == QtWidgets.QHeaderView.Interactive

    for column in range(editor.flux_table.columnCount()):
        assert flux_header.sectionResizeMode(column) == QtWidgets.QHeaderView.Interactive

    assert editor.parameter_table.selectionBehavior() == QtWidgets.QAbstractItemView.SelectItems
    assert editor.layer_table.selectionBehavior() == QtWidgets.QAbstractItemView.SelectItems
    assert editor.fault_table.selectionBehavior() == QtWidgets.QAbstractItemView.SelectItems
    assert editor.flux_table.selectionBehavior() == QtWidgets.QAbstractItemView.SelectItems

    assert editor.parameter_table.columnWidth(0) >= 220
    assert editor.parameter_table.columnWidth(1) >= 220
    assert editor.parameter_table.columnWidth(2) >= 160
    assert editor.fault_table.columnWidth(0) >= 120
    assert editor.fault_table.columnWidth(1) >= 220
    assert editor.layer_table.columnWidth(0) >= 240
    assert editor.layer_table.columnWidth(1) >= 120
    assert editor.layer_table.columnWidth(2) >= 280
    assert editor.layer_table.columnWidth(3) >= 140
    assert editor.flux_table.columnWidth(0) >= 180
    assert editor.flux_table.columnWidth(1) >= 240
    assert editor.flux_table.columnWidth(2) >= 220


def test_fault_table_uses_outer_scroll_instead_of_inner_vertical_scroll(editor: ChangesEditor) -> None:
    editor.fault_checkbox.setChecked(True)

    assert editor.fault_table.rowCount() == 4
    assert editor.fault_table.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarAlwaysOff
    assert editor.fault_table.height() > 0


def test_editable_tables_grow_before_enabling_internal_vertical_scroll(editor: ChangesEditor) -> None:
    editor.parameter_checkbox.setChecked(True)

    initial_height = editor.parameter_table.height()
    for _ in range(4):
        editor._add_parameter_row()

    assert editor.parameter_table.rowCount() == 7
    assert editor.parameter_table.height() > initial_height
    assert editor.parameter_table.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarAlwaysOff

    for _ in range(4):
        editor._add_parameter_row()

    assert editor.parameter_table.rowCount() == 11
    assert editor.parameter_table.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarAsNeeded

    editor.flux_checkbox.setChecked(True)
    initial_flux_height = editor.flux_table.height()
    for _ in range(4):
        editor._add_flux_row()

    assert editor.flux_table.rowCount() == 7
    assert editor.flux_table.height() > initial_flux_height
    assert editor.flux_table.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarAlwaysOff


def test_cb_state_board_supports_multi_select_delete_and_filters(editor: ChangesEditor) -> None:
    editor.cb_checkbox.setChecked(True)

    assert editor.cb_board._lane_frames["off"].property("active") is True
    assert editor.cb_board._lane_frames["switch"].property("active") is False

    off_lane = editor.cb_board._lanes["off"]
    on_lane = editor.cb_board._lanes["on"]

    editor.cb_board._handle_tokens_dropped("on", ["CB_A", "CB_B", "CB_C", "CB_D"], None)
    editor.cb_board._handle_tokens_dropped("off", ["CB_X"], None)

    assert on_lane.tokens() == ["CB_A", "CB_B", "CB_C", "CB_D"]
    assert off_lane.tokens() == ["CB_X"]
    assert not editor.cb_board.delete_button.isEnabled()

    editor.cb_board._activate_lane_from_container("on")
    assert editor.cb_board._lane_frames["on"].property("active") is True
    assert editor.cb_board._lane_frames["off"].property("active") is False
    assert not editor.cb_board.delete_button.isEnabled()

    assert on_lane.item(0).text() == "Unknown voltage"
    on_lane.setCurrentRow(1)
    on_lane.item(1).setSelected(True)
    on_lane.item(3).setSelected(True)
    assert editor.cb_board.delete_button.isEnabled()
    editor.cb_board.delete_button.click()

    assert on_lane.tokens() == ["CB_B", "CB_D"]
    assert editor.cb_board.undo_button.isEnabled()

    editor.cb_board.undo()
    assert on_lane.tokens() == ["CB_A", "CB_B", "CB_C", "CB_D"]

    editor.cb_board.redo()
    assert on_lane.tokens() == ["CB_B", "CB_D"]

    editor.cb_board.include_edit.setText("D")
    assert not on_lane.item(0).isHidden()
    assert on_lane.item(1).isHidden()
    assert not on_lane.item(2).isHidden()

    editor.cb_board.include_edit.clear()
    editor.cb_board.exclude_edit.setText("X")
    assert off_lane.item(0).isHidden()

    on_lane.item(1).setSelected(True)
    empty_point = QtCore.QPointF(off_lane.rect().right() - 6, off_lane.rect().bottom() - 6)
    empty_click = QtGui.QMouseEvent(
        QtCore.QEvent.MouseButtonPress,
        empty_point,
        empty_point,
        QtCore.Qt.LeftButton,
        QtCore.Qt.LeftButton,
        QtCore.Qt.NoModifier,
    )
    off_lane.mousePressEvent(empty_click)
    assert editor.cb_board._lane_frames["off"].property("active") is True
    assert editor.cb_board._lane_frames["on"].property("active") is False
    assert not editor.cb_board.delete_button.isEnabled()

    changes = editor.get_changes()
    assert changes.cb.off == ["CB_X"]
    assert changes.cb.on == ["CB_B", "CB_D"]


def test_cb_state_board_supports_cut_for_selected_cards(editor: ChangesEditor) -> None:
    editor.cb_checkbox.setChecked(True)

    on_lane = editor.cb_board._lanes["on"]
    editor.cb_board._handle_tokens_dropped("on", ["CB_A", "CB_B", "CB_C"], None)

    on_lane.item(1).setSelected(True)
    on_lane.item(3).setSelected(True)
    cut_event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_X, QtCore.Qt.ControlModifier)
    on_lane.keyPressEvent(cut_event)

    assert QtWidgets.QApplication.clipboard().text() == "CB_A\nCB_C"
    assert on_lane.tokens() == ["CB_B"]
    assert editor.cb_board.undo_button.isEnabled()


def test_cb_state_board_shows_same_as_base_cb_as_explicit_local_override(editor: ChangesEditor) -> None:
    base = ValueChanges(use_cb=True)
    base.cb.off = ["CB_66_A"]
    local = ValueChanges(use_cb=True)
    local.cb.off = ["CB_66_A"]

    editor.set_context(base_changes=base, is_base_case=False)
    editor.set_changes(local)

    off_lane = editor.cb_board._lanes["off"]
    token_item = next(
        off_lane.item(row)
        for row in range(off_lane.count())
        if not bool(off_lane.item(row).data(CBChipDelegate.GROUP_ROLE))
    )
    assert token_item.text() == "CB_66_A"
    assert token_item.data(CBChipDelegate.STATUS_ROLE) == "overridden"
    assert editor.get_changes().cb.off == ["CB_66_A"]

    token_item.setSelected(True)
    editor.cb_board.delete_button.click()

    inherited_item = next(
        off_lane.item(row)
        for row in range(off_lane.count())
        if not bool(off_lane.item(row).data(CBChipDelegate.GROUP_ROLE))
    )
    assert inherited_item.data(CBChipDelegate.STATUS_ROLE) == "inherited"
    assert editor.get_changes().cb.off == []


def test_section_buttons_enable_only_for_actionable_selection(editor: ChangesEditor) -> None:
    base = ValueChanges(
        use_parameters=True,
        use_fault_level=True,
        parameters=[
            ParameterChange(definition="Main", parameter="P", value="1"),
            ParameterChange(definition="Main", parameter="Q", value="2"),
        ],
    )
    base.fault_level.rpos = "0.1"
    base.fault_level.xpos = "0.2"
    base.fault_level.rzero = "0.3"
    base.fault_level.xzero = "0.4"

    local = ValueChanges(
        use_parameters=True,
        use_fault_level=True,
        parameters=[ParameterChange(definition="Main", parameter="P", value="9")],
    )
    local.fault_level.rpos = "0.9"

    editor.set_context(base_changes=base, is_base_case=False)
    editor.set_changes(local)

    assert editor.parameter_add_button.isEnabled() is True
    assert editor.parameter_remove_button.isEnabled() is False
    assert editor.parameter_revert_button.isEnabled() is False
    assert editor.fault_revert_button.isEnabled() is False

    editor.parameter_table.setCurrentCell(1, 2)
    editor.parameter_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(1, 0, 1, 2), True)
    QtWidgets.QApplication.processEvents()
    assert editor.parameter_remove_button.isEnabled() is False
    assert editor.parameter_revert_button.isEnabled() is False

    editor.parameter_table.clearSelection()
    editor.parameter_table.setCurrentCell(0, 2)
    editor.parameter_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(0, 0, 0, 2), True)
    QtWidgets.QApplication.processEvents()
    assert editor.parameter_remove_button.isEnabled() is True
    assert editor.parameter_revert_button.isEnabled() is True

    editor.fault_table.setCurrentCell(1, 1)
    editor.fault_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(1, 1, 1, 1), True)
    QtWidgets.QApplication.processEvents()
    assert editor.fault_revert_button.isEnabled() is False

    editor.fault_table.clearSelection()
    editor.fault_table.setCurrentCell(0, 1)
    editor.fault_table.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(0, 1, 0, 1), True)
    QtWidgets.QApplication.processEvents()
    assert editor.fault_revert_button.isEnabled() is True
