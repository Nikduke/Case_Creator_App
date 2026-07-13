from __future__ import annotations

from importlib import resources

from PySide6 import QtGui


def asset_path(name: str) -> str | None:
    try:
        path = resources.files("case_builder_app.assets").joinpath(name)
    except ModuleNotFoundError:
        return None
    if not path.is_file():
        return None
    return str(path)


def load_icon(*names: str) -> QtGui.QIcon | None:
    for name in names:
        path = asset_path(name)
        if not path:
            continue
        icon = QtGui.QIcon(path)
        if not icon.isNull():
            return icon
    return None
