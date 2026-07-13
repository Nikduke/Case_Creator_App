from __future__ import annotations

import json
from dataclasses import dataclass

from PySide6 import QtCore, QtGui, QtWidgets

from case_builder_app.models import CBChanges
from case_builder_app.services.equipment import numeric_voltage_token, voltage_sort_key
from case_builder_app.services.text_tokens import parse_token_text
from case_builder_app.ui.token_list import TokenHistory, token_matches_filter


@dataclass(frozen=True)
class CBPreviewValue:
    id: str
    token: str


@dataclass(frozen=True)
class CBPreviewRow:
    case_part_id: str
    label: str
    values: tuple[CBPreviewValue, ...]


class CBChipDelegate(QtWidgets.QStyledItemDelegate):
    _CHIP_HEIGHT = 32
    _CHIP_MARGIN_X = 6
    _CHIP_MARGIN_Y = 3
    _TEXT_PADDING = 10
    _CLOSE_WIDTH = 20
    STATUS_ROLE = QtCore.Qt.UserRole + 1
    GROUP_ROLE = QtCore.Qt.UserRole + 2

    def paint(self, painter, option, index):  # noqa: ANN001
        if bool(index.data(self.GROUP_ROLE)):
            self._paint_group_header(painter, option, index)
            return

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        rect = option.rect.adjusted(
            self._CHIP_MARGIN_X,
            self._CHIP_MARGIN_Y,
            -self._CHIP_MARGIN_X,
            -self._CHIP_MARGIN_Y,
        )
        selected = bool(option.state & QtWidgets.QStyle.State_Selected)
        status = str(index.data(self.STATUS_ROLE) or "plain")
        background = QtGui.QColor("#ffffff")
        border = QtGui.QColor("#d1dbe1")
        text_color = QtGui.QColor("#24343d")
        accent = None
        if status == "inherited":
            background = QtGui.QColor("#f8fbfd")
            border = QtGui.QColor("#d6e0e6")
            text_color = QtGui.QColor("#71808b")
        elif status == "overridden":
            background = QtGui.QColor("#fcfbfe")
            border = QtGui.QColor("#cbb8de")
            accent = QtGui.QColor("#a98cc9")
        elif status == "added":
            background = QtGui.QColor("#eef7f2")
            border = QtGui.QColor("#b8d5c4")
        if selected:
            background = QtGui.QColor("#d9e8f5")
            border = QtGui.QColor("#8ea5b3")
            text_color = QtGui.QColor("#24343d")
        painter.setPen(QtGui.QPen(border, 1))
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 8, 8)
        if accent is not None and not selected:
            accent_rect = QtCore.QRect(rect.left() + 2, rect.top() + 3, 5, max(0, rect.height() - 6))
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(accent_rect, 3, 3)

        text_rect = rect.adjusted(self._TEXT_PADDING, 0, -(self._CLOSE_WIDTH + self._TEXT_PADDING), 0)
        painter.setPen(text_color)
        painter.drawText(text_rect, QtCore.Qt.AlignVCenter | QtCore.Qt.TextSingleLine, str(index.data() or ""))

        close_rect = self.close_rect(rect)
        painter.setPen(QtGui.QColor("#6e7f8b"))
        painter.drawText(close_rect, QtCore.Qt.AlignCenter, "x")
        painter.restore()

    def sizeHint(self, option, index):  # noqa: ANN001
        if bool(index.data(self.GROUP_ROLE)):
            return QtCore.QSize(option.rect.width(), 26)
        return QtCore.QSize(option.rect.width(), self._CHIP_HEIGHT)

    def _paint_group_header(self, painter, option, index):  # noqa: ANN001
        painter.save()
        rect = option.rect.adjusted(8, 4, -8, -2)
        painter.setPen(QtGui.QColor("#60717d"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(max(8, font.pointSize() - 1))
        painter.setFont(font)
        painter.drawText(rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, str(index.data() or "Unknown voltage"))
        line_y = rect.center().y()
        text_width = QtGui.QFontMetrics(font).horizontalAdvance(str(index.data() or "Unknown voltage"))
        painter.setPen(QtGui.QPen(QtGui.QColor("#cfd9df"), 1))
        painter.drawLine(rect.left() + text_width + 10, line_y, rect.right(), line_y)
        painter.restore()

    @classmethod
    def close_rect(cls, rect: QtCore.QRect) -> QtCore.QRect:
        return QtCore.QRect(
            rect.right() - cls._CLOSE_WIDTH - 6,
            rect.top(),
            cls._CLOSE_WIDTH,
            rect.height(),
        )


class CBLaneList(QtWidgets.QListWidget):
    tokens_dropped = QtCore.Signal(str, object, object)
    remove_requested = QtCore.Signal(str)
    tokens_remove_requested = QtCore.Signal(object)
    empty_area_clicked = QtCore.Signal(str)
    activated = QtCore.Signal(str)
    undo_requested = QtCore.Signal()
    redo_requested = QtCore.Signal()
    _MIME_TYPE = "application/x-case-builder-cb-lane"

    def __init__(self, state_key: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.state_key = state_key
        self._delegate = CBChipDelegate(self)
        self.setItemDelegate(self._delegate)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.setSpacing(4)
        self.setStyleSheet(
            """
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                padding: 4px;
            }
            """
        )

    def tokens(self) -> list[str]:
        values: list[str] = []
        for row in range(self.count()):
            item = self.item(row)
            if bool(item.data(CBChipDelegate.GROUP_ROLE)):
                continue
            values.append(str(item.data(QtCore.Qt.UserRole) or item.text()))
        return values

    def visible_count(self) -> int:
        count = 0
        for row in range(self.count()):
            item = self.item(row)
            if bool(item.data(CBChipDelegate.GROUP_ROLE)):
                continue
            if not item.isHidden():
                count += 1
        return count

    def token_count(self) -> int:
        count = 0
        for row in range(self.count()):
            if not bool(self.item(row).data(CBChipDelegate.GROUP_ROLE)):
                count += 1
        return count

    def set_tokens(self, tokens: list[str]) -> None:
        self.clear()
        for token in tokens:
            self.add_token(token)

    def add_token(self, token: str, *, status: str = "plain") -> None:
        item = QtWidgets.QListWidgetItem(token)
        item.setData(QtCore.Qt.UserRole, token)
        item.setData(CBChipDelegate.STATUS_ROLE, status)
        item.setSizeHint(QtCore.QSize(0, 32))
        self.addItem(item)

    def add_group_header(self, title: str) -> None:
        item = QtWidgets.QListWidgetItem(title)
        item.setData(CBChipDelegate.GROUP_ROLE, True)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        item.setSizeHint(QtCore.QSize(0, 26))
        self.addItem(item)

    def remove_token(self, token: str) -> bool:
        for row in range(self.count()):
            item = self.item(row)
            if bool(item.data(CBChipDelegate.GROUP_ROLE)):
                continue
            if str(item.data(QtCore.Qt.UserRole) or item.text()) == token:
                self.takeItem(row)
                return True
        return False

    def apply_filter(self, include_text: str, exclude_text: str) -> None:
        group_rows: list[int] = []
        for row in range(self.count()):
            item = self.item(row)
            if bool(item.data(CBChipDelegate.GROUP_ROLE)):
                group_rows.append(row)
                item.setHidden(False)
                continue
            token = str(item.data(QtCore.Qt.UserRole) or item.text())
            item.setHidden(not token_matches_filter(token, include_text, exclude_text))

        for index, group_row in enumerate(group_rows):
            next_group_row = group_rows[index + 1] if index + 1 < len(group_rows) else self.count()
            has_visible_child = any(not self.item(row).isHidden() for row in range(group_row + 1, next_group_row))
            self.item(group_row).setHidden(not has_visible_child)

    def copy_selected_tokens(self) -> None:
        tokens = self._selected_tokens()
        if not tokens:
            return
        QtWidgets.QApplication.clipboard().setText("\n".join(tokens))

    def paste_tokens_from_clipboard(self) -> None:
        tokens = parse_token_text(QtWidgets.QApplication.clipboard().text())
        if tokens:
            self.activated.emit(self.state_key)
            self.tokens_dropped.emit(self.state_key, tokens, None)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.matches(QtGui.QKeySequence.Undo):
            self.undo_requested.emit()
            event.accept()
            return
        if event.matches(QtGui.QKeySequence.Redo):
            self.redo_requested.emit()
            event.accept()
            return
        if event.matches(QtGui.QKeySequence.Cut):
            tokens = self._selected_tokens()
            if tokens:
                QtWidgets.QApplication.clipboard().setText("\n".join(tokens))
                self.tokens_remove_requested.emit(tokens)
            event.accept()
            return
        if event.matches(QtGui.QKeySequence.Copy):
            self.copy_selected_tokens()
            event.accept()
            return
        if event.matches(QtGui.QKeySequence.Paste):
            self.paste_tokens_from_clipboard()
            event.accept()
            return
        if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            tokens = self._selected_tokens()
            if tokens:
                self.tokens_remove_requested.emit(tokens)
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.activated.emit(self.state_key)
        index = self.indexAt(event.position().toPoint())
        if index.isValid():
            item_rect = self.visualRect(index)
            chip_rect = item_rect.adjusted(
                self._delegate._CHIP_MARGIN_X,
                self._delegate._CHIP_MARGIN_Y,
                -self._delegate._CHIP_MARGIN_X,
                -self._delegate._CHIP_MARGIN_Y,
            )
            if self._delegate.close_rect(chip_rect).contains(event.position().toPoint()):
                self.remove_requested.emit(str(index.data(QtCore.Qt.UserRole) or index.data()))
                event.accept()
                return
        else:
            self.clearSelection()
            self.setCurrentIndex(QtCore.QModelIndex())
            self.empty_area_clicked.emit(self.state_key)
            self.setFocus()
            event.accept()
            return
        super().mousePressEvent(event)

    def startDrag(self, supported_actions) -> None:  # noqa: ANN001
        tokens = self._selected_tokens()
        if not tokens:
            return
        mime = QtCore.QMimeData()
        mime.setData(
            self._MIME_TYPE,
            json.dumps({"source": self.state_key, "tokens": tokens}).encode("utf-8"),
        )
        mime.setText("\n".join(tokens))
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        drag.exec(QtCore.Qt.MoveAction)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if self._extract_tokens(event.mimeData())[0]:
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if self._extract_tokens(event.mimeData())[0]:
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        tokens, source_state = self._extract_tokens(event.mimeData())
        if not tokens:
            super().dropEvent(event)
            return
        self.activated.emit(self.state_key)
        self.tokens_dropped.emit(self.state_key, tokens, source_state)
        self.setFocus()
        event.acceptProposedAction()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        if self.count() == 0:
            message = "Click here or press Ctrl+V to paste CBs"
        elif self.visible_count() == 0:
            message = "No CBs match the current filter"
        else:
            message = ""
        if not message:
            return
        painter = QtGui.QPainter(self.viewport())
        painter.setPen(QtGui.QColor("#70818d"))
        painter.drawText(
            self.viewport().rect().adjusted(16, 6, -16, -16),
            QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter | QtCore.Qt.TextWordWrap,
            message,
        )

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        self.activated.emit(self.state_key)
        super().focusInEvent(event)

    def _selected_tokens(self) -> list[str]:
        selected = self.selectedItems()
        if selected:
            return [
                str(item.data(QtCore.Qt.UserRole) or item.text())
                for item in selected
                if not bool(item.data(CBChipDelegate.GROUP_ROLE))
            ]
        current = self.currentItem()
        if current is not None and not bool(current.data(CBChipDelegate.GROUP_ROLE)):
            return [str(current.data(QtCore.Qt.UserRole) or current.text())]
        return []

    def _extract_tokens(self, mime_data: QtCore.QMimeData) -> tuple[list[str], str | None]:
        if mime_data.hasFormat(self._MIME_TYPE):
            payload = json.loads(bytes(mime_data.data(self._MIME_TYPE)).decode("utf-8"))
            return parse_token_text("\n".join(payload.get("tokens", []))), payload.get("source")
        if mime_data.hasText():
            return parse_token_text(mime_data.text()), None
        return [], None


class CBLaneFrame(QtWidgets.QFrame):
    clicked = QtCore.Signal(str)

    def __init__(self, state_key: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.state_key = state_key

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.state_key)
            event.accept()
            return
        super().mousePressEvent(event)


class CBStateBoard(QtWidgets.QFrame):
    changed = QtCore.Signal()
    preview_changed = QtCore.Signal()
    _MIN_VISIBLE_ROWS = 4
    _MAX_VISIBLE_ROWS = 10
    _STATES = [
        ("off", "OFF", "off"),
        ("switch", "SWITCH", "switch"),
        ("on", "ON", "on"),
    ]

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._loading = False
        self._selection_sync = False
        self._lane_headers: dict[str, QtWidgets.QLabel] = {}
        self._lane_frames: dict[str, QtWidgets.QFrame] = {}
        self._lanes: dict[str, CBLaneList] = {}
        self._history = TokenHistory[dict[str, list[str]]]()
        self._active_state: str | None = None
        self._is_base_case = False
        self._base_state: dict[str, str] = {}
        self._base_by_state: dict[str, list[str]] = {"off": [], "switch": [], "on": []}
        self._local_by_state: dict[str, list[str]] = {"off": [], "switch": [], "on": []}
        self._preview_selection: dict[str, str] = {}
        self._preview_button_groups: list[QtWidgets.QButtonGroup] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        filter_row = QtWidgets.QHBoxLayout()
        filter_row.setSpacing(8)
        include_label = QtWidgets.QLabel("Include", self)
        self.include_edit = QtWidgets.QLineEdit(self)
        self.include_edit.setPlaceholderText("Show only CBs containing...")
        exclude_label = QtWidgets.QLabel("Exclude", self)
        self.exclude_edit = QtWidgets.QLineEdit(self)
        self.exclude_edit.setPlaceholderText("Hide CBs containing...")
        filter_row.addWidget(include_label)
        filter_row.addWidget(self.include_edit, 1)
        filter_row.addWidget(exclude_label)
        filter_row.addWidget(self.exclude_edit, 1)
        layout.addLayout(filter_row)

        self.preview_frame = QtWidgets.QFrame(self)
        self.preview_frame.setObjectName("cbPreviewFrame")
        self.preview_layout = QtWidgets.QVBoxLayout(self.preview_frame)
        self.preview_layout.setContentsMargins(8, 6, 8, 6)
        self.preview_layout.setSpacing(4)
        layout.addWidget(self.preview_frame)
        self.preview_frame.setVisible(False)

        lane_row = QtWidgets.QHBoxLayout()
        lane_row.setSpacing(10)
        for state_key, title, accent in self._STATES:
            frame = CBLaneFrame(state_key, self)
            frame.setObjectName("cbLaneFrame")
            frame.setProperty("accent", accent)
            frame_layout = QtWidgets.QVBoxLayout(frame)
            frame_layout.setContentsMargins(10, 10, 10, 10)
            frame_layout.setSpacing(4)

            header = QtWidgets.QLabel(title, frame)
            header.setObjectName("cbLaneTitle")
            header.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            header.setFixedHeight(28)
            header.setProperty("cb_state_key", state_key)
            header.installEventFilter(self)
            frame_layout.addWidget(header, 0, QtCore.Qt.AlignTop)

            lane = CBLaneList(state_key, frame)
            frame_layout.addWidget(lane, 1)

            self._lane_headers[state_key] = header
            self._lane_frames[state_key] = frame
            self._lanes[state_key] = lane

            frame.clicked.connect(self._activate_lane_from_container)
            lane.activated.connect(self._set_active_lane)
            lane.tokens_dropped.connect(self._handle_tokens_dropped)
            lane.remove_requested.connect(self._remove_token)
            lane.tokens_remove_requested.connect(self._remove_tokens)
            lane.empty_area_clicked.connect(self._clear_all_selections)
            lane.undo_requested.connect(self.undo)
            lane.redo_requested.connect(self.redo)
            lane.itemSelectionChanged.connect(lambda state=state_key: self._handle_lane_selection_changed(state))
            lane_row.addWidget(frame, 1)

        layout.addLayout(lane_row)

        action_row = QtWidgets.QHBoxLayout()
        self.add_edit = QtWidgets.QPlainTextEdit(self)
        self.add_edit.setPlaceholderText("Add CB element/list")
        self.add_edit.setFixedHeight(42)
        self.add_edit.setMaximumWidth(360)
        self.add_button = QtWidgets.QPushButton("Add to ON", self)
        self.add_button.clicked.connect(self._add_entered_tokens)
        action_row.addWidget(self.add_edit, 2)
        action_row.addWidget(self.add_button)
        action_row.addStretch(1)
        self.undo_button = QtWidgets.QPushButton("Undo", self)
        self.redo_button = QtWidgets.QPushButton("Redo", self)
        self.delete_button = QtWidgets.QPushButton("Delete Selected", self)
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        self.delete_button.clicked.connect(self._delete_selected)
        action_row.addWidget(self.undo_button)
        action_row.addWidget(self.redo_button)
        action_row.addWidget(self.delete_button)
        layout.addLayout(action_row)

        self.include_edit.textChanged.connect(self._apply_filters)
        self.exclude_edit.textChanged.connect(self._apply_filters)
        self.add_edit.textChanged.connect(self._update_action_state)
        self._update_action_state()
        self._set_active_lane("off")

    def set_changes(self, cb_changes: CBChanges, *, base_changes: CBChanges | None = None, is_base_case: bool = False) -> None:
        self._loading = True
        self._is_base_case = is_base_case
        self._base_by_state = {
            "off": list(base_changes.off if base_changes is not None else []),
            "switch": list(base_changes.switch if base_changes is not None else []),
            "on": list(base_changes.on if base_changes is not None else []),
        }
        self._base_state = self._flatten_state(self._base_by_state)
        self._local_by_state = {
            "off": list(cb_changes.off),
            "switch": list(cb_changes.switch),
            "on": list(cb_changes.on),
        }
        self.include_edit.clear()
        self.exclude_edit.clear()
        self.add_edit.clear()
        self._render_lanes()
        self._loading = False
        self._reset_history()
        self._update_base_only_controls()

    def get_changes(self) -> CBChanges:
        return CBChanges(
            off=list(self._local_by_state["off"]),
            switch=list(self._local_by_state["switch"]),
            on=list(self._local_by_state["on"]),
        )

    def set_preview_rows(self, rows: list[CBPreviewRow]) -> None:
        previous_selection = dict(self._preview_selection)
        self._preview_selection = {}
        self._preview_button_groups = []
        self._clear_layout(self.preview_layout)

        if not rows:
            self.preview_frame.setVisible(False)
            return

        title = QtWidgets.QLabel("Preview branch", self.preview_frame)
        title.setObjectName("cbPreviewTitle")
        self.preview_layout.addWidget(title)

        for row in rows:
            if not row.values:
                continue
            row_frame = QtWidgets.QFrame(self.preview_frame)
            row_layout = QtWidgets.QHBoxLayout(row_frame)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            label = QtWidgets.QLabel(row.label, row_frame)
            label.setObjectName("cbPreviewLabel")
            label.setMinimumWidth(140)
            row_layout.addWidget(label)

            selected_id = previous_selection.get(row.case_part_id)
            if selected_id not in {value.id for value in row.values}:
                selected_id = row.values[0].id
            self._preview_selection[row.case_part_id] = selected_id

            group = QtWidgets.QButtonGroup(self.preview_frame)
            group.setExclusive(True)
            self._preview_button_groups.append(group)
            for value in row.values:
                button = QtWidgets.QPushButton(value.token, row_frame)
                button.setObjectName("cbPreviewButton")
                button.setCheckable(True)
                button.setChecked(value.id == selected_id)
                button.clicked.connect(
                    lambda _checked=False, case_part_id=row.case_part_id, value_id=value.id: self._select_preview_value(
                        case_part_id,
                        value_id,
                    )
                )
                group.addButton(button)
                row_layout.addWidget(button)
            row_layout.addStretch(1)
            self.preview_layout.addWidget(row_frame)

        self.preview_frame.setVisible(True)

    def preview_selection(self) -> dict[str, str]:
        return dict(self._preview_selection)

    def _select_preview_value(self, case_part_id: str, value_id: str) -> None:
        if self._preview_selection.get(case_part_id) == value_id:
            return
        self._preview_selection[case_part_id] = value_id
        self.preview_changed.emit()

    def _clear_layout(self, layout: QtWidgets.QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _handle_tokens_dropped(self, target_state: str, tokens: list[str], _source_state: str | None) -> None:
        changed = False
        for token in tokens:
            normalized = token.strip()
            if not normalized:
                continue
            changed = self._move_token(target_state, normalized) or changed
        if changed:
            self._after_content_changed()

    def _add_entered_tokens(self) -> None:
        tokens = parse_token_text(self.add_edit.toPlainText())
        if not tokens:
            return
        changed = False
        for token in tokens:
            changed = self._move_token("on", token.strip()) or changed
        if changed:
            self.add_edit.clear()
            self._after_content_changed()

    def _remove_token(self, token: str) -> None:
        if self._remove_local_token(token):
            self._after_content_changed()

    def _remove_tokens(self, tokens: list[str]) -> None:
        removed = False
        for token in tokens:
            removed = self._remove_local_token(token) or removed
        if removed:
            self._after_content_changed()

    def _remove_local_token(self, token: str) -> bool:
        removed = False
        for values in self._local_by_state.values():
            while token in values:
                values.remove(token)
                removed = True
        return removed

    def _move_token(self, target_state: str, token: str) -> bool:
        previous = self._snapshot()
        self._remove_local_token(token)
        if self._is_base_case:
            self._local_by_state[target_state].append(token)
            return self._snapshot() != previous

        base_state = self._base_state.get(token)
        if base_state is None:
            return False
        self._local_by_state[target_state].append(token)
        return self._snapshot() != previous

    def _apply_filters(self) -> None:
        include_value = self.include_edit.text()
        exclude_value = self.exclude_edit.text()
        for lane in self._lanes.values():
            lane.apply_filter(include_value, exclude_value)
        self._update_headers()
        self._adjust_lane_heights()
        self._update_action_state()

    def _update_headers(self) -> None:
        for state_key, title, _accent in self._STATES:
            lane = self._lanes[state_key]
            total = lane.token_count()
            visible = lane.visible_count()
            suffix = f" ({visible}/{total})" if visible != total else f" ({total})"
            self._lane_headers[state_key].setText(f"{title}{suffix}")

    def _adjust_lane_heights(self) -> None:
        visible_counts = [lane.visible_count() for lane in self._lanes.values()]
        max_visible = max(visible_counts, default=0)
        display_rows = max(self._MIN_VISIBLE_ROWS, min(max_visible or self._MIN_VISIBLE_ROWS, self._MAX_VISIBLE_ROWS))
        for lane in self._lanes.values():
            row_height = lane.sizeHintForRow(0)
            if row_height <= 0:
                row_height = QtGui.QFontMetrics(lane.font()).lineSpacing() + 14
            frame_height = lane.frameWidth() * 2
            spacing = max(0, (display_rows - 1) * lane.spacing())
            padding = 8
            lane.setMinimumHeight(display_rows * row_height + frame_height + spacing + padding)
            lane.setVerticalScrollBarPolicy(
                QtCore.Qt.ScrollBarAsNeeded if lane.visible_count() > self._MAX_VISIBLE_ROWS else QtCore.Qt.ScrollBarAlwaysOff
            )

    def _after_content_changed(self) -> None:
        self._render_lanes()
        if not self._loading:
            self._push_history()
            self.changed.emit()

    def _handle_lane_selection_changed(self, active_state: str) -> None:
        if self._selection_sync:
            return
        active_lane = self._lanes[active_state]
        if active_lane.selectedItems():
            self._set_active_lane(active_state)
            self._selection_sync = True
            try:
                for state_key, lane in self._lanes.items():
                    if state_key != active_state:
                        lane.clearSelection()
            finally:
                self._selection_sync = False
        self._update_action_state()

    def _clear_all_selections(self, _state_key: str | None = None) -> None:
        self._selection_sync = True
        try:
            for lane in self._lanes.values():
                lane.clearSelection()
        finally:
            self._selection_sync = False
        self._update_action_state()

    def _delete_selected(self) -> None:
        tokens: list[str] = []
        for lane in self._lanes.values():
            tokens.extend([str(item.data(QtCore.Qt.UserRole) or item.text()) for item in lane.selectedItems()])
        unique_tokens = list(dict.fromkeys(tokens))
        if not unique_tokens:
            return
        self._remove_tokens(unique_tokens)

    def _snapshot(self) -> dict[str, list[str]]:
        return {state_key: list(values) for state_key, values in self._local_by_state.items()}

    def _restore_snapshot(self, snapshot: dict[str, list[str]]) -> None:
        self._loading = True
        try:
            self._clear_all_selections()
            self._local_by_state = {state_key: list(snapshot.get(state_key, [])) for state_key, _title, _accent in self._STATES}
            self._render_lanes()
        finally:
            self._loading = False

    def _reset_history(self) -> None:
        self._history.reset(self._snapshot())
        self._update_action_state()

    def _push_history(self) -> None:
        self._history.push(self._snapshot())
        self._update_action_state()

    def undo(self) -> None:
        snapshot = self._history.undo()
        if snapshot is None:
            return
        self._restore_snapshot(snapshot)
        self.changed.emit()
        self._update_action_state()

    def redo(self) -> None:
        snapshot = self._history.redo()
        if snapshot is None:
            return
        self._restore_snapshot(snapshot)
        self.changed.emit()
        self._update_action_state()

    def _update_action_state(self) -> None:
        selected_tokens = [
            str(item.data(QtCore.Qt.UserRole) or item.text())
            for lane in self._lanes.values()
            for item in lane.selectedItems()
        ]
        removable = any(token not in self._base_state or token in self._flatten_state(self._local_by_state) for token in selected_tokens)
        self.delete_button.setEnabled(removable)
        self.undo_button.setEnabled(self._history.can_undo)
        self.redo_button.setEnabled(self._history.can_redo)
        self.add_button.setEnabled(self._is_base_case and bool(parse_token_text(self.add_edit.toPlainText())))

    def _update_base_only_controls(self) -> None:
        self.add_edit.setVisible(self._is_base_case)
        self.add_button.setVisible(self._is_base_case)

    def _set_active_lane(self, state_key: str) -> None:
        if state_key == self._active_state:
            return
        self._active_state = state_key
        for lane_state, frame in self._lane_frames.items():
            frame.setProperty("active", lane_state == state_key)
            frame.style().unpolish(frame)
            frame.style().polish(frame)
            frame.update()

    def _activate_lane_from_container(self, state_key: str) -> None:
        self._clear_all_selections()
        self._set_active_lane(state_key)
        self._lanes[state_key].setFocus(QtCore.Qt.MouseFocusReason)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        state_key = watched.property("cb_state_key")
        if state_key and event.type() == QtCore.QEvent.MouseButtonPress:
            self._activate_lane_from_container(str(state_key))
            return True
        return super().eventFilter(watched, event)

    def _flatten_state(self, values_by_state: dict[str, list[str]]) -> dict[str, str]:
        flattened: dict[str, str] = {}
        for state_key, tokens in values_by_state.items():
            for token in tokens:
                flattened[token] = state_key
        return flattened

    def _render_lanes(self) -> None:
        local_state = self._flatten_state(self._local_by_state)
        rendered: dict[str, list[tuple[str, str]]] = {"off": [], "switch": [], "on": []}

        if self._is_base_case:
            for state_key, tokens in self._local_by_state.items():
                rendered[state_key] = [(token, "base") for token in tokens]
        else:
            for base_state, tokens in self._base_by_state.items():
                for token in tokens:
                    final_state = local_state.get(token, base_state)
                    status = "overridden" if token in local_state else "inherited"
                    rendered[final_state].append((token, status))

            for state_key, tokens in self._local_by_state.items():
                for token in tokens:
                    if token not in self._base_state:
                        rendered[state_key].append((token, "added"))

        for state_key, lane in self._lanes.items():
            lane.clear()
            current_voltage = None
            for token, status in sorted(rendered[state_key], key=lambda item: voltage_sort_key(item[0])):
                token_voltage = numeric_voltage_token(token) or "Unknown"
                if token_voltage != current_voltage:
                    lane.add_group_header(f"{token_voltage} kV" if token_voltage != "Unknown" else "Unknown voltage")
                    current_voltage = token_voltage
                lane.add_token(token, status=status)

        self._apply_filters()
