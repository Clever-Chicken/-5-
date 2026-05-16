from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QPropertyAnimation, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.database import DonationDatabase
from app.downloader import DEFAULT_PUBLIC_PAGE_URL, DonationDownloader
from app.local_importer import load_local_records, maybe_load_existing_records
from app.models import DonationRecord
from app.parser import load_records, parse_raw_pages
from app.table_model import DonationTableModel, RECORD_HEADERS, fit_to_contents, fit_to_view, manual_mode
from app.theme import apply_app_theme

DATA_DIR = Path("data")
RAW_DATA_PATH = DATA_DIR / "donations_raw.json"
DATABASE_PATH = DATA_DIR / "donations.db"

class DownloadWorker(QThread):
    finished_with_records = Signal(list)
    failed = Signal(str)

    def __init__(self, url: str, output_path: Path) -> None:
        super().__init__()
        self.url = url
        self.output_path = output_path

    def run(self) -> None:
        try:
            pages = DonationDownloader().download(self.url, self.output_path)
            self.finished_with_records.emit(parse_raw_pages(pages))
        except Exception as exc:  # pragma: no cover - exercised manually through the GUI.
            self.failed.emit(str(exc))


class ReportWorker(QThread):
    finished_with_report = Signal(str, list, list)
    progress_changed = Signal(int, int, str)
    failed = Signal(str)

    def __init__(self, report_name: str, database_path: Path) -> None:
        super().__init__()
        self.report_name = report_name
        self.database_path = database_path

    def run(self) -> None:
        try:
            db = DonationDatabase(self.database_path)
            if self.report_name == "top":
                rows = db.top_donors(limit=100, progress_callback=self.progress_changed.emit)
                self.finished_with_report.emit(
                    "top",
                    ["捐赠人", "累计捐赠金额", "捐赠次数"],
                    [
                        {
                            "捐赠人": row["donor"],
                            "累计捐赠金额": _format_amount(row["total_amount"]),
                            "捐赠次数": str(row["donation_count"]),
                        }
                        for row in rows
                    ],
                )
                return

            stats = db.statistics()
            largest = stats["largest_donation"]
            largest_text = ""
            if largest is not None:
                largest_text = f"{largest.donor} / {_format_amount(largest.donate_amount)} / {largest.project_name}"
            self.finished_with_report.emit(
                "stats",
                ["统计项", "值"],
                [
                    {"统计项": "捐赠记录总数", "值": str(stats["record_count"])},
                    {"统计项": "捐赠记录总金额", "值": _format_amount(stats["total_amount"])},
                    {"统计项": "最大一笔捐赠", "值": largest_text},
                    {
                        "统计项": "捐赠次数最多者",
                        "值": f"{stats['most_frequent_donor']} / {stats['most_frequent_donor_count']} 次",
                    },
                ],
            )
        except Exception as exc:  # pragma: no cover - exercised manually through the GUI.
            self.failed.emit(str(exc))


class EdgeHaloProgressBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.processed = 0
        self.total = 1
        self.stage = ""
        self._halo_offset = 0.0
        self.setMinimumHeight(50)
        self.setVisible(False)

        self._animation = QPropertyAnimation(self, b"haloOffset", self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(2400)
        self._animation.setLoopCount(-1)
        self._animation.start()

    def set_progress(self, processed: int, total: int, stage: str) -> None:
        self.processed = max(0, processed)
        self.total = max(1, total)
        self.stage = stage
        self.update()

    def text(self) -> str:
        percent = min(100, int(self.processed / self.total * 100))
        return f"{self.stage} {self.processed}/{self.total} {percent}%"

    def get_halo_offset(self) -> float:
        return self._halo_offset

    def set_halo_offset(self, value: float) -> None:
        self._halo_offset = value
        self.update()

    haloOffset = Property(float, get_halo_offset, set_halo_offset)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        outer = QRectF(8, 8, self.width() - 16, 34)
        radius = outer.height() / 2
        halo = QLinearGradient(outer.left() - outer.width() + self._halo_offset * outer.width() * 2, 0, outer.right(), 0)
        halo.setColorAt(0.00, QColor("#ff8fd6"))
        halo.setColorAt(0.25, QColor("#97c7ff"))
        halo.setColorAt(0.52, QColor("#7cf2df"))
        halo.setColorAt(0.76, QColor("#ffd36f"))
        halo.setColorAt(1.00, QColor("#ff8fd6"))

        outer_path = QPainterPath()
        outer_path.addRoundedRect(outer, radius, radius)
        painter.fillPath(outer_path, halo)

        inner = outer.adjusted(2.4, 2.4, -2.4, -2.4)
        inner_radius = inner.height() / 2
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner, inner_radius, inner_radius)
        painter.fillPath(inner_path, QColor(255, 255, 255, 218))

        fill_width = inner.width() * min(1.0, self.processed / self.total)
        if fill_width > 0:
            fill = QRectF(inner.left(), inner.top(), fill_width, inner.height())
            fill_gradient = QLinearGradient(fill.left(), 0, fill.right(), 0)
            fill_gradient.setColorAt(0, QColor(255, 255, 255, 220))
            fill_gradient.setColorAt(0.55, QColor(181, 226, 255, 218))
            fill_gradient.setColorAt(1, QColor(255, 196, 235, 218))
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill, inner_radius, inner_radius)
            painter.fillPath(fill_path, fill_gradient)

        painter.setPen(QPen(QColor(73, 88, 110), 1))
        font = QFont(self.font())
        font.setPointSize(11)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(inner, Qt.AlignCenter, self.text())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[DonationRecord] = []
        self.worker: DownloadWorker | None = None
        self.report_worker: ReportWorker | None = None
        self.setWindowTitle("厦大基金会捐赠记录工具")
        self.resize(1180, 720)

        self.url_input = QLineEdit(DEFAULT_PUBLIC_PAGE_URL)
        self.download_button = QPushButton("下载")
        self.download_button.setObjectName("primaryButton")
        self.local_import_button = QPushButton("从本地数据文件导入")
        self.local_import_button.setObjectName("secondaryButton")
        self.show_all_button = QPushButton("显示全部数据")
        self.import_button = QPushButton("入库")
        self.top_button = QPushButton("捐赠金额最多的前100名")
        self.stats_button = QPushButton("统计")
        self.fit_window_button = QPushButton("适应窗口列宽")
        self.fit_numbers_button = QPushButton("显示完整数字列宽")
        self.status_label = QLabel("准备就绪")
        self.sort_title_label = QLabel("排序方式：")
        self.sort_chip = QPushButton("")
        self.sort_chip.setObjectName("sortChip")
        self.sort_chip.setVisible(False)
        self.clear_sort_button = QPushButton("清除排序")
        self.clear_sort_button.setObjectName("linkButton")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索记录...")
        self.search_input.setObjectName("searchInput")
        self.column_settings_button = QPushButton("列设置")
        self.column_settings_button.setObjectName("secondaryButton")
        self.column_menu = QMenu(self)
        self.column_actions: dict[str, QAction] = {}
        self.total_count_label = QLabel("共 0 条记录")
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["20", "50", "100"])
        self.prev_page_button = QPushButton("‹")
        self.prev_page_button.setObjectName("paginationButton")
        self.next_page_button = QPushButton("›")
        self.next_page_button.setObjectName("paginationButton")
        self.page_info_label = QLabel("第 1 / 1 页")
        self.page_jump_input = QLineEdit()
        self.page_jump_input.setPlaceholderText("页码")
        self.page_jump_input.setFixedWidth(72)
        self.pagination_numbers_layout = QHBoxLayout()
        self.pagination_buttons: list[QPushButton] = []
        self.table_model = DonationTableModel(self)
        self.table_model.set_records([])
        self.table = QTableView()
        self.table.setModel(self.table_model)
        self.progress_bar = EdgeHaloProgressBar()

        apply_app_theme(self)
        self._build_layout()
        self._connect_signals()

    def _build_layout(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        glass_panel = QWidget()
        glass_panel.setObjectName("glassPanel")
        panel_layout = QVBoxLayout(glass_panel)

        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("下载地址"))
        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.download_button)
        url_layout.addWidget(self.local_import_button)

        self.action_layout = QHBoxLayout()
        self.action_layout.addWidget(self.show_all_button)
        self.action_layout.addWidget(self.import_button)
        self.action_layout.addWidget(self.top_button)
        self.action_layout.addWidget(self.stats_button)
        self.action_layout.addWidget(self.fit_window_button)
        self.action_layout.addWidget(self.fit_numbers_button)
        self.action_layout.addStretch(1)
        self.action_layout.addWidget(self.status_label)

        panel_layout.addLayout(url_layout)
        panel_layout.addLayout(self.action_layout)

        tools_layout = QHBoxLayout()
        tools_layout.addWidget(self.sort_title_label)
        tools_layout.addWidget(self.sort_chip)
        tools_layout.addWidget(self.clear_sort_button)
        tools_layout.addStretch(1)
        tools_layout.addWidget(self.search_input)
        tools_layout.addWidget(self.column_settings_button)

        pagination_layout = QHBoxLayout()
        pagination_layout.addWidget(self.total_count_label)
        pagination_layout.addSpacing(24)
        pagination_layout.addWidget(QLabel("每页显示："))
        pagination_layout.addWidget(self.page_size_combo)
        pagination_layout.addStretch(1)
        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addLayout(self.pagination_numbers_layout)
        pagination_layout.addWidget(self.next_page_button)
        pagination_layout.addSpacing(12)
        pagination_layout.addWidget(self.page_info_label)
        pagination_layout.addWidget(self.page_jump_input)

        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setMinimumSectionSize(28)
        self.table.horizontalHeader().setSectionsClickable(True)
        manual_mode(self.table)
        self._build_column_menu()
        self._refresh_sort_state()
        self._refresh_pagination()

        layout.addWidget(glass_panel)
        layout.addWidget(self.progress_bar)
        layout.addLayout(tools_layout)
        layout.addWidget(self.table, 1)
        layout.addLayout(pagination_layout)
        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        self.download_button.clicked.connect(self.download_records)
        self.local_import_button.clicked.connect(self.import_local_file)
        self.show_all_button.clicked.connect(self.show_all_records)
        self.import_button.clicked.connect(self.import_records)
        self.top_button.clicked.connect(self.show_top_donors)
        self.stats_button.clicked.connect(self.show_statistics)
        self.fit_window_button.clicked.connect(self.fit_columns_to_window)
        self.fit_numbers_button.clicked.connect(self.fit_numeric_columns_to_contents)
        self.table.horizontalHeader().sectionClicked.connect(self._sort_by_column)
        self.sort_chip.clicked.connect(self._clear_sort)
        self.clear_sort_button.clicked.connect(self._clear_sort)
        self.page_size_combo.currentTextChanged.connect(self._change_page_size)
        self.prev_page_button.clicked.connect(self._go_previous_page)
        self.next_page_button.clicked.connect(self._go_next_page)
        self.page_jump_input.returnPressed.connect(self._jump_to_page)

    def _build_column_menu(self) -> None:
        self.column_menu.clear()
        self.column_actions.clear()
        for header in RECORD_HEADERS:
            action = QAction(header, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(self._apply_column_visibility)
            self.column_menu.addAction(action)
            self.column_actions[header] = action
        self.column_settings_button.setMenu(self.column_menu)

    def download_records(self) -> None:
        self._set_busy(True, "正在下载公开捐赠记录...")
        self.worker = DownloadWorker(self.url_input.text(), RAW_DATA_PATH)
        self.worker.finished_with_records.connect(self._download_finished)
        self.worker.failed.connect(self._download_failed)
        self.worker.start()

    def import_records(self) -> None:
        self._ensure_records_loaded()
        if not self.records:
            self._show_message("请先下载记录")
            return
        inserted = DonationDatabase(DATABASE_PATH).import_records(self.records)
        self.status_label.setText(f"入库完成：新增 {inserted} 条，当前 {len(self.records)} 条")

    def import_local_file(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择本地捐赠数据文件",
            str(DATA_DIR),
            "数据文件 (*.json *.csv *.xlsx);;JSON 文件 (*.json);;CSV 文件 (*.csv);;Excel 文件 (*.xlsx)",
        )
        if not path:
            return
        try:
            self.records = load_local_records(path)
        except Exception as exc:
            self._show_message(str(exc))
            return
        self._show_records(self.records)
        self.status_label.setText(f"本地导入完成：{len(self.records)} 条记录")

    def show_all_records(self) -> None:
        self._ensure_records_loaded()
        if not self.records:
            self._show_message("没有可显示的数据")
            return
        self._show_records(self.records)

    def show_top_donors(self) -> None:
        self._run_report("top", "正在统计前100名...")

    def show_statistics(self) -> None:
        self._run_report("stats", "正在统计汇总数据...")

    def _download_finished(self, records: list[DonationRecord]) -> None:
        self.records = load_records(RAW_DATA_PATH)
        self._show_records(self.records)
        self._set_busy(False, f"下载完成：{len(self.records)} 条记录，已保存到 {RAW_DATA_PATH}")

    def _download_failed(self, message: str) -> None:
        self._set_busy(False, "下载失败")
        self._show_message(message)

    def _show_records(self, records: list[DonationRecord]) -> None:
        self.table_model.set_records(records)
        manual_mode(self.table)
        self.status_label.setText(f"共 {len(records)} 条记录")
        self._sync_column_actions()
        self._refresh_sort_state()
        self._refresh_pagination()

    def _show_dict_rows(self, headers: list[str], rows: list[dict[str, str]]) -> None:
        sort_columns = {"捐赠人", "累计捐赠金额", "捐赠次数"} if headers == ["捐赠人", "累计捐赠金额", "捐赠次数"] else None
        self.table_model.set_report(headers, rows, sort_columns=sort_columns)
        manual_mode(self.table)
        self._sync_column_actions()
        self._refresh_sort_state()
        self._refresh_pagination()

    def fit_columns_to_window(self) -> None:
        fit_to_view(self.table)

    def fit_numeric_columns_to_contents(self) -> None:
        fit_to_contents(self.table)

    def _ensure_records_loaded(self) -> None:
        if self.records:
            return
        try:
            self.records = maybe_load_existing_records(RAW_DATA_PATH, DATABASE_PATH)
        except Exception as exc:
            self._show_message(str(exc))

    def _set_busy(self, busy: bool, message: str) -> None:
        self.download_button.setEnabled(not busy)
        self.status_label.setText(message)

    def _show_message(self, message: str) -> None:
        QMessageBox.information(self, "提示", message)

    def _run_report(self, report_name: str, message: str) -> None:
        self.top_button.setEnabled(False)
        self.stats_button.setEnabled(False)
        self.status_label.setText(message)
        if report_name == "top":
            self.progress_bar.setVisible(True)
            self.progress_bar.set_progress(0, 1, "准备统计前100名")
        self.report_worker = ReportWorker(report_name, DATABASE_PATH)
        self.report_worker.finished_with_report.connect(self._report_finished)
        self.report_worker.progress_changed.connect(self._update_top_progress)
        self.report_worker.failed.connect(self._report_failed)
        self.report_worker.start()

    def _report_finished(self, report_name: str, headers: list[str], rows: list[dict[str, str]]) -> None:
        self._show_dict_rows(headers, rows)
        self.top_button.setEnabled(True)
        self.stats_button.setEnabled(True)
        if report_name == "top":
            self.progress_bar.set_progress(100, 100, "排序前100名")
            QTimer.singleShot(1400, self.progress_bar.hide)
            self.status_label.setText(f"显示前 {len(rows)} 名捐赠者")
        else:
            self.status_label.setText("显示统计结果")

    def _report_failed(self, message: str) -> None:
        self.top_button.setEnabled(True)
        self.stats_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("统计失败")
        self._show_message(message)

    def _update_top_progress(self, processed: int, total: int, stage: str) -> None:
        self.progress_bar.setVisible(True)
        self.progress_bar.set_progress(processed, total, stage)

    def _sort_by_column(self, section: int) -> None:
        self.table_model.sort(section)
        self._refresh_sort_state()
        self._refresh_pagination()
        self.table.horizontalHeader().viewport().update()

    def _clear_sort(self) -> None:
        self.table_model.clear_sort()
        self._refresh_sort_state()
        self._refresh_pagination()
        self.table.horizontalHeader().viewport().update()

    def _refresh_sort_state(self) -> None:
        text = self.table_model.sort_state_text()
        self.sort_chip.setText(f"{text} ×" if text else "")
        self.sort_chip.setVisible(bool(text))
        self.clear_sort_button.setEnabled(bool(text))

    def _apply_column_visibility(self) -> None:
        selected = [header for header, action in self.column_actions.items() if action.isChecked()]
        self.table_model.set_visible_headers(selected)
        self._sync_column_actions()
        self._refresh_sort_state()
        self._refresh_pagination()

    def _sync_column_actions(self) -> None:
        visible = set(self.table_model.visible_headers())
        for header, action in self.column_actions.items():
            action.blockSignals(True)
            action.setChecked(header in visible)
            action.blockSignals(False)

    def _change_page_size(self, text: str) -> None:
        self.table_model.set_page_size(int(text))
        self._refresh_pagination()

    def _go_previous_page(self) -> None:
        self.table_model.set_page(self.table_model.current_page() - 1)
        self._refresh_pagination()

    def _go_next_page(self) -> None:
        self.table_model.set_page(self.table_model.current_page() + 1)
        self._refresh_pagination()

    def _jump_to_page(self) -> None:
        text = self.page_jump_input.text().strip()
        if not text:
            return
        try:
            page = int(text)
        except ValueError:
            self.page_jump_input.clear()
            return
        self.table_model.set_page(page)
        self.page_jump_input.clear()
        self._refresh_pagination()

    def _refresh_pagination(self) -> None:
        total = self.table_model.total_row_count()
        current = self.table_model.current_page()
        page_count = self.table_model.page_count()
        self.total_count_label.setText(f"共 {total:,} 条记录")
        self.page_info_label.setText(f"第 {current} / {page_count} 页")
        self.prev_page_button.setEnabled(current > 1)
        self.next_page_button.setEnabled(current < page_count)
        self._rebuild_page_buttons(current, page_count)

    def _rebuild_page_buttons(self, current: int, page_count: int) -> None:
        while self.pagination_numbers_layout.count():
            item = self.pagination_numbers_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.pagination_buttons.clear()

        for label in _page_button_labels(current, page_count):
            button = QPushButton(label)
            button.setObjectName("paginationButton")
            button.setEnabled(label != "...")
            if label == str(current):
                button.setProperty("current", True)
            if label != "...":
                button.clicked.connect(lambda checked=False, page=int(label): self._go_to_page(page))
            self.pagination_numbers_layout.addWidget(button)
            self.pagination_buttons.append(button)

    def _go_to_page(self, page: int) -> None:
        self.table_model.set_page(page)
        self._refresh_pagination()


def _page_button_labels(current: int, page_count: int) -> list[str]:
    if page_count <= 7:
        return [str(page) for page in range(1, page_count + 1)]

    pages = {1, page_count}
    pages.update(range(max(1, current - 2), min(page_count, current + 2) + 1))
    if current <= 4:
        pages.update(range(1, 6))
    if current >= page_count - 3:
        pages.update(range(page_count - 4, page_count + 1))

    labels: list[str] = []
    previous = 0
    for page in sorted(pages):
        if previous and page - previous > 1:
            labels.append("...")
        labels.append(str(page))
        previous = page
    return labels


def _format_amount(amount: Decimal | Any) -> str:
    return f"{Decimal(str(amount)):.2f}"
