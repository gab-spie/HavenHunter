"""Sheet-logging helpers (pure, no network and no credentials involved)."""
from havenhunter.models import Listing
from havenhunter.sheets import (
    DEFAULT_WORKSHEET,
    HEADERS,
    row_for,
    worksheet_title_for,
)


def _listing() -> Listing:
    return Listing(source="example", url="u", title="Bright flat", price=1600,
                   area_label="Old town", rooms=2)


def test_profile_maps_to_its_own_tab():
    assert worksheet_title_for("solo") == "solo"
    assert worksheet_title_for("shared") == "shared"


def test_missing_profile_falls_back_to_default_tab():
    assert worksheet_title_for(None) == DEFAULT_WORKSHEET
    assert worksheet_title_for("") == DEFAULT_WORKSHEET


def test_row_matches_headers_shape():
    row = row_for(_listing(), "sent")
    assert len(row) == len(HEADERS)


def test_row_carries_listing_fields_in_order():
    row = row_for(_listing(), "sent")
    # HEADERS = timestamp, source, title, price, area, url, status
    assert row[1] == "example"
    assert row[2] == "Bright flat"
    assert row[3] == 1600
    assert row[4] == "Old town"
    assert row[5] == "u"
    assert row[6] == "sent"
