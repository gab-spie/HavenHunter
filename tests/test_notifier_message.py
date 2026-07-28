"""Message templating tests (no Telegram network involved)."""
from havenhunter.config import Profile
from havenhunter.models import Criteria, Listing
from havenhunter.notifier import message_for


def _profile(template: str) -> Profile:
    return Profile(name="p", label="p", criteria=Criteria(), message_template=template)


def _listing() -> Listing:
    return Listing(source="example", url="u", title="Bright flat", price=1600,
                   area_label="Old town", rooms=2)


def test_plain_template_unchanged():
    profile = _profile("Hello, I am interested.")
    assert message_for(profile, _listing()) == "Hello, I am interested."


def test_placeholders_filled():
    profile = _profile("Interested in {TITLE} ({AREA}) at {PRICE} for {ROOMS} rooms.")
    out = message_for(profile, _listing())
    assert out == "Interested in Bright flat (Old town) at 1600 for 2 rooms."


def test_missing_rooms_leaves_empty():
    profile = _profile("Rooms: {ROOMS}.")
    l = Listing(source="example", url="u", title="t", price=800, area_label="x")
    assert message_for(profile, l) == "Rooms: ."
