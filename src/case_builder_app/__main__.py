from __future__ import annotations

import sys
import ctypes

from PySide6 import QtWidgets

from case_builder_app.assets import load_icon


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MPE.CaseCreatorApp")
    except OSError:
        pass


def main() -> int:
    _set_windows_app_id()
    from case_builder_app.ui.main_window import MainWindow

    app = QtWidgets.QApplication(sys.argv)
    icon = load_icon("mpe_app_icon.ico", "mpe_app_icon.png")
    if icon is not None:
        app.setWindowIcon(icon)
    window = MainWindow(app_icon=icon)
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
