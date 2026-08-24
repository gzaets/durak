"""The Durak rules engine (podkidnoy / "throw-in" durak).

The engine owns all state and enforces every rule; players are asked for
decisions through :class:`~durak.players.Player` and can only ever pick from a
list of legal moves the engine hands them.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Iterable, Optional, Sequence

from .cards import Card, beats, shuffled_deck, sort_key

if TYPE_CHECKING:  # pragma: no cover
    from .players import Player as PlayerProtocol

HAND_SIZE = 6
MAX_TABLE = 6


@dataclass
class TableEntry:
    """One attack card, plus the card that beat it (if any)."""

    attack: Card
    defense: Optional[Card] = None

    @property
    def beaten(self) -> bool:
        return self.defense is not None

    def cards(self) -> list[Card]:
        return [self.attack] if self.defense is None else [self.attack, self.defense]


@dataclass
class PlayerInfo:
    """What one player is allowed to know about another."""

    name: str
    hand_count: int
    is_human: bool
    role: str  # "attacker" | "defender" | "thrower" | "idle" | "out"
    seat: int


@dataclass
class GameView:
    """A read-only snapshot handed to whoever is being asked to move."""

    you: str
    hand: list[Card]
    trump_suit: str
    trump_card: Optional[Card]
    deck_count: int
    discard_count: int
    table: list[TableEntry]
    attack_limit: int
    attacker: str
    defender: str
    players: list[PlayerInfo]
    taken: bool
    log: list[str]

    @property
    def unbeaten(self) -> list[Card]:
        return [e.attack for e in self.table if not e.beaten]

    @property
    def table_ranks(self) -> set[int]:
        ranks = set()
        for entry in self.table:
            ranks.add(entry.attack.rank)
            if entry.defense:
                ranks.add(entry.defense.rank)
        return ranks

    def info(self, name: str) -> Optional[PlayerInfo]:
        return next((p for p in self.players if p.name == name), None)

    @property
    def defender_hand_count(self) -> int:
        info = self.info(self.defender)
        return info.hand_count if info else 0

    @property
    def endgame(self) -> bool:
        """True once the deck is gone: cards can no longer be replaced."""
        return self.deck_count == 0


@dataclass
class GameResult:
    durak: Optional[str]
    bouts: int
    order_out: list[str] = field(default_factory=list)


class Durak:
    def __init__(
        self,
        players: Sequence["PlayerProtocol"],
        rng: Optional[random.Random] = None,
        deck_size: int = 36,
        log_sink: Optional[Callable[[str], None]] = None,
        max_hand: int = HAND_SIZE,
    ) -> None:
        if not 2 <= len(players) <= 6:
            raise ValueError("Durak needs between 2 and 6 players")
        if deck_size < len(players) * max_hand + 1:
            raise ValueError(
                f"a {deck_size} card deck cannot deal {max_hand} cards to "
                f"{len(players)} players and still leave a stock"
            )
        self.players = list(players)
        self.rng = rng or random.Random()
        self.max_hand = max_hand
        self.deck = shuffled_deck(self.rng, deck_size)
        self.discard: list[Card] = []
        self.log: list[str] = []
        self.log_sink = log_sink
        self.finished: list["PlayerProtocol"] = []
        self.table: list[TableEntry] = []
        self.taken = False
        self.bouts = 0
        self.attack_limit = MAX_TABLE

        # The bottom card of the stock is turned face up; its suit is trump and
        # it is the very last card anybody draws.
        self.trump_card: Optional[Card] = self.deck[-1]
        self.trump: str = self.trump_card.suit

        for player in self.players:
            player.hand = []
        self.attacker_seat = 0
        self.defender_seat = 1

    # ------------------------------------------------------------------ setup

    def say(self, message: str) -> None:
        self.log.append(message)
        if self.log_sink:
            self.log_sink(message)

    def deal(self) -> None:
        for _ in range(self.max_hand):
            for player in self.players:
                player.hand.append(self.deck.pop(0))
        for player in self.players:
            self.sort_hand(player)
        self.attacker_seat = self._pick_first_attacker()
        self.defender_seat = self._next_seat(self.attacker_seat)

    def sort_hand(self, player: "PlayerProtocol") -> None:
        player.hand.sort(key=sort_key(self.trump))

    def _pick_first_attacker(self) -> int:
        """Lowest trump in hand opens; if nobody holds one, pick at random."""
        best_seat = None
        best_rank = 99
        for seat, player in enumerate(self.players):
            trumps = [c.rank for c in player.hand if c.suit == self.trump]
            if trumps and min(trumps) < best_rank:
                best_rank = min(trumps)
                best_seat = seat
        if best_seat is None:
            best_seat = self.rng.randrange(len(self.players))
            self.say(f"Nobody was dealt a trump — {self.players[best_seat].name} opens.")
        else:
            card = Card(best_rank, self.trump)
            self.say(
                f"{self.players[best_seat].name} holds the lowest trump "
                f"({card.label()}) and attacks first."
            )
        return best_seat

    # ---------------------------------------------------------------- helpers

    @property
    def active(self) -> list["PlayerProtocol"]:
        return [p for p in self.players if p not in self.finished]

    def is_active(self, player: "PlayerProtocol") -> bool:
        return player not in self.finished

    def _next_seat(self, seat: int, skip: Iterable[int] = ()) -> int:
        """Next seat clockwise that is still in the game."""
        skip = set(skip)
        count = len(self.players)
        for step in range(1, count + 1):
            candidate = (seat + step) % count
            if candidate in skip:
                continue
            if self.is_active(self.players[candidate]):
                return candidate
        return seat

    @property
    def attacker(self) -> "PlayerProtocol":
        return self.players[self.attacker_seat]

    @property
    def defender(self) -> "PlayerProtocol":
        return self.players[self.defender_seat]

    def attack_order(self) -> list["PlayerProtocol"]:
        """Who may put cards down, in priority order.

        The player whose turn it is to attack goes first; after that the throw-in
        right passes around the table, ending with the defender's right-hand
        neighbour.
        """
        order = [self.attacker]
        seat = self.defender_seat
        for _ in range(len(self.players)):
            seat = self._next_seat(seat)
            player = self.players[seat]
            if player is self.defender or player in order:
                continue
            order.append(player)
        return order

    def role_of(self, player: "PlayerProtocol") -> str:
        if player in self.finished:
            return "out"
        if player is self.defender:
            return "defender"
        if player is self.attacker:
            return "attacker"
        return "thrower" if len(self.active) > 2 else "idle"

    def view_for(self, player: "PlayerProtocol") -> GameView:
        return GameView(
            you=player.name,
            hand=list(player.hand),
            trump_suit=self.trump,
            trump_card=self.trump_card,
            deck_count=len(self.deck),
            discard_count=len(self.discard),
            table=[TableEntry(e.attack, e.defense) for e in self.table],
            attack_limit=self.attack_limit,
            attacker=self.attacker.name,
            defender=self.defender.name,
            players=[
                PlayerInfo(p.name, len(p.hand), p.is_human, self.role_of(p), seat)
                for seat, p in enumerate(self.players)
            ],
            taken=self.taken,
            log=list(self.log),
        )

    # ------------------------------------------------------------ legal moves

    def legal_attacks(self, player: "PlayerProtocol") -> list[Card]:
        """Any card opens a bout; after that only ranks already on the table."""
        if len(self.table) >= self.attack_limit:
            return []
        if not self.table:
            return list(player.hand)
        ranks = {e.attack.rank for e in self.table}
        ranks |= {e.defense.rank for e in self.table if e.defense}
        return [c for c in player.hand if c.rank in ranks]

    def legal_defenses(self, attack: Card) -> list[Card]:
        return [c for c in self.defender.hand if beats(attack, c, self.trump)]

    # ------------------------------------------------------------------ bouts

    def play_bout(self) -> None:
        self.bouts += 1
        attacker, defender = self.attacker, self.defender
        self.table = []
        self.taken = False
        # A defender can never be asked to beat more cards than they hold.
        self.attack_limit = min(MAX_TABLE, len(defender.hand))
        self.say("")
        self.say(f"— {attacker.name} attacks {defender.name} —")

        passed: set[int] = set()
        while len(self.table) < self.attack_limit:
            played_by, card = self._collect_attack(passed)
            if card is None:
                break

            self.table.append(TableEntry(card))
            played_by.hand.remove(card)
            verb = "attacks with" if len(self.table) == 1 else "adds"
            self.say(f"{played_by.name} {verb} {card.label()}.")
            passed.clear()

            if self.taken:
                continue
            if not self._resolve_defense(card):
                self.taken = True
                self.say(f"{defender.name} takes the cards.")

        self._settle_bout()

    def _collect_attack(self, passed: set[int]) -> tuple[Optional["PlayerProtocol"], Optional[Card]]:
        """Ask each eligible attacker in turn for one card. ``None`` means all passed."""
        initial = not self.table
        for player in self.attack_order():
            if id(player) in passed:
                continue
            legal = self.legal_attacks(player)
            if not legal:
                passed.add(id(player))
                continue
            card = player.choose_attack(self.view_for(player), legal, initial)
            if card is None:
                if initial:
                    # Opening the bout is mandatory; take their cheapest card.
                    card = min(legal, key=sort_key(self.trump))
                else:
                    passed.add(id(player))
                    continue
            if card not in legal:
                raise ValueError(f"{player.name} played an illegal attack: {card}")
            return player, card
        return None, None

    def _resolve_defense(self, attack: Card) -> bool:
        """Return True if the defender beat ``attack``."""
        defender = self.defender
        legal = self.legal_defenses(attack)
        if not legal:
            return False
        card = defender.choose_defense(self.view_for(defender), attack, legal)
        if card is None:
            return False
        if card not in legal:
            raise ValueError(f"{defender.name} played an illegal defense: {card}")
        defender.hand.remove(card)
        self.table[-1].defense = card
        self.say(f"{defender.name} beats {attack.label()} with {card.label()}.")
        return True

    def _settle_bout(self) -> None:
        defender = self.defender
        cards = [c for entry in self.table for c in entry.cards()]
        for player in self.players:
            player.observe(list(self.table), defender.name if self.taken else None)
        if self.taken:
            defender.hand.extend(cards)
            self.sort_hand(defender)
            self.say(f"{defender.name} picks up {len(cards)} card(s).")
        else:
            self.discard.extend(cards)
            if cards:
                self.say(f"{defender.name} beat off the attack — {len(cards)} card(s) discarded.")
        self.table = []

        self._refill()
        newly_out = self._retire_empty_hands()

        # Beating off the attack earns you the right to attack next.
        if self.taken or defender in self.finished:
            self.attacker_seat = self._next_seat(self.defender_seat)
        else:
            self.attacker_seat = self.defender_seat
        if not self.is_active(self.players[self.attacker_seat]):
            self.attacker_seat = self._next_seat(self.attacker_seat)
        self.defender_seat = self._next_seat(self.attacker_seat)
        self.taken = False
        self.attack_limit = min(MAX_TABLE, len(self.defender.hand))
        for name in newly_out:
            self.say(f"{name} is out of cards and safe.")

    def _refill(self) -> None:
        """Top hands back up to six, attacker first and defender last."""
        order = [p for p in self.attack_order() if self.is_active(p)]
        if self.is_active(self.defender):
            order.append(self.defender)
        for player in order:
            while self.deck and len(player.hand) < self.max_hand:
                player.hand.append(self.deck.pop(0))
            self.sort_hand(player)

    def _retire_empty_hands(self) -> list[str]:
        out = []
        if self.deck:
            return out
        for player in self.players:
            if self.is_active(player) and not player.hand:
                self.finished.append(player)
                out.append(player.name)
        return out

    # ------------------------------------------------------------------- game

    def run(self) -> GameResult:
        self.deal()
        while len(self.active) > 1:
            self.play_bout()
        remaining = self.active
        durak = remaining[0].name if remaining else None
        return GameResult(
            durak=durak,
            bouts=self.bouts,
            order_out=[p.name for p in self.finished],
        )
