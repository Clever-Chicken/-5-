import json

import pytest

from app.downloader import DEFAULT_PUBLIC_PAGE_URL, DonationDownloader, resolve_api_url


def test_resolve_api_url_maps_public_page_to_api_endpoint():
    assert resolve_api_url(DEFAULT_PUBLIC_PAGE_URL).endswith(
        "/alumni/donate/xmuDonatePublic/listForWeb"
    )


def test_resolve_api_url_keeps_api_url():
    api_url = "https://edfjzxt.xmu.edu.cn/alumni/donate/xmuDonatePublic/listForWeb"

    assert resolve_api_url(api_url) == api_url


def test_downloader_fetches_all_pages_and_saves_raw_json(tmp_path):
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        page_no = params["pageNo"]
        return {
            "success": True,
            "result": {
                "pages": 2,
                "records": [
                    {
                        "id": str(page_no),
                        "donateTime": "2026-05-15",
                        "donor": "张三",
                        "major": "",
                        "alumniAssoc": "",
                        "projName": "项目",
                        "donateAmt": page_no,
                    }
                ],
            },
        }

    output_path = tmp_path / "raw.json"
    downloader = DonationDownloader(http_get=fake_get, page_size=5000)

    pages = downloader.download(DEFAULT_PUBLIC_PAGE_URL, output_path)

    assert [call[1]["pageNo"] for call in calls] == [1, 2]
    assert calls[0][1]["pageSize"] == 5000
    assert pages[0]["result"]["records"][0]["id"] == "1"
    assert json.loads(output_path.read_text(encoding="utf-8")) == pages


def test_downloader_rejects_failed_api_response(tmp_path):
    def fake_get(url, params, timeout):
        return {"success": False, "message": "接口失败", "result": None}

    downloader = DonationDownloader(http_get=fake_get)

    with pytest.raises(ValueError, match="接口失败"):
        downloader.download(DEFAULT_PUBLIC_PAGE_URL, tmp_path / "raw.json")


def test_downloader_rejects_missing_records_shape(tmp_path):
    def fake_get(url, params, timeout):
        return {"success": True, "result": {"pages": 1}}

    downloader = DonationDownloader(http_get=fake_get)

    with pytest.raises(ValueError, match="records"):
        downloader.download(DEFAULT_PUBLIC_PAGE_URL, tmp_path / "raw.json")
