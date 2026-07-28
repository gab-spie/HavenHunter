"""End-to-end pipeline test against the offline example source."""
import asyncio

from havenhunter.config import Profile
from havenhunter.dedup import InMemoryStore
from havenhunter.models import Criteria
from havenhunter.pipeline import run
from havenhunter.sources import available


def _profile(max_price: int, min_rooms: int) -> Profile:
    return Profile(
        name="test",
        label="test",
        criteria=Criteria(
            default_max_price=max_price,
            min_rooms=min_rooms,
            furnished_required=True,
        ),
        message_template="hello",
    )


def test_example_source_registered():
    assert "example" in available()


def test_criteria_filter_by_budget():
    profile = _profile(max_price=1000, min_rooms=0)
    store = InMemoryStore()
    result = asyncio.run(run(profile, ["example"], store))
    # Only the sub-1000 listings survive the budget ceiling.
    assert all(l.price <= 1000 for l in result.fresh)
    assert result.fresh, "expected at least one affordable match"


def test_dedup_second_run_is_empty():
    profile = _profile(max_price=2000, min_rooms=0)
    store = InMemoryStore()
    first = asyncio.run(run(profile, ["example"], store))
    second = asyncio.run(run(profile, ["example"], store))
    assert first.fresh, "first run should surface new listings"
    assert second.fresh == [], "second run must surface nothing new"


def test_min_rooms_filter():
    profile = _profile(max_price=2000, min_rooms=2)
    store = InMemoryStore()
    result = asyncio.run(run(profile, ["example"], store))
    assert all((l.rooms or 0) >= 2 for l in result.fresh)


def test_excluded_area_is_rejected():
    from havenhunter.models import Listing
    criteria = Criteria(default_max_price=2000, excluded_areas=[18])
    in_18 = Listing(source="example", url="a", title="a", price=900,
                    area_label="Paris 18e", area_code=18)
    in_11 = Listing(source="example", url="b", title="b", price=900,
                    area_label="Paris 11e", area_code=11)
    unknown = Listing(source="example", url="c", title="c", price=900,
                      area_label="somewhere")
    assert criteria.accepts(in_18) is False
    assert criteria.accepts(in_11) is True
    assert criteria.accepts(unknown) is True  # unknown area is not excluded
