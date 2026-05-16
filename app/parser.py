from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.models import DonationRecord


def load_records(path: str | Path) -> list[DonationRecord]:
    with Path(path).open("r", encoding="utf-8") as file:
        raw_pages = json.load(file)
    return parse_raw_pages(raw_pages)


def parse_raw_pages(raw_pages: list[dict[str, Any]]) -> list[DonationRecord]:
    records: list[DonationRecord] = []
    for page in raw_pages:
        for item in page.get("result", {}).get("records", []):
            records.append(
                DonationRecord(
                    record_id=_clean_text(item.get("id")),
                    donate_time=_clean_text(item.get("donateTime")),
                    donor=_clean_text(item.get("donor")),
                    major=_clean_text(item.get("major")),
                    alumni_assoc=_clean_text(item.get("alumniAssoc")),
                    project_name=_clean_text(item.get("projName")),
                    donate_amount=_parse_amount(item.get("donateAmt")),
                )
            )
    return records


def record_from_mapping(item: dict[str, Any]) -> DonationRecord:
    return DonationRecord(
        record_id=_clean_text(item.get("record_id")),
        donate_time=_clean_text(item.get("donate_time")),
        donor=_clean_text(item.get("donor")),
        major=_clean_text(item.get("major")),
        alumni_assoc=_clean_text(item.get("alumni_assoc")),
        project_name=_clean_text(item.get("project_name")),
        donate_amount=_parse_amount(item.get("donate_amount")),
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.upper() == "NULL" else text


def _parse_amount(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))
