"""Cards, suits and the core "what beats what" rule for Durak."""

from __future__ import annotations

import random
from typing import NamedTuple

# Durak is played with a stripped deck: 6 through Ace.
RANK_NAMES = {
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "10",
    11: "J",
    12: "Q",
    13: "K",
    14: "A",
}

SUITS = ("S", "H", "D", "C")
SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
SUIT_NAMES = {"S": "Spades", "H": "Hearts", "D": "Diamonds", "C": "Clubs"}
RED_SUITS = frozenset({"H", "D"})

DECK_SIZES = (20, 24, 36, 52)


class Card(NamedTuple):
    rank: int
    suit: str

    @property
    def rank_name(self) -> str:
        return RANK_NAMES[self.rank]

    def label(self, ascii_only: bool = False, ranks: dict | None = None) -> str:
        """Short one-line name, e.g. ``10♦``, ``10D``, or ``Т♦`` in Russian.

        ``ranks`` overrides the face-card letters (J/Q/K/A) for a language that
        writes them differently; the number cards are the same everywhere.
        """
        name = (ranks or {}).get(self.rank) or RANK_NAMES[self.rank]
        suit = self.suit if ascii_only else SUIT_SYMBOLS[self.suit]
        return f"{name}{suit}"

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.label()


def build_deck(size: int = 36) -> list[Card]:
    """Build an ordered deck of ``size`` cards (highest ranks are always kept)."""
    if size % 4 or not 8 <= size <= 52:
        raise ValueError(f"unsupported deck size: {size}")
    ranks_per_suit = size // 4
    lowest = 15 - ranks_per_suit
    if lowest < 2:
        raise ValueError(f"unsupported deck size: {size}")
    if lowest < 6:
        # Ranks 2..5 only exist in a 52 card deck; extend the name table lazily.
        for rank in range(lowest, 6):
            RANK_NAMES.setdefault(rank, str(rank))
    return [Card(rank, suit) for suit in SUITS for rank in range(lowest, 15)]


def shuffled_deck(rng: random.Random, size: int = 36) -> list[Card]:
    deck = build_deck(size)
    rng.shuffle(deck)
    return deck


def beats(attack: Card, defense: Card, trump: str) -> bool:
    """True if ``defense`` legally beats ``attack`` with ``trump`` as the trump suit."""
    if defense.suit == attack.suit:
        return defense.rank > attack.rank
    if defense.suit == trump:
        return attack.suit != trump
    return False


def sort_key(trump: str):
    """Display order for a hand: trumps first, then the plain suits, low to high.

    Trumps lead so your strongest cards are always in the same place — the far
    left — no matter which suit happens to be trump this game. This is display
    order only; for "how much is this card worth" use :func:`card_power`.
    """

    def key(card: Card) -> tuple[int, int, int]:
        is_trump = card.suit == trump
        return (0 if is_trump else 1, SUITS.index(card.suit), card.rank)

    return key


def card_power(card: Card, trump: str) -> int:
    """A single number for "how much does it hurt to give this card up"."""
    return card.rank + (100 if card.suit == trump else 0)
