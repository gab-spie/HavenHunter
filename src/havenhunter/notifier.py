"""Telegram notifier with a guided one-at-a-time review flow.

Rather than dumping a batch of matches into the chat, the notifier walks the
user through them one card at a time. Each card shows the listing plus its
origin badge and a live counter, with three inline buttons: Validate, Skip,
Done. A second bubble underneath holds only a ready-to-copy contact message.

Design choices worth noting:

* Inline keyboards only ever link out via http(s) URLs. Anything else is
  omitted instead of handed to Telegram: an unexpected scheme silently breaks
  the whole keyboard, and a source-supplied URL is not trusted input.
* Every button press answers instantly with a toast, then edits the card in
  place. Any slower bookkeeping (logging, persistence) happens after the toast,
  so the UI never feels dead.
* Session state is per chat. A review can be paused with Done and resumed later
  without losing position.
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field
from urllib.parse import urlparse

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler

from .config import Profile
from .models import Listing

_ALLOWED_URL_SCHEMES = {"http", "https"}


@dataclass
class Review:
    """A paused-or-running guided review for one chat."""

    profile: str
    listings: list[Listing]
    index: int = 0
    validated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    card_message_id: int | None = None
    copy_message_id: int | None = None

    @property
    def current(self) -> Listing | None:
        if 0 <= self.index < len(self.listings):
            return self.listings[self.index]
        return None

    @property
    def done(self) -> bool:
        return self.index >= len(self.listings)


def message_for(profile: Profile, listing: Listing) -> str:
    """Fill the profile's template for one listing.

    Templates may include optional placeholders that get replaced from the
    listing: {TITLE}, {AREA}, {PRICE}, {ROOMS}. A template without any
    placeholder is returned as is, so simple templates stay simple.
    """
    rooms = str(listing.rooms) if listing.rooms is not None else ""
    replacements = {
        "{TITLE}": listing.title,
        "{AREA}": listing.area_label,
        "{PRICE}": str(listing.price),
        "{ROOMS}": rooms,
    }
    text = profile.message_template
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text.strip()


class Notifier:
    def __init__(
        self,
        app: Application,
        chat_id: int,
        profiles: dict[str, Profile],
        allowed_ids: frozenset[int] | None = None,
    ):
        self._app = app
        self._chat_id = chat_id
        self._profiles = profiles
        # Owner-only, same as the command handlers: CallbackQueryHandler has no
        # filters argument, so this is enforced entirely inside _on_button.
        self._allowed_ids = allowed_ids if allowed_ids is not None else frozenset({chat_id})
        self._reviews: dict[int, Review] = {}
        app.add_handler(CallbackQueryHandler(self._on_button, pattern=r"^rv:"))

    async def start_review(
        self, profile: str, listings: list[Listing], announce_empty: bool = True
    ) -> None:
        """Open a guided review for a batch of fresh listings.

        `announce_empty` controls the empty-result message. Manual scans set it
        so the user gets feedback; scheduled scans clear it to stay silent when
        there is nothing new.
        """
        if not listings:
            if announce_empty:
                await self._app.bot.send_message(
                    chat_id=self._chat_id,
                    text="Nothing new to review. Standing by.",
                )
            return
        review = Review(profile=profile, listings=listings)
        card = await self._app.bot.send_message(chat_id=self._chat_id, text="Preparing review...")
        copy = await self._app.bot.send_message(chat_id=self._chat_id, text="...")
        review.card_message_id = card.message_id
        review.copy_message_id = copy.message_id
        self._reviews[self._chat_id] = review
        await self._render(self._chat_id)

    def _keyboard(self, listing: Listing) -> InlineKeyboardMarkup:
        rows = []
        scheme = urlparse(listing.url).scheme.lower()
        if scheme in _ALLOWED_URL_SCHEMES:
            rows.append([InlineKeyboardButton("Open listing", url=listing.url)])
        # Any other scheme (or none) is dropped rather than passed to Telegram:
        # a bad scheme silently breaks the whole inline keyboard, not just
        # this one button.
        rows.append(
            [
                InlineKeyboardButton("Validate", callback_data="rv:ok"),
                InlineKeyboardButton("Skip", callback_data="rv:skip"),
            ]
        )
        rows.append([InlineKeyboardButton("Done for now", callback_data="rv:done")])
        return InlineKeyboardMarkup(rows)

    def _card_text(self, review: Review, listing: Listing) -> str:
        pos = review.index + 1
        total = len(review.listings)
        bits = [
            f"[{listing.source}]  ({pos}/{total})",
            f"{listing.title}",
            f"{listing.price} / month · {listing.area_label}",
        ]
        if listing.tags:
            bits.append(listing.tags)
        if listing.published_at and listing.published_at_reliable:
            bits.append(f"Posted {listing.published_at:%d %b %H:%M}")
        return "\n".join(bits)

    async def _render(self, chat_id: int) -> None:
        review = self._reviews.get(chat_id)
        if review is None:
            return
        if review.done:
            await self._finish(chat_id, review)
            return
        listing = review.current
        assert listing is not None
        profile = self._profiles[review.profile]
        await self._app.bot.edit_message_text(
            chat_id=chat_id,
            message_id=review.card_message_id,
            text=self._card_text(review, listing),
            reply_markup=self._keyboard(listing),
            disable_web_page_preview=True,
        )
        # The copy bubble holds only the message, wrapped so it is one tap to copy.
        await self._app.bot.edit_message_text(
            chat_id=chat_id,
            message_id=review.copy_message_id,
            text=f"<pre>{html.escape(message_for(profile, listing))}</pre>",
            parse_mode="HTML",
        )

    async def _finish(self, chat_id: int, review: Review) -> None:
        await self._app.bot.edit_message_text(
            chat_id=chat_id,
            message_id=review.card_message_id,
            text=(f"Review done. {len(review.validated)} validated, "
                  f"{len(review.skipped)} skipped."),
        )
        await self._app.bot.edit_message_text(
            chat_id=chat_id, message_id=review.copy_message_id, text="...",
        )
        self._reviews.pop(chat_id, None)

    async def _on_button(self, update: Update, _context) -> None:
        query = update.callback_query
        if query is None or query.message is None:
            return
        chat_id = query.message.chat_id
        user = update.effective_user
        if chat_id not in self._allowed_ids or (
            user is not None and user.id not in self._allowed_ids
        ):
            return  # not the owner: ignore silently, no toast, no bookkeeping

        review = self._reviews.get(chat_id)
        action = query.data.split(":", 1)[1]

        toast = {"ok": "Validated", "skip": "Skipped", "done": "Paused"}.get(action, "")
        await query.answer(text=toast)  # instant feedback, before any bookkeeping

        if review is None:
            return
        listing = review.current
        if action == "done":
            await self._finish(chat_id, review)
            return
        if listing is not None:
            if action == "ok":
                review.validated.append(listing.key())
            elif action == "skip":
                review.skipped.append(listing.key())
        review.index += 1
        await self._render(chat_id)
