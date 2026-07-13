from __future__ import annotations

from copy import deepcopy
from typing import Generic, TypeVar


T = TypeVar("T")


class TokenHistory(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []
        self._index = -1

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return 0 <= self._index < len(self._items) - 1

    def reset(self, snapshot: T) -> None:
        self._items = [deepcopy(snapshot)]
        self._index = 0

    def push(self, snapshot: T) -> bool:
        stored_snapshot = deepcopy(snapshot)
        if self._items and stored_snapshot == self._items[self._index]:
            return False
        self._items = self._items[: self._index + 1]
        self._items.append(stored_snapshot)
        self._index = len(self._items) - 1
        return True

    def undo(self) -> T | None:
        if not self.can_undo:
            return None
        self._index -= 1
        return deepcopy(self._items[self._index])

    def redo(self) -> T | None:
        if not self.can_redo:
            return None
        self._index += 1
        return deepcopy(self._items[self._index])


def token_matches_filter(text: str, include_text: str, exclude_text: str) -> bool:
    token = text.casefold()
    include_value = include_text.strip().casefold()
    exclude_value = exclude_text.strip().casefold()
    return (not include_value or include_value in token) and (not exclude_value or exclude_value not in token)
