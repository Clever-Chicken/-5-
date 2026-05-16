from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableView

from app.models import DonationRecord
from app.table_model import DonationTableModel, fit_to_contents, fit_to_view, manual_mode


def displayed(model: DonationTableModel, row: int, column: int) -> str:
    return model.data(model.index(row, column), Qt.ItemDataRole.DisplayRole)


def make_record(record_id: int, amount: str) -> DonationRecord:
    return DonationRecord(
        str(record_id),
        "2026-05-15",
        f"捐赠人{record_id}",
        "",
        "",
        "项目",
        Decimal(amount),
    )


def test_set_records_displays_every_record_without_1000_row_limit(qt_app):
    model = DonationTableModel()
    records = [make_record(index, "1") for index in range(1005)]

    model.set_records(records)

    assert model.total_row_count() == 1005
    assert model.rowCount() == 20
    assert model.columnCount() == 7
    assert displayed(model, 19, 0) == "19"


def test_records_sort_donation_amount_by_decimal_value(qt_app):
    model = DonationTableModel()
    model.set_records([make_record(1, "10"), make_record(2, "2"), make_record(3, "1")])

    model.sort(6)
    assert [displayed(model, row, 6) for row in range(model.rowCount())] == ["1.00", "2.00", "10.00"]

    model.sort(6)
    assert [displayed(model, row, 6) for row in range(model.rowCount())] == ["10.00", "2.00", "1.00"]


def test_set_report_shows_first_100_rows_only(qt_app):
    model = DonationTableModel()
    rows = [{"序号": str(index), "值": f"项目{index}"} for index in range(120)]

    model.set_report(["序号", "值"], rows)

    assert model.total_row_count() == 100
    assert model.rowCount() == 20
    assert model.columnCount() == 2
    assert displayed(model, 19, 0) == "19"


def test_report_sorting_only_applies_to_configured_columns_and_toggles_order(qt_app):
    model = DonationTableModel()
    headers = ["捐赠人", "累计捐赠金额", "捐赠次数"]
    rows = [
        {"捐赠人": "乙", "累计捐赠金额": "2.00", "捐赠次数": 10},
        {"捐赠人": "甲", "累计捐赠金额": "10.00", "捐赠次数": 2},
        {"捐赠人": "丙", "累计捐赠金额": "1.00", "捐赠次数": 30},
    ]
    model.set_report(headers, rows, sort_columns={"累计捐赠金额", "捐赠次数"})

    model.sort(0)
    assert [displayed(model, row, 0) for row in range(model.rowCount())] == ["乙", "甲", "丙"]

    model.sort(1)
    assert [displayed(model, row, 1) for row in range(model.rowCount())] == ["1.00", "2.00", "10.00"]

    model.sort(1)
    assert [displayed(model, row, 1) for row in range(model.rowCount())] == ["10.00", "2.00", "1.00"]

    model.sort(2)
    assert [displayed(model, row, 2) for row in range(model.rowCount())] == ["2", "10", "30"]


def test_report_text_columns_sort_with_chinese_collation_when_allowed(qt_app):
    model = DonationTableModel()
    model.set_report(
        ["捐赠人", "累计捐赠金额"],
        [
            {"捐赠人": "乙", "累计捐赠金额": Decimal("2")},
            {"捐赠人": "甲", "累计捐赠金额": Decimal("10")},
            {"捐赠人": "丙", "累计捐赠金额": Decimal("1")},
        ],
        sort_columns={"捐赠人", "累计捐赠金额"},
    )

    model.sort(0)

    assert [displayed(model, row, 0) for row in range(model.rowCount())] == ["丙", "甲", "乙"]


def test_column_width_helpers_set_expected_resize_modes(qt_app):
    model = DonationTableModel()
    model.set_records([make_record(1, "1")])
    table = QTableView()
    table.setModel(model)

    fit_to_view(table)
    assert table.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert table.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    fit_to_contents(table)
    assert table.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert table.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded

    manual_mode(table)
    assert table.horizontalHeader().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive


def test_fit_to_contents_resizes_only_numeric_columns(qt_app):
    model = DonationTableModel()
    model.set_report(
        ["捐赠人", "累计捐赠金额", "捐赠次数"],
        [{"捐赠人": "很长的捐赠者名称", "累计捐赠金额": "123456789.12", "捐赠次数": "99"}],
        sort_columns={"捐赠人", "累计捐赠金额", "捐赠次数"},
    )
    table = QTableView()
    table.setModel(model)
    table.setColumnWidth(0, 33)
    table.setColumnWidth(1, 33)
    table.setColumnWidth(2, 33)

    fit_to_contents(table)

    assert table.columnWidth(0) == 33
    assert table.columnWidth(1) > 33
    assert table.columnWidth(2) > 33


