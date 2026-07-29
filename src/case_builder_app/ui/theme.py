from __future__ import annotations

from dataclasses import dataclass

from PySide6 import QtGui, QtWidgets


def _mix(first: QtGui.QColor, second: QtGui.QColor, amount: float) -> QtGui.QColor:
    amount = max(0.0, min(1.0, amount))
    return QtGui.QColor.fromRgb(
        round(first.red() * (1 - amount) + second.red() * amount),
        round(first.green() * (1 - amount) + second.green() * amount),
        round(first.blue() * (1 - amount) + second.blue() * amount),
    )


def _contrast_text(background: QtGui.QColor) -> QtGui.QColor:
    luminance = (0.299 * background.red() + 0.587 * background.green() + 0.114 * background.blue()) / 255
    return QtGui.QColor("#111111" if luminance >= 0.55 else "#ffffff")


def _relative_luminance(color: QtGui.QColor) -> float:
    channels = []
    for value in (color.red(), color.green(), color.blue()):
        channel = value / 255
        channels.append(channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _readable_text(background: QtGui.QColor, preferred: QtGui.QColor) -> QtGui.QColor:
    lighter = max(_relative_luminance(background), _relative_luminance(preferred))
    darker = min(_relative_luminance(background), _relative_luminance(preferred))
    if (lighter + 0.05) / (darker + 0.05) >= 3.0:
        return preferred
    return _contrast_text(background)


def _role(
    palette: QtGui.QPalette,
    role: QtGui.QPalette.ColorRole,
    group: QtGui.QPalette.ColorGroup = QtGui.QPalette.ColorGroup.Active,
) -> QtGui.QColor:
    return palette.color(group, role)


@dataclass(frozen=True)
class ThemeColors:
    window: QtGui.QColor
    base: QtGui.QColor
    alternate_base: QtGui.QColor
    text: QtGui.QColor
    muted_text: QtGui.QColor
    button: QtGui.QColor
    button_text: QtGui.QColor
    header_background: QtGui.QColor
    header_text: QtGui.QColor
    border: QtGui.QColor
    strong_border: QtGui.QColor
    highlight: QtGui.QColor
    highlighted_text: QtGui.QColor
    inherited_background: QtGui.QColor
    inherited_border: QtGui.QColor
    inherited_text: QtGui.QColor
    overridden_background: QtGui.QColor
    overridden_border: QtGui.QColor
    overridden_text: QtGui.QColor
    added_background: QtGui.QColor
    added_border: QtGui.QColor
    added_text: QtGui.QColor
    off_background: QtGui.QColor
    off_border: QtGui.QColor
    switch_background: QtGui.QColor
    switch_border: QtGui.QColor
    on_background: QtGui.QColor
    on_border: QtGui.QColor

    @classmethod
    def from_palette(cls, palette: QtGui.QPalette | None = None) -> "ThemeColors":
        if palette is None:
            app = QtWidgets.QApplication.instance()
            palette = app.palette() if app is not None else QtGui.QPalette()

        window = _role(palette, QtGui.QPalette.ColorRole.Window)
        base = _role(palette, QtGui.QPalette.ColorRole.Base)
        alternate_base = _role(palette, QtGui.QPalette.ColorRole.AlternateBase)
        text = _role(palette, QtGui.QPalette.ColorRole.Text)
        muted_text = _role(palette, QtGui.QPalette.ColorRole.Text, QtGui.QPalette.ColorGroup.Disabled)
        button = _role(palette, QtGui.QPalette.ColorRole.Button)
        button_text = _role(palette, QtGui.QPalette.ColorRole.ButtonText)
        border = _role(palette, QtGui.QPalette.ColorRole.Mid)
        strong_border = _role(palette, QtGui.QPalette.ColorRole.Dark)
        highlight = _role(palette, QtGui.QPalette.ColorRole.Highlight)
        highlighted_text = _role(palette, QtGui.QPalette.ColorRole.HighlightedText)
        dark = window.lightness() < 128
        if dark and base.lightness() > 160:
            base = _mix(window, QtGui.QColor("#ffffff"), 0.08)
        elif not dark and base.lightness() < 80:
            base = _mix(window, QtGui.QColor("#000000"), 0.08)
        if dark and alternate_base.lightness() > 160:
            alternate_base = _mix(window, QtGui.QColor("#ffffff"), 0.12)
        elif not dark and alternate_base.lightness() < 80:
            alternate_base = _mix(window, QtGui.QColor("#000000"), 0.08)
        text = _readable_text(base, text)
        button_text = _readable_text(button, button_text)
        header_background = alternate_base
        header_text = _readable_text(header_background, text)
        tint_amount = 0.34 if dark else 0.12
        border_amount = 0.58 if dark else 0.38

        def accent(color: str) -> tuple[QtGui.QColor, QtGui.QColor]:
            tint = QtGui.QColor(color)
            return _mix(base, tint, tint_amount), _mix(border, tint, border_amount)

        inherited_background, inherited_border = accent("#607d8b")
        overridden_background, overridden_border = accent("#8e62b5")
        added_background, added_border = accent("#3b8a5a")
        off_background, off_border = accent("#3b8a5a")
        switch_background, switch_border = accent("#b87916")
        on_background, on_border = accent("#b34a3d")

        return cls(
            window=window,
            base=base,
            alternate_base=alternate_base,
            text=text,
            muted_text=muted_text,
            button=button,
            button_text=button_text,
            header_background=header_background,
            header_text=header_text,
            border=border,
            strong_border=strong_border,
            highlight=highlight,
            highlighted_text=highlighted_text,
            inherited_background=inherited_background,
            inherited_border=inherited_border,
            inherited_text=_mix(text, base, 0.35),
            overridden_background=overridden_background,
            overridden_border=overridden_border,
            overridden_text=_contrast_text(overridden_background),
            added_background=added_background,
            added_border=added_border,
            added_text=_contrast_text(added_background),
            off_background=off_background,
            off_border=off_border,
            switch_background=switch_background,
            switch_border=switch_border,
            on_background=on_background,
            on_border=on_border,
        )


def _css(color: QtGui.QColor) -> str:
    return color.name()


def editor_table_stylesheet(palette: QtGui.QPalette | None = None) -> str:
    colors = ThemeColors.from_palette(palette)
    return f"""
QTableWidget#editorTable {{
    background: {_css(colors.base)};
    color: {_css(colors.text)};
    alternate-background-color: {_css(colors.alternate_base)};
    border: 1px solid {_css(colors.border)};
    border-radius: 6px;
    gridline-color: {_css(colors.border)};
    selection-background-color: {_css(colors.highlight)};
    selection-color: {_css(colors.highlighted_text)};
}}
QTableWidget#editorTable::item {{
    padding: 6px 8px;
}}
QHeaderView::section {{
    background: {_css(colors.header_background)};
    color: {_css(colors.header_text)};
    font-weight: 600;
    padding: 8px 10px;
    border-top: 0px;
    border-left: 0px;
    border-right: 1px solid {_css(colors.border)};
    border-bottom: 2px solid {_css(colors.strong_border)};
}}
QTableWidget#editorTable QHeaderView {{
    background: {_css(colors.header_background)};
    color: {_css(colors.header_text)};
}}
QTableWidget#editorTable QHeaderView::section:horizontal {{
    background: {_css(colors.header_background)};
    color: {_css(colors.header_text)};
}}
QTableWidget QHeaderView::section:vertical {{
    background: {_css(colors.header_background)};
    color: {_css(colors.header_text)};
    border-right: 1px solid {_css(colors.border)};
    border-bottom: 1px solid {_css(colors.border)};
}}
QTableCornerButton::section {{
    background: {_css(colors.alternate_base)};
    border-top: 0px;
    border-left: 0px;
    border-right: 1px solid {_css(colors.border)};
    border-bottom: 2px solid {_css(colors.strong_border)};
}}
QLineEdit, QPlainTextEdit, QComboBox {{
    background: {_css(colors.base)};
    color: {_css(colors.text)};
    selection-background-color: {_css(colors.highlight)};
    selection-color: {_css(colors.highlighted_text)};
}}
"""


def changes_editor_stylesheet(palette: QtGui.QPalette | None = None) -> str:
    colors = ThemeColors.from_palette(palette)
    return f"""
QFrame#selectorBar {{
    background: {_css(colors.alternate_base)};
    border: 1px solid {_css(colors.border)};
    border-radius: 10px;
}}
QToolButton#selectorButton {{
    background: {_css(colors.button)};
    border: 1px solid {_css(colors.border)};
    border-radius: 16px;
    padding: 6px 12px;
    color: {_css(colors.button_text)};
    font-weight: 600;
}}
QToolButton#selectorButton:checked {{
    background: {_css(colors.highlight)};
    border-color: {_css(colors.strong_border)};
    color: {_css(colors.highlighted_text)};
}}
QGroupBox#sectionCard {{
    background: {_css(colors.window)};
    color: {_css(colors.text)};
    border: 1px solid {_css(colors.border)};
    border-radius: 10px;
    margin-top: 22px;
    padding: 12px;
    font-weight: 600;
}}
QGroupBox#sectionCard::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px 4px 6px;
    color: {_css(colors.text)};
}}
QFrame#cbLaneFrame {{
    border-radius: 8px;
}}
QFrame#cbLaneFrame[accent="off"] {{
    background: {_css(colors.off_background)};
    border: 1px solid {_css(colors.off_border)};
}}
QFrame#cbLaneFrame[accent="off"][active="true"] {{
    background: {_css(colors.added_background)};
    border: 1px solid {_css(colors.added_border)};
}}
QFrame#cbLaneFrame[accent="switch"] {{
    background: {_css(colors.switch_background)};
    border: 1px solid {_css(colors.switch_border)};
}}
QFrame#cbLaneFrame[accent="switch"][active="true"] {{
    background: {_css(colors.switch_background)};
    border: 1px solid {_css(colors.strong_border)};
}}
QFrame#cbLaneFrame[accent="on"] {{
    background: {_css(colors.on_background)};
    border: 1px solid {_css(colors.on_border)};
}}
QFrame#cbLaneFrame[accent="on"][active="true"] {{
    background: {_css(colors.on_background)};
    border: 1px solid {_css(colors.strong_border)};
}}
QFrame#cbPreviewFrame {{
    background: {_css(colors.alternate_base)};
    border: 1px solid {_css(colors.border)};
    border-radius: 8px;
}}
QLabel#cbPreviewTitle, QLabel#cbLaneTitle {{
    color: {_css(colors.text)};
    font-weight: 700;
}}
QLabel#cbPreviewLabel {{
    color: {_css(colors.muted_text)};
    font-weight: 600;
}}
QPushButton#cbPreviewButton {{
    background: {_css(colors.button)};
    color: {_css(colors.button_text)};
    border: 1px solid {_css(colors.border)};
    border-radius: 12px;
    padding: 4px 10px;
    min-width: 44px;
}}
QPushButton#cbPreviewButton:checked {{
    background: {_css(colors.highlight)};
    color: {_css(colors.highlighted_text)};
    border-color: {_css(colors.strong_border)};
    font-weight: 700;
}}
QLineEdit {{
    min-height: 28px;
}}
""" + editor_table_stylesheet(palette)


def main_window_stylesheet(palette: QtGui.QPalette | None = None) -> str:
    colors = ThemeColors.from_palette(palette)
    return f"""
QLabel#projectPathLabel {{
    color: {_css(colors.text)};
    background: {_css(colors.alternate_base)};
    border: 1px solid {_css(colors.border)};
    border-radius: 8px;
    padding: 3px 10px;
    font-weight: 600;
}}
QLabel#projectNoticeLabel {{
    color: {_css(colors.added_text)};
    background: {_css(colors.added_background)};
    border: 1px solid {_css(colors.added_border)};
    border-radius: 8px;
    padding: 3px 10px;
    font-weight: 600;
}}
QPushButton#primaryExportButton {{
    color: {_css(colors.added_text)};
    background: {_css(colors.added_background)};
    border: 1px solid {_css(colors.added_border)};
}}
QPushButton#primaryExportButton:disabled {{
    color: {_css(colors.muted_text)};
    background: {_css(colors.alternate_base)};
}}
"""
