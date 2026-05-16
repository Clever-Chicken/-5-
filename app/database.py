from __future__ import annotations

import sqlite3
from decimal import Decimal
from heapq import nlargest
from pathlib import Path
from typing import Any, Callable

from app.models import DonationRecord
from app.name_match import group_donor_names

ProgressCallback = Callable[[int, int, str], None]


class DonationDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.create_schema()

    def create_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS donation_records (
                    record_id TEXT PRIMARY KEY,
                    donate_time TEXT NOT NULL,
                    donor TEXT NOT NULL,
                    major TEXT NOT NULL,
                    alumni_assoc TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    donate_amount TEXT NOT NULL
                )
                """
            )

    def import_records(self, records: list[DonationRecord]) -> int:
        before = self.count_records()
        rows = [
            (
                record.record_id,
                record.donate_time,
                record.donor,
                record.major,
                record.alumni_assoc,
                record.project_name,
                str(record.donate_amount),
            )
            for record in records
        ]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO donation_records (
                    record_id,
                    donate_time,
                    donor,
                    major,
                    alumni_assoc,
                    project_name,
                    donate_amount
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(record_id) DO UPDATE SET
                    donate_time = excluded.donate_time,
                    donor = excluded.donor,
                    major = excluded.major,
                    alumni_assoc = excluded.alumni_assoc,
                    project_name = excluded.project_name,
                    donate_amount = excluded.donate_amount
                """,
                rows,
            )
        return self.count_records() - before

    def count_records(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) FROM donation_records").fetchone()
        return int(row[0])

    def fetch_all_records(self) -> list[DonationRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT record_id, donate_time, donor, major, alumni_assoc, project_name, donate_amount
                FROM donation_records
                ORDER BY donate_time DESC, record_id DESC
                """
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def top_donors(
        self,
        limit: int = 100,
        progress_callback: ProgressCallback | None = None,
    ) -> list[dict[str, Any]]:
        _report_progress(progress_callback, 0, 1, "读取捐赠者聚合数据")
        exact_totals = self.fetch_donor_totals()
        total_names = max(len(exact_totals), 1)
        _report_progress(progress_callback, min(len(exact_totals), total_names), total_names, "读取捐赠者聚合数据")
        donor_names = [row["donor"] for row in exact_totals if row["donor"]]
        _report_progress(progress_callback, 0, max(len(donor_names), 1), "合并捐赠者名称")
        groups = group_donor_names(donor_names)
        _report_progress(progress_callback, len(donor_names), max(len(donor_names), 1), "合并捐赠者名称")
        totals: dict[str, dict[str, Any]] = {}

        for index, row in enumerate(exact_totals, start=1):
            donor = groups.get(row["donor"], row["donor"])
            if not donor:
                continue
            if donor not in totals:
                totals[donor] = {
                    "donor": donor,
                    "total_amount": Decimal("0"),
                    "donation_count": 0,
                }
            totals[donor]["total_amount"] += row["total_amount"]
            totals[donor]["donation_count"] += row["donation_count"]
            _report_progress(progress_callback, index, total_names, "累计捐赠金额")

        ranked = nlargest(
            limit,
            totals.values(),
            key=lambda item: (item["total_amount"], item["donation_count"], item["donor"]),
        )
        _report_progress(progress_callback, len(ranked), max(len(ranked), 1), "排序前100名")
        return ranked

    def fetch_donor_totals(self) -> list[dict[str, Any]]:
        totals: dict[str, dict[str, Any]] = {}
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT donor, donate_amount
                FROM donation_records
                WHERE donor != ''
                """
            )
            for donor, amount in cursor:
                donor_name = str(donor)
                if donor_name not in totals:
                    totals[donor_name] = {
                        "donor": donor_name,
                        "total_amount": Decimal("0"),
                        "donation_count": 0,
                    }
                totals[donor_name]["total_amount"] += Decimal(str(amount))
                totals[donor_name]["donation_count"] += 1
        return list(totals.values())

    def statistics(self) -> dict[str, Any]:
        record_count = 0
        total_amount = Decimal("0")
        largest_donation = None
        donor_counts: dict[str, int] = {}
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT record_id, donate_time, donor, major, alumni_assoc, project_name, donate_amount
                FROM donation_records
                """
            )
            for row in cursor:
                record = _record_from_row(row)
                record_count += 1
                total_amount += record.donate_amount
                if largest_donation is None or record.donate_amount > largest_donation.donate_amount:
                    largest_donation = record
                if record.donor:
                    donor_counts[record.donor] = donor_counts.get(record.donor, 0) + 1
        most_frequent_donor = ""
        most_frequent_donor_count = 0
        if donor_counts:
            most_frequent_donor, most_frequent_donor_count = max(
                donor_counts.items(), key=lambda item: (item[1], item[0])
            )
        return {
            "record_count": record_count,
            "total_amount": total_amount,
            "largest_donation": largest_donation,
            "most_frequent_donor": most_frequent_donor,
            "most_frequent_donor_count": most_frequent_donor_count,
        }

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)


def _record_from_row(row: tuple[Any, ...]) -> DonationRecord:
    return DonationRecord(
        record_id=str(row[0]),
        donate_time=str(row[1]),
        donor=str(row[2]),
        major=str(row[3]),
        alumni_assoc=str(row[4]),
        project_name=str(row[5]),
        donate_amount=Decimal(str(row[6])),
    )


def _report_progress(
    progress_callback: ProgressCallback | None,
    processed: int,
    total: int,
    stage: str,
) -> None:
    if progress_callback is None:
        return
    progress_callback(processed, max(total, 1), stage)
