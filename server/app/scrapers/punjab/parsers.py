"""Pure HTML parsing for the Punjab Active Tenders page.

Everything read here comes from a remote site and is treated as untrusted: links
are only kept when they match the site's known PDF paths, and a page whose table
no longer looks as expected raises `SiteChanged` rather than saving wrong data.
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Any, NamedTuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

ELEMENT_PREFIX = "ctl00_ContentPlaceHolderSRIS_"

PUBLISH_BOX = ELEMENT_PREFIX + "rdgrdManageTender_ctl00_ctl02_ctl02_FilterTextBox_Publish_Date"

EXPECTED_COLUMNS = (
    "Procurement Title", "Procurement Name", "Type", "Publish Date", "Close Date",
    "Department", "Status", "Tender Notice", "Bidding Document",
)

AUCTION_TITLE = "Sales/Auction/Disposal"
AUCTION_TITLE_ID = "5"

_PDF_LINK = re.compile(r"(?:Tenders|BiddingDocuments)/\d+/\d+/\d{28,}\.pdf")
_PDF_NAME = re.compile(r"/(\d{28,})\.pdf$")
_DETAIL_PATH = re.compile(r"ActiveTendersDetail\.aspx\?id=\d+")
# A PDF name is ddMMyyyyHHmmss (14) + 8 random digits, then the tender id.
_ID_OFFSET = 22

# Link text the site appends to the name of a tender that has a detail page.
_DETAIL_LINK = re.compile(r"\s*\(\s*View Tender Detail\s*\)\s*$", re.IGNORECASE)

_PAGER = re.compile(r"([\d,]+)\s+items?\s+in\s+([\d,]+)\s+pages?", re.IGNORECASE)


class SiteChanged(Exception):
    """The page no longer has the structure this parser was written for."""


class PageInfo(NamedTuple):
    total_records: int
    total_pages: int
    current_page: int
    no_records: bool


def clean_text(value: str | None) -> str:
    """Collapse runs of whitespace, including the site's non-breaking spaces. NUL goes
    too: PostgreSQL refuses it, and one such value would lose a whole page of tenders."""
    return " ".join((value or "").replace("\x00", "").split())


def to_iso_date(value: str | None) -> str | None:
    """`04 Nov 2026` -> `2026-11-04`. ISO matters: the shared closing-date parser
    tries month-first formats, so a day-first date would be misread."""
    try:
        return datetime.strptime(clean_text(value), "%d %b %Y").date().isoformat()
    except ValueError:
        return None


def safe_pdf_url(href: str | None, base_url: str) -> str | None:
    """The absolute PDF link, or None unless `href` is one of the site's known paths."""
    if not href or not _PDF_LINK.fullmatch(href.strip()):
        return None
    return urljoin(base_url.rstrip("/") + "/", href.strip())


def safe_detail_url(href: str | None, base_url: str) -> str | None:
    """The corrigendum's detail page, only when `href` is the site's own detail path."""
    if not href or not _DETAIL_PATH.fullmatch(href.strip()):
        return None
    return urljoin(base_url.rstrip("/") + "/", href.strip())


def tender_id_from_links(*urls: str | None) -> str | None:
    """The site shows no tender number; its id is the tail of each PDF's name."""
    for url in urls:
        match = _PDF_NAME.search(url or "")
        if match:
            return match.group(1)[_ID_OFFSET:]
    return None


def fallback_id(title: str, department: str, published: str | None, closing: str | None) -> str:
    """An id for a row with no usable link. Built from content, never position:
    rows move between pages as new tenders arrive."""
    raw = "|".join((title.lower(), department.lower(), published or "", closing or ""))
    return "PB-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def is_auction(notice_type: str | None) -> bool:
    """True when the site's Procurement Title is Sales/Auction/Disposal."""
    return clean_text(notice_type) == AUCTION_TITLE


