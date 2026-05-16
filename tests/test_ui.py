from app.database import DonationDatabase
from app.downloader import DEFAULT_PUBLIC_PAGE_URL
from app.models import DonationRecord
from app.ui import EdgeHaloProgressBar, MainWindow, RAW_DATA_PATH
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QPushButton, QTableView


def test_main_window_contains_required_controls(qt_app):
    window = MainWindow()

    assert window.url_input.text() == DEFAULT_PUBLIC_PAGE_URL
    assert window.download_button.text() == "下载"
    assert window.local_import_button.text() == "从本地数据文件导入"
    assert window.show_all_button.text() == "显示全部数据"
    assert window.import_button.text() == "入库"
    assert window.top_button.text() == "捐赠金额最多的前100名"
    assert window.stats_button.text() == "统计"
    assert window.sort_title_label.text() == "排序方式："
    assert window.sort_chip.objectName() == "sortChip"
    assert window.clear_sort_button.text() == "清除排序"
    assert window.search_input.placeholderText() == "搜索记录..."
    assert window.column_settings_button.text() == "列设置"
    assert window.total_count_label.text() == "共 0 条记录"
    assert window.page_size_combo.currentText() == "20"
    assert window.prev_page_button.text() == "‹"
    assert window.next_page_button.text() == "›"
    assert window.page_jump_input.placeholderText() == "页码"
    assert isinstance(window.table, QTableView)
    assert window.table_model.columnCount() == 7


def test_action_buttons_put_show_all_before_database_reports(qt_app):
    window = MainWindow()

    buttons = [
        window.action_layout.itemAt(index).widget().text()
        for index in range(window.action_layout.count())
        if window.action_layout.itemAt(index).widget() is not None
    ]

    assert buttons[:4] == ["显示全部数据", "入库", "捐赠金额最多的前100名", "统计"]


def test_show_records_displays_first_page_and_total_count(qt_app):
    window = MainWindow()
    records = [
        DonationRecord(str(index), "2026-05-15", "张三", "", "", "项目", Decimal("1"))
        for index in range(1005)
    ]

    window._show_records(records)

    assert window.table_model.rowCount() == 20
    assert "共 1005 条记录" in window.status_label.text()
    assert window.total_count_label.text() == "共 1,005 条记录"
    assert window.page_info_label.text() == "第 1 / 51 页"


def test_page_size_combo_switches_to_50_and_returns_first_page(qt_app):
    window = MainWindow()
    records = [
        DonationRecord(str(index), "2026-05-15", "张三", "", "", "项目", Decimal("1"))
        for index in range(1005)
    ]
    window._show_records(records)
    window.table_model.set_page(3)

    window.page_size_combo.setCurrentText("50")

    assert window.table_model.rowCount() == 50
    assert window.table_model.current_page() == 1
    assert window.page_info_label.text() == "第 1 / 21 页"


def test_page_jump_input_ignores_invalid_and_clamps_overflow(qt_app):
    window = MainWindow()
    records = [
        DonationRecord(str(index), "2026-05-15", "张三", "", "", "项目", Decimal("1"))
        for index in range(1005)
    ]
    window._show_records(records)
    window.table_model.set_page(2)
    window._refresh_pagination()

    window.page_jump_input.setText("abc")
    window._jump_to_page()
    assert window.table_model.current_page() == 2

    window.page_jump_input.setText("999")
    window._jump_to_page()
    assert window.table_model.current_page() == 51
    assert window.page_info_label.text() == "第 51 / 51 页"


def test_header_click_updates_sort_chip_and_clear_sort_resets(qt_app):
    window = MainWindow()
    records = [
        DonationRecord("1", "2026-05-15", "乙", "", "", "项目", Decimal("2")),
        DonationRecord("2", "2026-05-15", "甲", "", "", "项目", Decimal("10")),
    ]
    window._show_records(records)

    window.table.horizontalHeader().sectionClicked.emit(2)

    assert window.sort_chip.text() == "捐赠人：正向排序 ×"
    assert window.table_model.data(window.table_model.index(0, 2)) == "甲"

    window.sort_chip.click()
    assert window.sort_chip.isHidden()
    assert window.table_model.data(window.table_model.index(0, 2)) == "乙"


def test_column_settings_menu_toggles_visible_columns_and_keeps_one(qt_app):
    window = MainWindow()
    window._show_records([
        DonationRecord("1", "2026-05-15", "张三", "", "", "项目", Decimal("1"))
    ])

    donor_action = window.column_actions["捐赠人"]
    donor_action.setChecked(False)
    window._apply_column_visibility()

    assert "捐赠人" not in window.table_model.visible_headers()
    assert window.table_model.columnCount() == 6

    for header, action in window.column_actions.items():
        action.setChecked(header == "记录号")
    window._apply_column_visibility()
    window.column_actions["记录号"].setChecked(False)
    window._apply_column_visibility()

    assert window.table_model.visible_headers() == ["记录号"]
    assert window.column_actions["记录号"].isChecked()


def test_pagination_buttons_include_page_numbers_and_ellipsis(qt_app):
    window = MainWindow()
    records = [
        DonationRecord(str(index), "2026-05-15", "张三", "", "", "项目", Decimal("1"))
        for index in range(1005)
    ]

    window._show_records(records)

    button_texts = [
        button.text()
        for button in window.pagination_buttons
        if isinstance(button, QPushButton)
    ]
    assert button_texts[:5] == ["1", "2", "3", "4", "5"]
    assert "..." in button_texts
    assert "51" in button_texts


