"""Qt results table model for MVP UI (lazy Qt binding)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Any


def build_results_model(QtCore: Any, QtGui: Any) -> Tuple[type, type]:
    """Create ResultRow and ResultsTableModel bound to provided QtCore/QtGui."""

    @dataclass
    class ResultRow:
        status: str
        action: str
        input_path: str
        name: str
        detected_system: str
        security: str
        signals: str
        candidates: str
        planned_target: str
        normalization: str
        reason: str
        meta_index: int
        status_tooltip: str = ""
        status_color: Optional[str] = None

    class ResultsTableModel(QtCore.QAbstractTableModel):
        headers = [
            "Status/Fehler",
            "Aktion",
            "Eingabepfad",
            "Name",
            "Erkannte Konsole/Typ",
            "Sicherheit",
            "Signale",
            "Kandidaten",
            "Geplantes Ziel",
            "Normalisierung",
            "Grund",
        ]

        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self._rows: List[ResultRow] = []

        def rowCount(self, parent=QtCore.QModelIndex()) -> int:
            if parent.isValid():
                return 0
            return len(self._rows)

        def columnCount(self, parent=QtCore.QModelIndex()) -> int:
            if parent.isValid():
                return 0
            return len(self.headers)

        def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
            if not index.isValid():
                return None
            row = self._rows[index.row()]
            column = index.column()
            values = [
                row.status,
                row.action,
                row.input_path,
                row.name,
                row.detected_system,
                row.security,
                row.signals,
                row.candidates,
                row.planned_target,
                row.normalization,
                row.reason,
            ]
            if role in (QtCore.Qt.ItemDataRole.DisplayRole, QtCore.Qt.ItemDataRole.EditRole):
                try:
                    return values[column]
                except Exception:
                    return ""
            if role == QtCore.Qt.ItemDataRole.ToolTipRole and column == 0:
                return row.status_tooltip or None
            if role == QtCore.Qt.ItemDataRole.ForegroundRole and column == 0 and row.status_color:
                try:
                    return QtGui.QBrush(QtGui.QColor(row.status_color))
                except Exception:
                    return None
            if role == QtCore.Qt.ItemDataRole.UserRole:
                return row.meta_index
            return None

        def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
            if orientation == QtCore.Qt.Orientation.Horizontal and role == QtCore.Qt.ItemDataRole.DisplayRole:
                if 0 <= section < len(self.headers):
                    return self.headers[section]
            return None

        def flags(self, index):
            if not index.isValid():
                return QtCore.Qt.ItemFlag.NoItemFlags
            return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable

        def set_rows(self, rows: List[ResultRow]) -> None:
            self.beginResetModel()
            self._rows = list(rows)
            self.endResetModel()

        def clear(self) -> None:
            self.set_rows([])

        def append_row(self, row: ResultRow) -> None:
            position = len(self._rows)
            self.beginInsertRows(QtCore.QModelIndex(), position, position)
            self._rows.append(row)
            self.endInsertRows()

        def update_status(
            self,
            row_index: int,
            status: str,
            tooltip: Optional[str] = None,
            color: Optional[str] = None,
        ) -> None:
            if row_index < 0 or row_index >= len(self._rows):
                return
            row = self._rows[row_index]
            row.status = str(status)
            if tooltip is not None:
                row.status_tooltip = tooltip
            if color is not None:
                row.status_color = color
            top_left = self.index(row_index, 0)
            self.dataChanged.emit(
                top_left,
                top_left,
                [
                    QtCore.Qt.ItemDataRole.DisplayRole,
                    QtCore.Qt.ItemDataRole.ToolTipRole,
                    QtCore.Qt.ItemDataRole.ForegroundRole,
                ],
            )

        def get_row(self, row_index: int) -> Optional[ResultRow]:
            if 0 <= row_index < len(self._rows):
                return self._rows[row_index]
            return None

    return ResultRow, ResultsTableModel
