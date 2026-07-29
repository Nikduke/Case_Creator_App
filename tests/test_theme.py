from __future__ import annotations

import pytest
from PySide6 import QtGui, QtWidgets

from case_builder_app.ui.table_helpers import create_editor_table
from case_builder_app.ui.theme import ThemeColors, _relative_luminance, editor_table_stylesheet


def _contrast_ratio(first: QtGui.QColor, second: QtGui.QColor) -> float:
    lighter = max(_relative_luminance(first), _relative_luminance(second))
    darker = min(_relative_luminance(first), _relative_luminance(second))
    return (lighter + 0.05) / (darker + 0.05)


def _palette(window: str, base: str, alternate_base: str, text: str) -> QtGui.QPalette:
    palette = QtGui.QPalette()
    for role, color in (
        (QtGui.QPalette.ColorRole.Window, window),
        (QtGui.QPalette.ColorRole.Base, base),
        (QtGui.QPalette.ColorRole.AlternateBase, alternate_base),
        (QtGui.QPalette.ColorRole.Text, text),
        (QtGui.QPalette.ColorRole.Button, base),
        (QtGui.QPalette.ColorRole.ButtonText, text),
        (QtGui.QPalette.ColorRole.Mid, "#808080"),
        (QtGui.QPalette.ColorRole.Dark, "#404040"),
        (QtGui.QPalette.ColorRole.Highlight, "#3478c9"),
        (QtGui.QPalette.ColorRole.HighlightedText, "#ffffff"),
    ):
        palette.setColor(role, QtGui.QColor(color))
    return palette


@pytest.mark.parametrize(
    "palette",
    [
        _palette("#f4f4f4", "#ffffff", "#f0f0f0", "#202020"),
        _palette("#202020", "#ffffff", "#ffffff", "#ffffff"),
    ],
)
def test_editor_table_headers_keep_contrast_in_light_and_dark_palettes(qapp, palette) -> None:  # noqa: ANN001
    colors = ThemeColors.from_palette(palette)
    stylesheet = editor_table_stylesheet(palette)

    assert _contrast_ratio(colors.header_background, colors.header_text) >= 3.0
    assert colors.header_background.name() in stylesheet
    assert colors.header_text.name() in stylesheet

    parent = QtWidgets.QWidget()
    table = create_editor_table(parent, ["Header"])
    table.setStyleSheet(stylesheet)
    assert "QHeaderView::section" in table.styleSheet()
    parent.deleteLater()