def test_download_finished_reads_records_from_saved_file(qt_app, tmp_path, monkeypatch):
    raw_path = tmp_path / "donations_raw.json"
    raw_path.write_text(
        """
        [
          {
            "result": {
              "records": [
                {
                  "id": "1",
                  "donateTime": "2026-05-15",
                  "donor": "张三",
                  "major": "",
                  "alumniAssoc": "",
                  "projName": "项目",
                  "donateAmt": "1.23"
                }
              ]
            }
          }
        ]
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.ui.RAW_DATA_PATH", raw_path)
    window = MainWindow()

    window._download_finished([])

    assert RAW_DATA_PATH.name == "donations_raw.json"
    assert window.records[0].record_id == "1"
    assert window.records[0].donate_amount == Decimal("1.23")


def test_import_records_loads_existing_raw_file_when_memory_is_empty(qt_app, tmp_path, monkeypatch):
    raw_path = tmp_path / "donations_raw.json"
    db_path = tmp_path / "donations.db"
    raw_path.write_text(
        """
        [
          {
            "result": {
              "records": [
                {
                  "id": "1",
                  "donateTime": "2026-05-15",
                  "donor": "张三",
                  "major": "",
                  "alumniAssoc": "",
                  "projName": "项目",
                  "donateAmt": "12.30"
                }
              ]
            }
          }
        ]
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.ui.RAW_DATA_PATH", raw_path)
    monkeypatch.setattr("app.ui.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.ui.QMessageBox.information", lambda *args: None)
    window = MainWindow()

    window.import_records()

    assert window.records[0].record_id == "1"
    assert DonationDatabase(db_path).count_records() == 1
    assert "入库完成" in window.status_label.text()


def test_show_all_loads_existing_raw_file_when_memory_is_empty(qt_app, tmp_path, monkeypatch):
    raw_path = tmp_path / "donations_raw.json"
    db_path = tmp_path / "donations.db"
    raw_path.write_text(
        """
        [
          {
            "result": {
              "records": [
                {
                  "id": "1",
                  "donateTime": "2026-05-15",
                  "donor": "张三",
                  "major": "",
                  "alumniAssoc": "",
                  "projName": "项目",
                  "donateAmt": "12.30"
                }
              ]
            }
          }
        ]
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("app.ui.RAW_DATA_PATH", raw_path)
    monkeypatch.setattr("app.ui.DATABASE_PATH", db_path)
    monkeypatch.setattr("app.ui.QMessageBox.information", lambda *args: None)
    window = MainWindow()

    window.show_all_records()

    assert window.table_model.rowCount() == 1
    assert window.records[0].donor == "张三"


def test_local_import_button_loads_selected_csv_file(qt_app, tmp_path, monkeypatch):
    source = tmp_path / "records.csv"
    source.write_text(
        "记录号,捐赠时间,捐赠人,院系专业,校友会,捐赠项目,捐赠金额\n"
        "1,2026-05-15,张三,,,项目,9.99\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("app.ui.QFileDialog.getOpenFileName", lambda *args: (str(source), ""))
    window = MainWindow()

    window.import_local_file()

    assert window.records[0].record_id == "1"
    assert window.table_model.rowCount() == 1
    assert "本地导入完成" in window.status_label.text()


def test_column_width_buttons_switch_resize_modes(qt_app):
    window = MainWindow()

    window.fit_columns_to_window()
    assert window.table.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert window.table.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    window.fit_numeric_columns_to_contents()
    assert window.table.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert window.table.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


def test_top_report_headers_are_click_sortable(qt_app):
    window = MainWindow()
    rows = [
        {"捐赠人": "B", "累计捐赠金额": "2.00", "捐赠次数": "10"},
        {"捐赠人": "A", "累计捐赠金额": "10.00", "捐赠次数": "2"},
    ]

    window._report_finished("top", ["捐赠人", "累计捐赠金额", "捐赠次数"], rows)
    assert window.table.horizontalHeader().sectionsClickable()

    window.table.horizontalHeader().sectionClicked.emit(0)
    assert window.table_model.data(window.table_model.index(0, 0)) == "A"

    window.table.horizontalHeader().sectionClicked.emit(1)
    assert window.table_model.data(window.table_model.index(0, 1)) == "2.00"

    window.table.horizontalHeader().sectionClicked.emit(1)
    assert window.table_model.data(window.table_model.index(0, 1)) == "10.00"


def test_edge_halo_progress_bar_formats_processed_total_and_percent(qt_app):
    progress = EdgeHaloProgressBar()

    progress.set_progress(37, 250, "正在合并捐赠者名称")

    assert progress.processed == 37
    assert progress.total == 250
    assert progress.stage == "正在合并捐赠者名称"
    assert "37/250" in progress.text()
    assert "14%" in progress.text()


def test_top_progress_updates_progress_bar_text(qt_app):
    window = MainWindow()

    window._update_top_progress(37, 250, "正在合并捐赠者名称")

    assert not window.progress_bar.isHidden()
    assert "37/250" in window.progress_bar.text()
    assert "正在合并捐赠者名称" in window.progress_bar.text()


def test_run_top_report_shows_progress_and_disables_report_buttons(qt_app):
    window = MainWindow()

    window._run_report("top", "正在统计前100名...")

    try:
        assert not window.progress_bar.isHidden()
        assert not window.top_button.isEnabled()
        assert not window.stats_button.isEnabled()
        assert "准备统计前100名" in window.progress_bar.text()
    finally:
        window.report_worker.quit()
        window.report_worker.wait()
