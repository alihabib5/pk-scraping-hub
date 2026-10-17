"""PPRA dropdown filters: the site takes option ids, never names."""

from urllib.parse import parse_qs, urlparse

from app.core import exports
from app.scrapers.ppra import filters
from app.scrapers.ppra.parsers import parse_options
from app.scrapers.ppra.schemas import PpraFilters

BASE = "https://epms.ppra.gov.pk/public/tenders/active-tenders"


def _params(f: PpraFilters) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(filters.build_search_url(f, BASE)).query).items()}


def test_parse_options_reads_every_dropdown():
    html = """
    <select name="sector"><option value="">All Sectors</option>
      <option value="9">Electrical Items</option><option value="14">Info and Comm Tech</option></select>
    <select name="organization"><option value="">All Organizations</option>
      <option value="11">Water and Power   Development Authority (WAPDA)</option></select>
    <select name="unrelated"><option value="1">x</option></select>
    """
    assert parse_options(html) == {
        "sector": [{"value": "9", "label": "Electrical Items"}, {"value": "14", "label": "Info and Comm Tech"}],
        "organization": [{"value": "11", "label": "Water and Power Development Authority (WAPDA)"}],
    }


def test_seed_has_the_full_lists():
    options = filters.get_filter_options()["options"]
    assert len(options["sector"]) >= 29
    assert len(options["organization"]) > 1000
    assert {"tender_type", "tender_method", "procurement_category", "tender_nature", "country", "status"} <= set(options)


def test_search_url_sends_site_ids():
    params = _params(PpraFilters(sector="14", organization="11", category="1", tender_method="2"))
    assert params == {"sector": "14", "organization": "11", "procurement_category": "1", "tender_method": "2"}


def test_names_from_older_runs_are_converted_to_ids():
    params = _params(PpraFilters(
        sector="Electrical Items", category="Goods", tender_type="Pre-qualification Notice",
        nature="International", status="Cancelled", country="Pakistan",
    ))
    assert params == {
        "sector": "9", "procurement_category": "1", "tender_type": "2",
        "tender_nature": "1", "status": "2", "country": "178",
    }


def test_all_and_blank_are_not_sent():
    assert _params(PpraFilters()) == {}
    assert _params(PpraFilters(sector="", organization=None, category="ALL")) == {}


def test_filename_and_labels_show_names_not_ids():
    run = {
        "scraper": "ppra", "run_id": "r1", "started_at": "2026-10-17T06:50:03",
        "filters": {"advertise_from": "2026-10-16", "advertise_to": "2026-10-17",
                    "category": "1", "sector": "14", "organization": "11", "country": "178"},
    }
    assert exports.excel_name(run) == (
        "PPRA_Tenders(16-10-2026 to 17-10-2026, Goods, Info and Comm Tech, "
        "Water and Power Development Authority (WAPDA)).xlsx"
    )
