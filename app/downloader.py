from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import requests

DEFAULT_PUBLIC_PAGE_URL = "https://edfjzxt.xmu.edu.cn/website/page/Information/xxgk.html"
DEFAULT_API_URL = "https://edfjzxt.xmu.edu.cn/alumni/donate/xmuDonatePublic/listForWeb"

HttpGet = Callable[[str, dict[str, int], int], dict[str, Any]]


def resolve_api_url(url: str) -> str:
    cleaned = url.strip()
    if "xmuDonatePublic/listForWeb" in cleaned:
        return cleaned
    return DEFAULT_API_URL


class DonationDownloader:
    def __init__(
        self,
        http_get: HttpGet | None = None,
        page_size: int = 5000,
        timeout: int = 30,
    ) -> None:
        self.http_get = http_get or _requests_get_json
        self.page_size = page_size
        self.timeout = timeout

    def download(self, url: str, output_path: str | Path) -> list[dict[str, Any]]:
        api_url = resolve_api_url(url)
        pages: list[dict[str, Any]] = []
        page_no = 1
        total_pages = 1

        while page_no <= total_pages:
            page = self.http_get(
                api_url,
                {"pageNo": page_no, "pageSize": self.page_size},
                self.timeout,
            )
            _validate_page(page)
            pages.append(page)
            result = page.get("result", {})
            total_pages = int(result.get("pages") or page_no)
            page_no += 1

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
        return pages


def _requests_get_json(url: str, params: dict[str, int], timeout: int) -> dict[str, Any]:
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Donation API did not return a JSON object")
    return data


def _validate_page(page: dict[str, Any]) -> None:
    if page.get("success") is False:
        message = page.get("message") or "Donation API returned success=false"
        raise ValueError(str(message))
    result = page.get("result")
    if not isinstance(result, dict):
        raise ValueError("Donation API response missing result object")
    if not isinstance(result.get("records"), list):
        raise ValueError("Donation API response missing records list")
    if "pages" not in result:
        raise ValueError("Donation API response missing pages value")
