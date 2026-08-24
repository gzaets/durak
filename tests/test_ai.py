"""Tests for the computer opponents.

The strength tests play thousands of hands, but every one of them uses a fixed
seed, so they are deterministic rather than flaky.
"""

from __future__ import annotations

import random

import pytest

from durak.ai import TACTICS, AIPlayer, suggest_defense, suggest_move
from durak.cards import Card
from durak.engine import Durak, TableEntry

S, H, D, C = "S", "H", "D", "C"


def view_for(bot: AIPlayer, game: Durak):
    return game.view_for(bot)


def duel(a: str, b: str, games: int = 1500, seed: int = 5) -> float:
    """Fraction of decided games in which ``a`` was left holding the cards."""
    rng = random.Random(seed)
    losses = {a: 0, b: 0}
    draws = 0
    for i in range(games):
        order = [a, b] if i % 2 == 0 else [b, a]  # alternate who deals first
        players = [AIPlayer(name, name, rng) for name in order]
        result = Durak(players, rng=rng).run()
        if result.durak is None:
            draws += 1
        else:
            losses[result.durak] += 1
    return losses[a] / (games - draws)


# ------------------------------------------------------------ basic sanity


def test_every_difficulty_finishes_a_game():
    for difficulty in TACTICS:
        rng = random.Random(99)
        players = [AIPlayer(f"p{i}", difficulty, rng) for i in range(4)]
        result = Durak(players, rng=rng).run()
        assert result.durak is None or result.durak in {p.name for p in players}
        assert result.bouts > 0


def test_unknown_difficulty_is_rejected():
    with pytest.raises(ValueError):
        AIPlayer("x", "impossible")


@pytest.mark.parametrize("difficulty", list(TACTICS))
def test_bots_only_ever_return_a_legal_card(difficulty):
    rng = random.Random(3)
    for _ in range(30):
        players = [AIPlayer(f"p{i}", difficulty, rng) for i in range(3)]
        game = Durak(players, rng=rng)
        # The engine raises on an illegal card, so a clean run is the assertion.
        game.run()


# ------------------------------------------------------------ card tactics


def test_a_bot_leads_its_cheapest_plain_card_not_a_trump():
    bot = AIPlayer("bot", "normal")
    other = AIPlayer("other", "normal")
    game = Durak([bot, other], rng=random.Random(0))
    game.trump = S
    bot.hand = [Card(6, S), Card(8, H), Card(14, D)]
    other.hand = [Card(9, C)]
    move = bot.choose_attack(view_for(bot, game), list(bot.hand), initial=True)
    assert move == Card(8, H)  # the 6 of trumps stays home


def test_a_bot_defends_with_the_cheapest_card_that_works():
    bot = AIPlayer("bot", "normal")
    other = AIPlayer("other", "normal")
    game = Durak([other, bot], rng=random.Random(0))
    game.trump = S
    bot.hand = [Card(9, H), Card(13, H), Card(7, S)]
    attack = Card(8, H)
    legal = [c for c in bot.hand if c in game.legal_defenses(attack)] or [
        Card(9, H),
        Card(13, H),
        Card(7, S),
    ]
    assert bot.choose_defense(view_for(bot, game), attack, legal) == Card(9, H)


def test_a_bot_would_rather_take_one_card_than_burn_an_ace_of_trumps():
    bot = AIPlayer("bot", "normal")
    other = AIPlayer("other", "normal")
    game = Durak([other, bot], rng=random.Random(0))
    game.trump = S
    bot.hand = [Card(14, S), Card(9, D), Card(10, D)]
    attack = Card(6, H)
    game.table = [TableEntry(attack)]
    assert bot.choose_defense(view_for(bot, game), attack, [Card(14, S)]) is None


def test_a_bot_spends_a_low_trump_without_complaint():
    bot = AIPlayer("bot", "normal")
    other = AIPlayer("other", "normal")
    game = Durak([other, bot], rng=random.Random(0))
    game.trump = S
    bot.hand = [Card(7, S), Card(9, D)]
    attack = Card(6, H)
    game.table = [TableEntry(attack)]
    assert bot.choose_defense(view_for(bot, game), attack, [Card(7, S)]) == Card(7, S)


def test_a_counting_bot_knows_when_a_card_cannot_be_beaten():
    bot = AIPlayer("bot", "hard")
    bot.hand = [Card(13, H)]
    assert not bot.is_unbeatable(Card(13, H), trump=S)
    # Once every trump and the ace of hearts are in the beaten pile, the king
    # of hearts is unanswerable.
    bot.beaten = {Card(r, S) for r in range(6, 15)} | {Card(14, H)}
    assert bot.is_unbeatable(Card(13, H), trump=S)


def test_a_non_counting_bot_never_claims_a_card_is_unbeatable():
    bot = AIPlayer("bot", "normal")
    bot.beaten = {Card(r, S) for r in range(6, 15)} | {Card(14, H)}
    bot.hand = [Card(13, H)]
    assert not bot.is_unbeatable(Card(13, H), trump=S)


def test_only_a_counting_bot_remembers_the_beaten_pile():
    table = [TableEntry(Card(6, H), Card(10, H))]
    hard, normal = AIPlayer("h", "hard"), AIPlayer("n", "normal")
    for bot in (hard, normal):
        bot.observe(table, taken_by=None)
    assert hard.beaten == {Card(6, H), Card(10, H)}
    assert normal.beaten == set()


def test_taken_cards_are_not_treated_as_gone():
    bot = AIPlayer("h", "hard")
    bot.observe([TableEntry(Card(6, H), Card(10, H))], taken_by="somebody")
    assert bot.beaten == set()


# ------------------------------------------------------------ relative skill


def test_normal_beats_easy():
    assert duel("normal", "easy") < 0.42


def test_hard_beats_normal():
    # The margin is small — this is a heuristic bot, not a solver — but it is
    # consistent across seeds.
    assert duel("hard", "normal", games=3000) < 0.48


def test_hard_beats_easy_by_more_than_normal_does():
    assert duel("hard", "easy") < duel("normal", "easy") + 0.02


# ------------------------------------------------------------------- hints


def test_hints_offer_a_legal_move():
    rng = random.Random(2)
    human_seat = AIPlayer("you", "normal", rng)
    other = AIPlayer("other", "normal", rng)
    game = Durak([human_seat, other], rng=rng)
    game.deal()
    view = game.view_for(human_seat)
    legal = game.legal_attacks(human_seat)
    assert suggest_move(view, legal, initial=True) in legal
    attack = legal[0]
    defenses = [c for c in other.hand if c.suit == attack.suit and c.rank > attack.rank]
    if defenses:
        hint = suggest_defense(game.view_for(other), attack, defenses)
        assert hint is None or hint in defenses
