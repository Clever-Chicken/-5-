from __future__ import annotations

from decimal import Decimal
from itertools import islice
from math import ceil
from typing import Any, Iterable

from PySide6.QtCore import QAbstractTableModel, QCollator, QLocale, QModelIndex, Qt
from PySide6.QtWidgets import QHeaderView, QTableView

from app.models import DonationRecord

try:
    from pypinyin import lazy_pinyin
except ImportError:  # pragma: no cover - dependency is installed in the packaged build.
    lazy_pinyin = None

RECORD_HEADERS = ["记录号", "捐赠时间", "捐赠人", "院系专业", "校友会", "捐赠项目", "捐赠金额"]
REPORT_ROW_LIMIT = 100
NUMERIC_HEADERS = {"累计捐赠金额", "捐赠次数", "捐赠金额"}
MONEY_HEADERS = {"累计捐赠金额", "捐赠金额"}
TEXT_COLLATOR = QCollator(QLocale(QLocale.Language.Chinese, QLocale.Country.China))


class DonationTableModel(QAbstractTableModel):
    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self._headers: list[str] = []
        self._visible_headers: list[str] = []
        self._all_rows: list[dict[str, Any]] = []
        self._original_rows: list[dict[str, Any]] = []
        self._sort_columns: set[str] = set()
        self._sort_header: str | None = None
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._page_size = 20
        self._current_page = 1

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._page_rows())

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._visible_headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        if not 0 <= index.column() < len(self._visible_headers):
            return None
        rows = self._page_rows()
        if not 0 <= index.row() < len(rows):
            return None
        header = self._visible_headers[index.column()]
        value = rows[index.row()].get(header, "")
        if role == Qt.ItemDataRole.DisplayRole:
            return _display_value(header, value)
        if role == Qt.ItemDataRole.TextAlignmentRole and header in NUMERIC_HEADERS:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self._visible_headers):
            header = self._visible_headers[section]
            return f"{header} {self._sort_arrow(header)}"
        if orientation == Qt.Orientation.Vertical:
            return str((self._current_page - 1) * self._page_size + section + 1)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if not 0 <= column < len(self._visible_headers):
            return
        header = self._visible_headers[column]
        if header not in self._sort_columns:
            return

        if self._sort_header == header:
            self._sort_order = _opposite_order(self._sort_order)
        else:
            self._sort_header = header
            self._sort_order = Qt.SortOrder.AscendingOrder

        self.layoutAboutToBeChanged.emit()
        self._all_rows.sort(
            key=lambda row: _sort_value(header, row.get(header, "")),
            reverse=self._sort_order == Qt.SortOrder.DescendingOrder,
        )
        self._current_page = 1
        self.layoutChanged.emit()

    def set_records(self, records: Iterable[DonationRecord]) -> None:
        self.beginResetModel()
        headers = RECORD_HEADERS.copy()
        rows = [
            {
                "记录号": record.record_id,
                "捐赠时间": record.donate_time,
                "捐赠人": record.donor,
                "院系专业": record.major,
                "校友会": record.alumni_assoc,
                "捐赠项目": record.project_name,
                "捐赠金额": record.donate_amount,
            }
            for record in records
        ]
        self._replace_rows(headers, rows, set(headers))
        self.endResetModel()

    def set_report(
        self,
        headers: list[str],
        rows: Iterable[dict[str, Any]],
        sort_columns: Iterable[str | int] | None = None,
    ) -> None:
        self.beginResetModel()
        report_headers = list(headers)
        report_rows = [{header: row.get(header, "") for header in report_headers} for row in islice(rows, REPORT_ROW_LIMIT)]
        self._replace_rows(report_headers, report_rows, _normalize_sort_columns(report_headers, sort_columns))
        self.endResetModel()

    def page_count(self) -> int:
        if not self._all_rows:
            return 1
        return max(1, ceil(len(self._all_rows) / self._page_size))

    def total_row_count(self) -> int:
        return len(self._all_rows)

    def current_page(self) -> int:
        return self._current_page

    def set_page_size(self, page_size: int) -> None:
        if page_size <= 0 or page_size == self._page_size:
            return
        self.beginResetModel()
        self._page_size = page_size
        self._current_page = 1
        self.endResetModel()

    def set_page(self, page: int) -> None:
        clamped_page = min(max(1, page), self.page_count())
        if clamped_page == self._current_page:
            return
        self.beginResetModel()
        self._current_page = clamped_page
        self.endResetModel()

    def set_visible_headers(self, headers: Iterable[str]) -> None:
        visible = [header for header in headers if header in self._headers]
        if not visible:
            return
        if visible == self._visible_headers:
            return
        self.beginResetModel()
        self._visible_headers = visible
        self._current_page = min(self._current_page, self.page_count())
        self.endResetModel()

    def visible_headers(self) -> list[str]:
        return self._visible_headers.copy()

    def visible_header_at(self, column: int) -> str:
        if 0 <= column < len(self._visible_headers):
            return self._visible_headers[column]
        return ""

    def sort_state_text(self) -> str:
        if self._sort_header is None:
            return ""
        direction = "正向排序" if self._sort_order == Qt.SortOrder.AscendingOrder else "逆向排序"
        return f"{self._sort_header}：{direction}"

    def clear_sort(self) -> None:
        if self._sort_header is None:
            return
        self.layoutAboutToBeChanged.emit()
        self._all_rows = self._original_rows.copy()
        self._sort_header = None
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._current_page = 1
        self.layoutChanged.emit()

    def _replace_rows(self, headers: list[str], rows: list[dict[str, Any]], sort_columns: set[str]) -> None:
        self._headers = headers
        self._visible_headers = headers.copy()
        self._all_rows = rows
        self._original_rows = rows.copy()
        self._sort_columns = sort_columns
        self._sort_header = None
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._current_page = 1

    def _page_rows(self) -> list[dict[str, Any]]:
        start = (self._current_page - 1) * self._page_size
        return self._all_rows[start : start + self._page_size]

    def _sort_arrow(self, header: str) -> str:
        if self._sort_header != header:
            return "↕"
        if self._sort_order == Qt.SortOrder.AscendingOrder:
            return "↑"
        return "↓"