def test_pagination_defaults_and_page_boundaries(qt_app):
    model = DonationTableModel()
    model.set_records([make_record(index, "1") for index in range(45)])

    assert model.total_row_count() == 45
    assert model.page_count() == 3
    assert model.current_page() == 1
    assert model.rowCount() == 20
    assert displayed(model, 0, 0) == "0"
    assert displayed(model, 19, 0) == "19"

    model.set_page(2)
    assert model.current_page() == 2
    assert model.rowCount() == 20
    assert displayed(model, 0, 0) == "20"

    model.set_page(99)
    assert model.current_page() == 3
    assert model.rowCount() == 5
    assert displayed(model, 0, 0) == "40"

    model.set_page(0)
    assert model.current_page() == 1
    assert displayed(model, 0, 0) == "0"


def test_vertical_headers_show_absolute_row_numbers_across_pages(qt_app):
    model = DonationTableModel()
    model.set_records([make_record(index, "1") for index in range(45)])

    assert model.headerData(0, Qt.Orientation.Vertical) == "1"
    assert model.headerData(19, Qt.Orientation.Vertical) == "20"

    model.set_page(2)

    assert model.headerData(0, Qt.Orientation.Vertical) == "21"
    assert model.headerData(19, Qt.Orientation.Vertical) == "40"

    model.set_page(3)

    assert model.headerData(0, Qt.Orientation.Vertical) == "41"
    assert model.headerData(4, Qt.Orientation.Vertical) == "45"


def test_page_size_change_resets_to_first_page(qt_app):
    model = DonationTableModel()
    model.set_records([make_record(index, "1") for index in range(45)])
    model.set_page(3)

    model.set_page_size(50)

    assert model.current_page() == 1
    assert model.page_count() == 1
    assert model.rowCount() == 45


def test_sorting_applies_to_all_rows_before_paging_and_clear_restores_original_order(qt_app):
    model = DonationTableModel()
    records = [make_record(index, str(amount)) for index, amount in enumerate(range(25, 0, -1))]
    model.set_records(records)
    model.set_page(2)

    model.sort(6)

    assert model.current_page() == 1
    assert model.sort_state_text() == "捐赠金额：正向排序"
    assert [displayed(model, row, 6) for row in range(3)] == ["1.00", "2.00", "3.00"]
    model.set_page(2)
    assert [displayed(model, row, 6) for row in range(model.rowCount())] == [
        "21.00",
        "22.00",
        "23.00",
        "24.00",
        "25.00",
    ]

    model.sort(6)

    assert model.current_page() == 1
    assert model.sort_state_text() == "捐赠金额：逆向排序"
    assert [displayed(model, row, 6) for row in range(3)] == ["25.00", "24.00", "23.00"]

    model.clear_sort()

    assert model.current_page() == 1
    assert model.sort_state_text() == ""
    assert [displayed(model, row, 6) for row in range(3)] == ["25.00", "24.00", "23.00"]


def test_horizontal_headers_include_sort_arrows(qt_app):
    model = DonationTableModel()
    model.set_records([make_record(1, "1"), make_record(2, "2")])

    assert model.headerData(0, Qt.Orientation.Horizontal) == "记录号 ↕"
    assert model.headerData(6, Qt.Orientation.Horizontal) == "捐赠金额 ↕"

    model.sort(6)
    assert model.headerData(6, Qt.Orientation.Horizontal) == "捐赠金额 ↑"
    assert model.headerData(0, Qt.Orientation.Horizontal) == "记录号 ↕"

    model.sort(6)
    assert model.headerData(6, Qt.Orientation.Horizontal) == "捐赠金额 ↓"


def test_visible_headers_filter_columns_and_keep_at_least_one(qt_app):
    model = DonationTableModel()
    model.set_records([make_record(1, "9")])

    model.set_visible_headers(["捐赠人", "捐赠金额"])

    assert model.visible_headers() == ["捐赠人", "捐赠金额"]
    assert model.columnCount() == 2
    assert displayed(model, 0, 0) == "捐赠人1"
    assert displayed(model, 0, 1) == "9.00"

    model.set_visible_headers([])

    assert model.visible_headers() == ["捐赠人", "捐赠金额"]


def test_set_records_resets_pagination_sorting_and_visible_columns(qt_app):
    model = DonationTableModel()
    model.set_records([make_record(index, str(index)) for index in range(30)])
    model.set_visible_headers(["捐赠人"])
    model.set_page(2)
    model.sort(0)

    model.set_records([make_record(99, "1")])

    assert model.current_page() == 1
    assert model.sort_state_text() == ""
    assert model.visible_headers() == [
        "记录号",
        "捐赠时间",
        "捐赠人",
        "院系专业",
        "校友会",
        "捐赠项目",
        "捐赠金额",
    ]
