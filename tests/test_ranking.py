"""Ranking heuristic tests."""
from datetime import datetime, timedelta

from havenhunter.models import Listing
from havenhunter.ranking import rank, score_batch


def _listing(url, price, surface, hours_old):
    return Listing(
        source="example",
        url=url,
        title=url,
        price=price,
        area_label="x",
        surface=surface,
        published_at=datetime.now() - timedelta(hours=hours_old),
        published_at_reliable=True,
    )


def test_cheaper_per_m2_ranks_higher():
    # Same surface and freshness, cheaper wins.
    a = _listing("a", price=1000, surface=50, hours_old=1)  # 20 /m2
    b = _listing("b", price=2000, surface=50, hours_old=1)  # 40 /m2
    assert rank([b, a])[0].url == "a"


def test_fresher_ranks_higher_when_value_equal():
    a = _listing("a", price=1000, surface=50, hours_old=1)
    b = _listing("b", price=1000, surface=50, hours_old=48)
    assert rank([b, a])[0].url == "a"


def test_scores_are_bounded():
    items = [
        _listing("a", 800, 25, 2),
        _listing("b", 1500, 40, 10),
        _listing("c", 1200, 30, 30),
    ]
    for _, s in score_batch(items):
        assert 0.0 <= s <= 1.0


def test_empty_batch():
    assert rank([]) == []
    assert score_batch([]) == []


def test_missing_surface_does_not_crash():
    a = Listing(source="example", url="a", title="a", price=900, area_label="x")
    b = Listing(source="example", url="b", title="b", price=800, area_label="x")
    ranked = rank([a, b])
    assert {l.url for l in ranked} == {"a", "b"}
