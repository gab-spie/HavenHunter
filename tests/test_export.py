"""CSV export tests."""
import csv

from havenhunter.export import to_csv
from havenhunter.models import Listing


def _listing(url, price):
    return Listing(source="example", url=url, title=f"t-{url}", price=price, area_label="x")


def test_csv_round_trip(tmp_path):
    listings = [_listing("a", 800), _listing("b", 1200)]
    path = to_csv(listings, tmp_path / "out" / "run.csv")
    assert path.exists()

    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["url"] for r in rows] == ["a", "b"]
    assert [int(r["price"]) for r in rows] == [800, 1200]


def test_csv_header(tmp_path):
    path = to_csv([_listing("a", 800)], tmp_path / "run.csv")
    with path.open(encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert header[0] == "source" and "url" in header
