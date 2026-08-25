"""Heuristic computer opponents.

Three difficulties share one body of tactics and differ in how much care they
take:

``easy``    plays a legal card more or less at random and defends greedily.
``normal``  sheds its cheapest cards, hoards trumps, and knows when taking a
            bout is cheaper than burning a high trump.
In transfer mode everyone but ``easy`` also weighs passing the attack on
against blocking it, using the same card-cost yardstick.

``hard``    everything ``normal`` does, plus it remembers the beaten pile, so
            it knows when one of its cards can no longer be beaten by anybody
            and can lead those to bury a short-handed defender in the endgame;
            it also spots ranks it cannot survive being fed and takes early.

The tactic flags below were picked by measuring: every combination was played
6000 hands against plain ``normal`` and only the ones that actually won more
often were kept (see ``tests/test_ai.py::test_hard_beats_normal``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional, Sequence

from .cards import Card, beats, build_deck, card_power
from .engine import GameView, TableEntry, Transfer
from .players import Player

DIFFICULTIES = ("easy", "normal", "hard")

# A trump this big should not be spent beating a cheap plain card.
PRECIOUS_TRUMP = 12
# Once this many cards have been played at us, taking costs more than any
# single card we could save by taking.
MAX_TAKE_ATTACKS = 2


@dataclass(frozen=True)
class Tactics:
    """The individual habits that separate one difficulty from another."""

    # Pick legal moves at random rather than weighing them up.
    random_play: bool = False
    # Remember the beaten pile, and lead cards nobody can beat any more.
    count_cards: bool = False
    # Spot ranks we can't survive being fed, and take early instead.
    trap_aware: bool = False
    # How much a transfer is worth beyond the card it costs (transfer mode).
    # Swept like the flags above, but this one came out flat: anything in 0-3
    # plays the same within noise, so the exact value here is not load bearing.
    transfer_bonus: int = 3


TACTICS = {
    "easy": Tactics(random_play=True),
    "normal": Tactics(),
    "hard": Tactics(count_cards=True, trap_aware=True),
}


class AIPlayer(Player):
    is_human = False

    def __init__(
        self,
        name: str,
        difficulty: str = "normal",
        rng: Optional[random.Random] = None,
        deck_size: int = 36,
        tactics: Optional[Tactics] = None,
    ) -> None:
        super().__init__(name)
        if difficulty not in DIFFICULTIES:
            raise ValueError(f"unknown difficulty: {difficulty}")
        self.difficulty = difficulty
        self.tactics = tactics or TACTICS[difficulty]
        self.rng = rng or random.Random()
        self._full_deck = frozenset(build_deck(deck_size))
        self.beaten: set[Card] = set()

    # ------------------------------------------------------- card counting

    def observe(self, table: Sequence[TableEntry], taken_by: Optional[str]) -> None:
        """Remember the beaten pile — those cards can never come back."""
        if not self.tactics.count_cards or taken_by is not None:
            return
        for entry in table:
            self.beaten.update(entry.cards())

    def outstanding(self) -> set[Card]:
        """Cards that could still be in somebody's hand or the stock."""
        return set(self._full_deck) - self.beaten - set(self.hand)

    def is_unbeatable(self, card: Card, trump: str) -> bool:
        """True if no card left in play can beat ``card``."""
        if not self.tactics.count_cards:
            return False
        return not any(beats(card, other, trump) for other in self.outstanding())

    # ------------------------------------------------------------- attacking

    def choose_attack(self, view: GameView, legal: Sequence[Card], initial: bool) -> Optional[Card]:
        legal = list(legal)
        if not legal:
            return None
        if self.tactics.random_play:
            if not initial and self.rng.random() < 0.35:
                return None
            return self.rng.choice(legal)

        key = card_power_for(view.trump_suit)
        killer = self._killer_card(view, legal)
        if killer is not None:
            return killer
        if initial:
            return self._opening_attack(view, legal)
        if not self._worth_adding(view, legal):
            return None
        plain = [c for c in legal if c.suit != view.trump_suit]
        return min(plain or legal, key=key)

    def _killer_card(self, view: GameView, legal: list[Card]) -> Optional[Card]:
        """In the endgame, lead a card nobody can beat to force a pick-up."""
        if not self.tactics.count_cards or not view.endgame:
            return None
        unstoppable = [c for c in legal if self.is_unbeatable(c, view.trump_suit)]
        if not unstoppable:
            return None
        # Cheapest first: the monsters keep their value for the next bout too.
        return min(unstoppable, key=card_power_for(view.trump_suit))

    def _opening_attack(self, view: GameView, legal: list[Card]) -> Card:
        """Lead the cheapest card, saving trumps for when they decide a bout."""
        trump = view.trump_suit
        key = card_power_for(trump)
        plain = [c for c in legal if c.suit != trump]
        return min(plain or legal, key=key)

    def _worth_adding(self, view: GameView, legal: list[Card]) -> bool:
        """Decide whether throwing another card in is a good idea."""
        trump = view.trump_suit
        cheapest = min(legal, key=card_power_for(trump))
        defender_cards = view.defender_hand_count

        if view.taken:
            # They are already picking up: bury them in cheap cards.
            return cheapest.suit != trump or view.endgame
        if cheapest.suit == trump:
            # Only trumps left to add — worth it only to finish someone off.
            return view.endgame and defender_cards <= 2
        return True

    # ------------------------------------------------------------- defending

    def choose_defense(self, view, attack, legal=(), transfers=()):
        legal, transfers = list(legal), list(transfers)
        if not legal and not transfers:
            return None
        if self.tactics.random_play:
            if transfers and self.rng.random() < 0.5:
                return Transfer(self.rng.choice(transfers))
            if not legal or self.rng.random() < 0.1:
                return None
            return min(legal, key=card_power_for(view.trump_suit))

        trump = view.trump_suit
        key = card_power_for(trump)
        plain = [c for c in legal if c.suit != trump]
        best = min(plain or legal, key=key) if legal else None

        if transfers:
            pass_on = self._best_transfer(view, transfers, best)
            if pass_on is not None:
                return Transfer(pass_on)
        if best is None:
            return None
        return None if self._should_take(view, attack, best) else best

    def _best_transfer(
        self, view: GameView, transfers: list[Card], best_block: Optional[Card]
    ) -> Optional[Card]:
        """Pick a card to pass the attack on with, or ``None`` to stay and fight.

        Passing costs one card but gets us out of the whole bout, so it wins
        unless blocking is clearly cheaper — which happens when the only card
        of the right rank is a trump and we hold a spare low card that beats.
        """
        key = card_power_for(view.trump_suit)
        cheapest = min(transfers, key=key)
        if best_block is None:
            return cheapest  # the alternative is picking the table up
        return cheapest if key(cheapest) <= key(best_block) + self.tactics.transfer_bonus else None

    def _should_take(self, view: GameView, attack: Card, defense: Card) -> bool:
        """Sometimes swallowing the table beats spending a card you need."""
        trump = view.trump_suit
        if defense.suit != trump or attack.suit == trump:
            # A plain-suit answer is cheap, and trump can only be met with trump.
            return False

        attacks = len(view.table)  # cards thrown at us so far this bout
        if attacks > MAX_TAKE_ATTACKS:
            return False  # too big a pile to swallow, whatever it would save

        if view.endgame:
            # No refills left: a big trump usually wins the last bouts outright.
            return defense.rank >= PRECIOUS_TRUMP and attacks == 1 and len(self.hand) >= 3
        if self.tactics.trap_aware and self._rank_trap(view, attack):
            return True
        return defense.rank >= PRECIOUS_TRUMP and attacks == 1

    def _rank_trap(self, view: GameView, attack: Card) -> bool:
        """Would defending here just invite more of a rank we cannot handle?

        If copies of the attacking rank are still out there and we hold at most
        one answer to it, beating this card only buys one round before we pick
        the whole pile up anyway.
        """
        seen = sum(1 for entry in view.table for c in entry.cards() if c.rank == attack.rank)
        seen += sum(1 for c in self.hand if c.rank == attack.rank)
        if self.tactics.count_cards:
            seen += sum(1 for c in self.beaten if c.rank == attack.rank)
        if seen >= 4:
            return False  # we have accounted for every copy of this rank
        answers = sum(1 for c in self.hand if beats(attack, c, view.trump_suit))
        return answers <= 1


def card_power_for(trump: str):
    return lambda card: card_power(card, trump)


def _advisor(view: GameView) -> AIPlayer:
    bot = AIPlayer("advisor", "normal")
    bot.hand = list(view.hand)
    return bot


def suggest_move(view: GameView, legal: Sequence[Card], initial: bool) -> Optional[Card]:
    """Hint for the human: what a 'normal' bot would do in this spot."""
    return _advisor(view).choose_attack(view, legal, initial)


def suggest_defense(view: GameView, attack: Card, legal: Sequence[Card], transfers: Sequence[Card] = ()):
    return _advisor(view).choose_defense(view, attack, legal, transfers)


__all__ = ["AIPlayer", "DIFFICULTIES", "TACTICS", "Tactics", "suggest_move", "suggest_defense"]