def fit_to_view(table_view: QTableView) -> None:
    model = table_view.model()
    column_count = model.columnCount() if model is not None else 0
    if column_count:
        available_width = max(table_view.viewport().width(), column_count)
        base_width = max(48, available_width // column_count)
        for column in range(column_count):
            table_view.setColumnWidth(column, base_width)
    table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)


def fit_to_contents(table_view: QTableView) -> None:
    model = table_view.model()
    column_count = model.columnCount() if model is not None else 0
    for column in range(column_count):
        if isinstance(model, DonationTableModel):
            header = model.visible_header_at(column)
        else:
            header = model.headerData(column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        if header in NUMERIC_HEADERS:
            table_view.resizeColumnToContents(column)
    table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)


def manual_mode(table_view: QTableView) -> None:
    table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)


def _display_value(header: str, value: Any) -> str:
    if header in MONEY_HEADERS:
        return f"{Decimal(str(value)):.2f}"
    return str(value)


def _sort_value(header: str, value: Any) -> Decimal | Any:
    if header in NUMERIC_HEADERS:
        return Decimal(str(value))
    displayed = _display_value(header, value)
    if lazy_pinyin is not None:
        return tuple(lazy_pinyin(displayed))
    return TEXT_COLLATOR.sortKey(displayed)


def _normalize_sort_columns(headers: list[str], sort_columns: Iterable[str | int] | None) -> set[str]:
    if sort_columns is None:
        return set()

    normalized: set[str] = set()
    for column in sort_columns:
        if isinstance(column, int) and 0 <= column < len(headers):
            normalized.add(headers[column])
        else:
            normalized.add(str(column))
    return normalized


def _opposite_order(order: Qt.SortOrder) -> Qt.SortOrder:
    if order == Qt.SortOrder.AscendingOrder:
        return Qt.SortOrder.DescendingOrder
    return Qt.SortOrder.AscendingOrder
