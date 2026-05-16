import json
import zipfile
from decimal import Decimal

from app.database import DonationDatabase
from app.local_importer import load_local_records, maybe_load_existing_records
from app.models import DonationRecord


def test_load_local_records_reads_raw_paginated_json(tmp_path):
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(
        json.dumps(
            [
                {
                    "result": {
                        "records": [
                            {
                                "id": "1",
                                "donateTime": "2026-05-15",
                                "donor": "张三",
                                "major": "计算机",
                                "alumniAssoc": "北京校友会",
                                "projName": "项目A",
                                "donateAmt": "10.50",
                            }
                        ]
                    }
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    records = load_local_records(raw_path)

    assert records == [
        DonationRecord("1", "2026-05-15", "张三", "计算机", "北京校友会", "项目A", Decimal("10.50"))
    ]


def test_load_local_records_reads_flat_json_records_and_preserves_parser_nulls(tmp_path):
    json_path = tmp_path / "flat.json"
    json_path.write_text(
        json.dumps(
            [
                {
                    "record_id": 2,
                    "donate_time": None,
                    "donor": " NULL ",
                    "major": "",
                    "alumni_assoc": None,
                    "project_name": "项目B",
                    "donate_amount": "",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    record = load_local_records(json_path)[0]

    assert record.record_id == "2"
    assert record.donate_time == ""
    assert record.donor == ""
    assert record.major == ""
    assert record.alumni_assoc == ""
    assert record.project_name == "项目B"
    assert record.donate_amount == Decimal("0")


def test_load_local_records_reads_csv_with_field_aliases(tmp_path):
    csv_path = tmp_path / "donations.csv"
    csv_path.write_text(
        "记录号,捐赠时间,捐赠人,院系专业,校友会,捐赠项目,捐赠金额\n"
        "3,2026-05-16,李四,数学,上海校友会,项目C,20.01\n",
        encoding="utf-8",
    )

    records = load_local_records(csv_path)

    assert records == [
        DonationRecord("3", "2026-05-16", "李四", "数学", "上海校友会", "项目C", Decimal("20.01"))
    ]


def test_load_local_records_reads_csv_with_snake_case_field_aliases(tmp_path):
    csv_path = tmp_path / "donations_snake.csv"
    csv_path.write_text(
        "record_id,donate_time,donor,major,alumni_assoc,project_name,donate_amount\n"
        "3b,2026-05-16,李四,数学,上海校友会,项目C,20.02\n",
        encoding="utf-8",
    )

    records = load_local_records(csv_path)

    assert records == [
        DonationRecord("3b", "2026-05-16", "李四", "数学", "上海校友会", "项目C", Decimal("20.02"))
    ]


def test_load_local_records_reads_xlsx_with_field_aliases(tmp_path):
    xlsx_path = tmp_path / "donations.xlsx"
    _write_minimal_xlsx(
        xlsx_path,
        [
            ["id", "donateTime", "donor", "major", "alumniAssoc", "projName", "donateAmt"],
            ["4", "2026-05-17", "王五", "物理", "广州校友会", "项目D", "30.25"],
        ],
    )

    records = load_local_records(xlsx_path)

    assert records == [
        DonationRecord("4", "2026-05-17", "王五", "物理", "广州校友会", "项目D", Decimal("30.25"))
    ]


def test_maybe_load_existing_records_prefers_raw_json_over_database(tmp_path):
    raw_path = tmp_path / "donations_raw.json"
    db_path = tmp_path / "donations.db"
    raw_path.write_text(
        json.dumps(
            [
                {
                    "record_id": "raw",
                    "donate_time": "2026-05-18",
                    "donor": "原始文件",
                    "major": "",
                    "alumni_assoc": "",
                    "project_name": "项目E",
                    "donate_amount": "40",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    db = DonationDatabase(db_path)
    db.import_records(
        [DonationRecord("db", "2026-05-19", "数据库", "", "", "项目F", Decimal("50"))]
    )

    records = maybe_load_existing_records(raw_path, db_path)

    assert [record.record_id for record in records] == ["raw"]


def test_maybe_load_existing_records_falls_back_to_database_then_empty(tmp_path):
    raw_path = tmp_path / "missing_raw.json"
    db_path = tmp_path / "donations.db"
    db = DonationDatabase(db_path)
    db.import_records(
        [DonationRecord("db", "2026-05-19", "数据库", "", "", "项目F", Decimal("50"))]
    )

    records = maybe_load_existing_records(raw_path, db_path)
    empty = maybe_load_existing_records(raw_path, tmp_path / "missing.db")

    assert records == [DonationRecord("db", "2026-05-19", "数据库", "", "", "项目F", Decimal("50"))]
    assert empty == []


def _write_minimal_xlsx(path, rows):
    def cell_name(row_index, column_index):
        letters = ""
        while column_index:
            column_index, remainder = divmod(column_index - 1, 26)
            letters = chr(65 + remainder) + letters
        return f"{letters}{row_index}"

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cells.append(
                f'<c r="{cell_name(row_index, column_index)}" t="inlineStr">'
                f"<is><t>{value}</t></is></c>"
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>""",
        )
