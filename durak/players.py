"""Player interface plus the interactive terminal player."""

from __future__ import annotations

from typing import Optional, Sequence

from .cards import Card
from .engine import GameView, TableEntry


class Player:
    """Base class: the engine only ever calls these two methods."""

    is_human = False

    def __init__(self, name: str) -> None:
        self.name = name
        self.hand: list[Card] = []

    def choose_attack(
        self, view: GameView, legal: Sequence[Card], initial: bool
    ) -> Optional[Card]:
        """Pick a card to attack/throw in with, or ``None`` to pass.

        ``None`` is not allowed when ``initial`` is True (the opening attack of
        a bout is mandatory) — the engine will pick for you if you try.
        """
        raise NotImplementedError

    def choose_defense(
        self, view: GameView, attack: Card, legal: Sequence[Card]
    ) -> Optional[Card]:
        """Pick a card that beats ``attack``, or ``None`` to take the table."""
        raise NotImplementedError

    def observe(self, table: Sequence["TableEntry"], taken_by: Optional[str]) -> None:
        """Called for every player when a bout ends, before the table is cleared.

        ``taken_by`` is the defender's name if they picked the cards up, or
        ``None`` if the cards went to the beaten pile. Card-counting players
        override this; everyone else can ignore it.
        """

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} {self.name!r} {len(self.hand)} cards>"


class QuitGame(Exception):
    """Raised when the human asks to leave."""


class HumanPlayer(Player):
    is_human = True

    def __init__(self, name: str, ui) -> None:
        super().__init__(name)
        self.ui = ui

    def choose_attack(self, view, legal, initial):
        return self.ui.ask_attack(view, list(legal), initial)

    def choose_defense(self, view, attack, legal):
        return self.ui.ask_defense(view, attack, list(legal))