def compute_content_hash(data: dict[str, Any]) -> str:
    """sha256 over everything visible, so a Refresh run can spot a changed tender."""
    fields = (
        "title", "notice_type", "procurement_type", "department", "status",
        "published_on", "closing_on", "notice_url", "document_url",
    )
    norm = {field: str(data.get(field) or "").strip().lower() for field in fields}
    return hashlib.sha256(json.dumps(norm, sort_keys=True).encode("utf-8")).hexdigest()


def check_columns(html: str) -> None:
    """Raise SiteChanged unless the results table has the nine expected columns."""
    table = BeautifulSoup(html, "html.parser").select_one("table.rgMasterTable")
    if table is None:
        raise SiteChanged("the results table is missing")
    found = tuple(clean_text(th.get_text(" ")) for th in table.select("th.rgHeader"))
    if found != EXPECTED_COLUMNS:
        raise SiteChanged(f"unexpected result columns: {found}")


def publish_filter_text(html: str) -> str:
    """What the grid's Publish Date filter box holds. The site keeps it after a post, so it
    proves the filter we typed is the one the rows came from."""
    box = BeautifulSoup(html, "html.parser").find("input", id=PUBLISH_BOX)
    return clean_text(box.get("value") if box else "")


def parse_pager(html: str) -> PageInfo:
    """Totals and the current page. A result that fits on one page has no pager,
    so its total is simply the rows shown."""
    soup = BeautifulSoup(html, "html.parser")
    rows = len(soup.select("tr.rgRow, tr.rgAltRow"))
    info = soup.select_one(".rgInfoPart")
    match = _PAGER.search(info.get_text(" ", strip=True)) if info else None
    if not match:
        return PageInfo(rows, 1, 1, rows == 0)
    current = soup.select_one(".rgCurrentPage")
    current_text = current.get_text(strip=True) if current else ""
    return PageInfo(
        int(match.group(1).replace(",", "")),
        int(match.group(2).replace(",", "")),
        int(current_text) if current_text.isdigit() else 0,
        rows == 0,
    )


def parse_listing(html: str, base_url: str) -> list[dict[str, Any]]:
    """Every tender row on the page. `rejected_links` counts links that were dropped."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    twins: dict[str, int] = {}
    for position, row in enumerate(soup.select("tr.rgRow, tr.rgAltRow"), start=1):
        cells = row.find_all("td", recursive=False)
        if len(cells) != len(EXPECTED_COLUMNS):
            raise SiteChanged(f"a result row has {len(cells)} cells")
        text = [clean_text(cell.get_text(" ")) for cell in cells]
        text[1] = _DETAIL_LINK.sub("", text[1])
        hrefs = [(cell.find("a", href=True) or {}).get("href") for cell in cells[7:9]]
        notice_url, document_url = (safe_pdf_url(href, base_url) for href in hrefs)
        rejected = sum(1 for href, url in zip(hrefs, (notice_url, document_url)) if href and not url)

        published_on, closing_on = to_iso_date(text[3]), to_iso_date(text[4])
        title = text[1] or text[0]
        tender_no = tender_id_from_links(notice_url, document_url)
        if not tender_no:
            # shortcut: tells twins apart within one page only; identical rows on different
            # pages still collapse (the run warns), upgrade if the site ever shows them.
            tender_no = fallback_id(title, text[5], published_on, closing_on)
            twins[tender_no] = twins.get(tender_no, 0) + 1
            if twins[tender_no] > 1:
                tender_no += f"-{twins[tender_no]}"
        record: dict[str, Any] = {
            "position": position,
            "tender_no": tender_no,
            "title": title,
            "notice_type": text[0] or None,
            "procurement_type": text[2] or None,
            "department": text[5] or None,
            "status": text[6] or None,
            "published_on": published_on,
            "closing_on": closing_on,
            "notice_url": notice_url,
            "document_url": document_url,
            "rejected_links": rejected,
            # A corrigendum names the tender it amends only through this link.
            "raw_data": {
                "columns": text[:7],
                "detail_url": safe_detail_url((cells[1].find("a", href=True) or {}).get("href"), base_url),
            },
        }
        record["content_hash"] = compute_content_hash(record)
        records.append(record)
    return records
