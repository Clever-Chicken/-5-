from decimal import Decimal
from unittest.mock import patch

from app.database import DonationDatabase
from app.models import DonationRecord


def test_database_import_is_duplicate_safe_and_counts_records(tmp_path):
    db = DonationDatabase(tmp_path / "donations.db")
    records = [
        DonationRecord("1", "2026-05-15", "张三", "", "", "项目A", Decimal("10")),
        DonationRecord("1", "2026-05-15", "张三", "", "", "项目A", Decimal("10")),
        DonationRecord("2", "2026-05-16", "李四", "计算机", "北京校友会", "项目B", Decimal("20.5")),
    ]

    inserted = db.import_records(records)
    db.import_records(records)

    assert inserted == 2
    assert db.count_records() == 2
    records_by_id = {record.record_id: record for record in db.fetch_all_records()}
    assert records_by_id["2"].major == "计算机"


def test_top_donors_merges_related_names_and_sums_amounts(tmp_path):
    db = DonationDatabase(tmp_path / "donations.db")
    db.import_records(
        [
            DonationRecord("1", "2026-05-15", "李氏基金", "", "", "项目A", Decimal("100")),
            DonationRecord("2", "2026-05-16", "新加坡李氏基金", "", "", "项目B", Decimal("50")),
            DonationRecord("3", "2026-05-17", "王氏基金", "", "", "项目C", Decimal("120")),
        ]
    )

    top = db.top_donors(limit=2)

    assert top[0]["donor"] == "新加坡李氏基金"
    assert top[0]["total_amount"] == Decimal("150.0")
    assert top[0]["donation_count"] == 2
    assert top[1]["donor"] == "王氏基金"


def test_top_donors_aggregates_exact_names_before_fuzzy_grouping(tmp_path):
    db = DonationDatabase(tmp_path / "donations.db")
    db.import_records(
        [
            DonationRecord("1", "2026-05-15", "李氏基金", "", "", "项目A", Decimal("1")),
            DonationRecord("2", "2026-05-16", "李氏基金", "", "", "项目B", Decimal("2")),
            DonationRecord("3", "2026-05-17", "新加坡李氏基金", "", "", "项目C", Decimal("3")),
        ]
    )

    exact_rows = db.fetch_donor_totals()
    top = db.top_donors(limit=1)

    assert len(exact_rows) == 2
    assert top == [
        {"donor": "新加坡李氏基金", "total_amount": Decimal("6.0"), "donation_count": 3}
    ]


def test_top_donors_reports_progress_with_processed_and_total(tmp_path):
    db = DonationDatabase(tmp_path / "donations.db")
    db.import_records(
        [
            DonationRecord("1", "2026-05-15", "李氏基金", "", "", "项目A", Decimal("1")),
            DonationRecord("2", "2026-05-16", "新加坡李氏基金", "", "", "项目B", Decimal("2")),
            DonationRecord("3", "2026-05-17", "王氏基金", "", "", "项目C", Decimal("3")),
        ]
    )
    events = []

    db.top_donors(progress_callback=lambda processed, total, stage: events.append((processed, total, stage)))

    assert events
    assert all(processed <= total for processed, total, _stage in events)
    assert events[-1][0] == events[-1][1]
    assert events[-1][2] == "排序前100名"


def test_statistics_returns_total_amount_largest_and_most_frequent_donor(tmp_path):
    db = DonationDatabase(tmp_path / "donations.db")
    db.import_records(
        [
            DonationRecord("1", "2026-05-15", "张三", "", "", "项目A", Decimal("10")),
            DonationRecord("2", "2026-05-16", "张三", "", "", "项目B", Decimal("20")),
            DonationRecord("3", "2026-05-17", "李四", "", "", "项目C", Decimal("200")),
        ]
    )

    stats = db.statistics()

    assert stats["record_count"] == 3
    assert stats["total_amount"] == Decimal("230.0")
    assert stats["largest_donation"].record_id == "3"
    assert stats["most_frequent_donor"] == "张三"
    assert stats["most_frequent_donor_count"] == 2


def test_database_preserves_cent_precision_for_money(tmp_path):
    db = DonationDatabase(tmp_path / "donations.db")
    db.import_records(
        [
            DonationRecord("1", "2026-05-15", "张三", "", "", "项目A", Decimal("123456789012345.67")),
            DonationRecord("2", "2026-05-16", "李四", "", "", "项目B", Decimal("0.01")),
        ]
    )

    stats = db.statistics()

    with db._connect() as connection:
        stored = connection.execute(
            "SELECT donate_amount, typeof(donate_amount) FROM donation_records WHERE record_id = '1'"
        ).fetchone()

    assert stored == ("123456789012345.67", "text")
    assert db.fetch_all_records()[1].donate_amount == Decimal("123456789012345.67")
    assert stats["total_amount"] == Decimal("123456789012345.68")


def test_top_donors_uses_heap_selection_instead_of_full_sort(tmp_path):
    db = DonationDatabase(tmp_path / "donations.db")
    db.import_records(
        [
            DonationRecord(str(index), "2026-05-15", f"捐赠者{index}", "", "", "项目", Decimal(index))
            for index in range(120)
        ]
    )

    with patch("app.database.nlargest", wraps=__import__("heapq").nlargest) as nlargest:
        top = db.top_donors(limit=10)

    assert nlargest.called
    assert len(top) == 10
    assert top[0]["donor"] == "捐赠者119"


def test_statistics_scans_minimal_columns_without_fetching_all_records(tmp_path):
    db = DonationDatabase(tmp_path / "donations.db")
    db.import_records(
        [
            DonationRecord("1", "2026-05-15", "张三", "", "", "项目A", Decimal("10")),
            DonationRecord("2", "2026-05-16", "张三", "", "", "项目B", Decimal("20")),
            DonationRecord("3", "2026-05-17", "李四", "", "", "项目C", Decimal("200")),
        ]
    )

    with patch.object(db, "fetch_all_records", side_effect=AssertionError("full fetch used")):
        stats = db.statistics()

    assert stats["record_count"] == 3
    assert stats["total_amount"] == Decimal("230")
    assert stats["largest_donation"].record_id == "3"
