from decimal import Decimal

from app.parser import parse_raw_pages


def test_parse_raw_pages_extracts_public_donation_fields():
    raw_pages = [
        {
            "success": True,
            "result": {
                "records": [
                    {
                        "id": "2055083205920301058",
                        "donateTime": "2026-05-15",
                        "donor": "郑毅芳",
                        "major": "",
                        "alumniAssoc": "",
                        "projName": "台湾研究院教育研究发展基金",
                        "donateAmt": 1000.0,
                    },
                    {
                        "id": "2053839989493473281",
                        "donateTime": "2026-05-11",
                        "donor": "李致远",
                        "major": "宪法学与行政法学",
                        "alumniAssoc": "福州校友会",
                        "projName": "台湾研究院教育研究发展基金",
                        "donateAmt": "16.88",
                    },
                ]
            },
        }
    ]

    records = parse_raw_pages(raw_pages)

    assert len(records) == 2
    assert records[0].record_id == "2055083205920301058"
    assert records[0].donate_time == "2026-05-15"
    assert records[0].donor == "郑毅芳"
    assert records[0].major == ""
    assert records[0].alumni_assoc == ""
    assert records[0].project_name == "台湾研究院教育研究发展基金"
    assert records[0].donate_amount == Decimal("1000.0")
    assert records[1].donate_amount == Decimal("16.88")


def test_parse_raw_pages_converts_null_and_null_string_to_empty_text():
    raw_pages = [
        {
            "result": {
                "records": [
                    {
                        "id": "1",
                        "donateTime": None,
                        "donor": None,
                        "major": "NULL",
                        "alumniAssoc": None,
                        "projName": None,
                        "donateAmt": None,
                    }
                ]
            }
        }
    ]

    record = parse_raw_pages(raw_pages)[0]

    assert record.donate_time == ""
    assert record.donor == ""
    assert record.major == ""
    assert record.alumni_assoc == ""
    assert record.project_name == ""
    assert record.donate_amount == Decimal("0")
