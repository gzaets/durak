"""Rules engine tests. Hands are stacked by hand so outcomes are deterministic."""

from __future__ import annotations

import random

import pytest

from durak.cards import Card, beats, build_deck, card_power, sort_key
from durak.engine import CLASSIC, TRANSFER, Durak, TableEntry, Transfer
from durak.players import Player

S, H, D, C = "S", "H", "D", "C"


class Scripted(Player):
    """Plays a fixed list of moves; ``None`` means pass/take."""

    def __init__(self, name, attacks=(), defenses=()):
        super().__init__(name)
        self.attacks = list(attacks)
        self.defenses = list(defenses)
        self.observed = []
        self.offered_transfers = []

    def choose_attack(self, view, legal, initial):
        move = self.attacks.pop(0) if self.attacks else None
        assert move is None or move in legal, f"{self.name}: {move} not in {legal}"
        return move

    def choose_defense(self, view, attack, legal, transfers=()):
        self.offered_transfers.append(list(transfers))
        move = self.defenses.pop(0) if self.defenses else None
        if isinstance(move, Transfer):
            assert move.card in transfers, f"{self.name}: cannot transfer {move.card}"
        else:
            assert move is None or move in legal, f"{self.name}: {move} not in {legal}"
        return move

    def observe(self, table, taken_by):
        self.observed.append((len(table), taken_by))


def make_game(hands, trump=S, stock=(), seat=0, mode=CLASSIC):
    """Build a game with exact hands, a known trump and a known stock."""
    players = [p for p, _ in hands]
    game = Durak(players, rng=random.Random(0), mode=mode)
    for player, cards in hands:
        player.hand = list(cards)
    game.deck = list(stock)
    game.trump = trump
    game.trump_card = stock[-1] if stock else None
    game.attacker_seat = seat
    game.defender_seat = game._next_seat(seat)
    return game


# ------------------------------------------------------------------- cards


def test_deck_is_36_unique_cards():
    deck = build_deck(36)
    assert len(deck) == 36
    assert len(set(deck)) == 36
    assert min(c.rank for c in deck) == 6
    assert max(c.rank for c in deck) == 14


@pytest.mark.parametrize("size,lowest", [(20, 10), (24, 9), (36, 6), (52, 2)])
def test_deck_sizes_keep_the_high_ranks(size, lowest):
    deck = build_deck(size)
    assert len(deck) == size
    assert min(c.rank for c in deck) == lowest


def test_higher_card_of_same_suit_beats():
    assert beats(Card(7, H), Card(10, H), trump=S)
    assert not beats(Card(10, H), Card(7, H), trump=S)
    assert not beats(Card(10, H), Card(10, H), trump=S)


def test_trump_beats_any_plain_suit():
    assert beats(Card(14, H), Card(6, S), trump=S)
    assert not beats(Card(6, S), Card(14, H), trump=S)


def test_only_a_bigger_trump_beats_a_trump():
    assert beats(Card(9, S), Card(10, S), trump=S)
    assert not beats(Card(10, S), Card(9, S), trump=S)
    assert not beats(Card(10, S), Card(14, H), trump=S)


def test_different_plain_suits_never_beat():
    assert not beats(Card(6, H), Card(14, D), trump=S)


def test_hands_sort_with_trumps_first():
    hand = [Card(14, H), Card(6, S), Card(7, H), Card(14, S)]
    hand.sort(key=sort_key(S))
    # Trumps lead, low to high, then the plain suits.
    assert hand == [Card(6, S), Card(14, S), Card(7, H), Card(14, H)]


def test_the_trump_suit_always_leads_whichever_suit_it_is():
    hand = [Card(14, S), Card(6, H), Card(6, C), Card(6, D)]
    for trump in ("S", "H", "D", "C"):
        ordered = sorted(hand, key=sort_key(trump))
        assert ordered[0].suit == trump


def test_display_order_is_not_value_order():
    """The leftmost card is the lowest trump, which is not the cheapest card."""
    hand = [Card(6, S), Card(7, H)]
    hand.sort(key=sort_key(S))
    assert hand[0] == Card(6, S)
    assert min(hand, key=lambda c: card_power(c, S)) == Card(7, H)


# ------------------------------------------------------------- legal moves


def test_opening_attack_may_use_any_card():
    a = Scripted("A")
    b = Scripted("B")
    game = make_game([(a, [Card(6, H), Card(14, D)]), (b, [Card(7, H)])])
    assert set(game.legal_attacks(a)) == {Card(6, H), Card(14, D)}


def test_throw_ins_are_limited_to_ranks_on_the_table():
    a = Scripted("A")
    b = Scripted("B")
    game = make_game([(a, [Card(6, D), Card(9, C), Card(14, D)]), (b, [Card(7, H)])])
    game.table = [TableEntry(Card(6, H), Card(9, H))]
    # 6 and 9 are on the table, so only those ranks may be added.
    assert set(game.legal_attacks(a)) == {Card(6, D), Card(9, C)}


def test_defense_options_include_trumps_only_against_plain_suits():
    a = Scripted("A")
    b = Scripted("B")
    game = make_game([(a, []), (b, [Card(8, H), Card(6, S), Card(6, C)])], trump=S)
    assert set(game.legal_defenses(Card(7, H))) == {Card(8, H), Card(6, S)}
    assert game.legal_defenses(Card(7, S)) == []


# -------------------------------------------------------------------- bouts


def test_successful_defense_discards_the_table_and_flips_the_attack():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[Card(10, H)])
    game = make_game([(a, [Card(6, H), Card(9, C)]), (b, [Card(10, H), Card(11, C)])])
    game.play_bout()
    assert game.discard == [Card(6, H), Card(10, H)]
    assert a.hand == [Card(9, C)]
    assert b.hand == [Card(11, C)]
    # Beating off the attack earns B the right to attack.
    assert game.attacker is b and game.defender is a


def test_taking_moves_the_whole_table_into_the_defenders_hand():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[None])
    game = make_game([(a, [Card(6, H), Card(9, C)]), (b, [Card(10, H), Card(11, C)])])
    game.play_bout()
    assert game.discard == []
    assert sorted(b.hand) == sorted([Card(10, H), Card(11, C), Card(6, H)])
    # A keeps the attack: B lost their turn by taking.
    assert game.attacker is a and game.defender is b


def test_attack_is_capped_at_six_cards():
    # A holds seven cards of two ranks; both ranks reach the table, so all seven
    # are legal throw-ins, but the sixth card must close the bout.
    attacker_cards = [Card(6, H), Card(6, D), Card(6, C), Card(6, S), Card(7, D), Card(7, C), Card(7, S)]
    a = Scripted("A", attacks=list(attacker_cards))
    b = Scripted("B", defenses=[Card(7, H), None])
    defender_cards = [Card(7, H), Card(9, C), Card(10, C), Card(11, C), Card(12, C), Card(13, C)]
    game = make_game([(a, attacker_cards), (b, defender_cards)])
    game.play_bout()
    assert a.hand == [Card(7, S)]  # the seventh card had nowhere to go
    assert len(b.hand) == 5 + 7  # five left in hand, plus six attacks and one defense


def test_attack_cannot_exceed_the_defenders_hand_size():
    a = Scripted("A", attacks=[Card(6, H), Card(6, D), Card(6, C)])
    b = Scripted("B", defenses=[None])
    game = make_game([(a, [Card(6, H), Card(6, D), Card(6, C)]), (b, [Card(9, C)])])
    game.play_bout()
    # The defender held one card, so only one card could be played at them.
    assert sorted(b.hand) == sorted([Card(9, C), Card(6, H)])
    assert len(a.hand) == 2


def test_a_third_player_may_throw_in_a_matching_rank():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[None, None])
    c = Scripted("C", attacks=[Card(6, D)])
    game = make_game(
        [(a, [Card(6, H), Card(9, S)]), (b, [Card(10, C), Card(11, C)]), (c, [Card(6, D), Card(12, C)])]
    )
    game.play_bout()
    assert Card(6, D) in b.hand and Card(6, H) in b.hand
    assert c.hand == [Card(12, C)]


def test_a_third_player_cannot_throw_in_an_unmatched_rank():
    a, b = Scripted("A"), Scripted("B")
    c = Scripted("C")
    game = make_game([(a, [Card(6, H)]), (b, [Card(10, C)]), (c, [Card(9, D), Card(6, C)])])
    game.table = [TableEntry(Card(6, H))]
    assert game.legal_attacks(c) == [Card(6, C)]  # the 9 has no match on the table


def test_the_engine_rejects_an_illegal_card():
    class Cheat(Scripted):
        def choose_attack(self, view, legal, initial):
            return Card(9, D)  # never legal here

    a = Cheat("A")
    b = Scripted("B", defenses=[None])
    game = make_game([(a, [Card(9, D), Card(6, C)]), (b, [Card(10, C)])])
    game.table = [TableEntry(Card(6, H))]
    with pytest.raises(ValueError, match="illegal attack"):
        game._collect_attack(set())


def test_defender_may_stop_defending_midway_and_take_everything():
    a = Scripted("A", attacks=[Card(6, H), Card(6, D)])
    b = Scripted("B", defenses=[Card(10, H), None])
    game = make_game(
        [(a, [Card(6, H), Card(6, D), Card(12, S)]), (b, [Card(10, H), Card(9, D), Card(11, C)])]
    )
    game.play_bout()
    # Everything on the table is taken, including the card B already beat.
    for card in (Card(6, H), Card(10, H), Card(6, D)):
        assert card in b.hand
    assert game.discard == []


# ------------------------------------------------------ drawing and endings


def test_hands_refill_to_six_with_the_attacker_served_first():
    stock = [Card(6, C), Card(7, C), Card(8, C)]
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[Card(10, H)])
    game = make_game(
        [
            (a, [Card(6, H), Card(9, D), Card(10, D), Card(11, D), Card(12, D)]),
            (b, [Card(10, H), Card(9, H), Card(12, C), Card(13, C), Card(14, C)]),
        ],
        stock=stock,
    )
    game.play_bout()
    # Both are two cards short but only three are left: the attacker draws first.
    assert len(a.hand) == 6 and len(b.hand) == 5
    assert Card(6, C) in a.hand and Card(7, C) in a.hand and Card(8, C) in b.hand
    assert game.deck == []


def test_a_player_who_empties_their_hand_is_out_once_the_stock_is_gone():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[Card(10, H)])
    game = make_game([(a, [Card(6, H)]), (b, [Card(10, H), Card(9, C)])])
    game.play_bout()
    assert a in game.finished
    assert game.active == [b]


def test_the_last_player_holding_cards_is_the_durak():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[None])
    game = make_game([(a, [Card(6, H)]), (b, [Card(10, C)])])
    game.play_bout()
    assert game.active == [b]
    assert [p.name for p in game.finished] == ["A"]


def test_emptying_together_is_a_draw():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[Card(10, H)])
    game = make_game([(a, [Card(6, H)]), (b, [Card(10, H)])])
    game.play_bout()
    assert game.active == []


def test_observe_is_reported_to_every_player():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[None])
    game = make_game([(a, [Card(6, H), Card(9, C)]), (b, [Card(10, C)])])
    game.play_bout()
    assert a.observed == [(1, "B")] and b.observed == [(1, "B")]


# -------------------------------------------------------------------- setup


def test_the_lowest_trump_opens_the_game():
    players = [Scripted("A"), Scripted("B"), Scripted("C")]
    game = Durak(players, rng=random.Random(4))
    game.deal()
    trumps = [
        min((c.rank for c in p.hand if c.suit == game.trump), default=99) for p in players
    ]
    assert trumps.index(min(trumps)) == game.attacker_seat


def test_the_trump_card_is_the_bottom_of_the_stock():
    game = Durak([Scripted("A"), Scripted("B")], rng=random.Random(1))
    assert game.trump_card == game.deck[-1]
    assert game.trump == game.trump_card.suit
    game.deal()
    assert game.deck[-1] == game.trump_card  # still the very last card dealt


def test_player_count_and_deck_size_are_validated():
    with pytest.raises(ValueError):
        Durak([Scripted("A")])
    with pytest.raises(ValueError):
        Durak([Scripted(str(i)) for i in range(4)], deck_size=20)


# ---------------------------------------------------------- transfer mode


def transfer_game(hands, **kwargs):
    return make_game(hands, mode=TRANSFER, **kwargs)


def test_classic_mode_never_offers_a_transfer():
    a = Scripted("A")
    b = Scripted("B", defenses=[None])
    game = make_game([(a, [Card(6, H), Card(9, C)]), (b, [Card(6, D), Card(9, D)])])
    game.table = [TableEntry(Card(6, H))]
    assert game.receiver is None
    assert game.legal_transfers() == []


def test_a_matching_rank_may_be_passed_on():
    a = Scripted("A")
    b = Scripted("B")
    game = transfer_game([(a, [Card(9, C), Card(10, C)]), (b, [Card(6, D), Card(6, C), Card(9, D)])])
    game.table = [TableEntry(Card(6, H))]
    assert game.receiver is a
    assert set(game.legal_transfers()) == {Card(6, D), Card(6, C)}


def test_a_rank_you_do_not_hold_cannot_be_passed_on():
    a = Scripted("A")
    b = Scripted("B")
    game = transfer_game([(a, [Card(9, C), Card(10, C)]), (b, [Card(7, D), Card(9, D)])])
    game.table = [TableEntry(Card(6, H))]
    assert game.legal_transfers() == []


def test_beating_a_card_gives_up_the_right_to_pass():
    a = Scripted("A")
    b = Scripted("B")
    game = transfer_game([(a, [Card(9, C), Card(10, C)]), (b, [Card(6, D), Card(9, D)])])
    game.table = [TableEntry(Card(6, H), Card(7, H))]
    assert game.legal_transfers() == []


def test_you_cannot_pass_onto_somebody_who_holds_too_few_cards():
    a = Scripted("A")
    b = Scripted("B")
    # A would have to beat two cards but holds only one.
    game = transfer_game([(a, [Card(9, C)]), (b, [Card(6, D), Card(9, D)])])
    game.table = [TableEntry(Card(6, H))]
    assert game.legal_transfers() == []
    a.hand.append(Card(10, C))
    assert game.legal_transfers() == [Card(6, D)]


def test_with_two_players_the_attack_comes_straight_back():
    a = Scripted("A", attacks=[Card(6, H)], defenses=[Card(7, H), Card(7, D)])
    b = Scripted("B", defenses=[Transfer(Card(6, D))])
    game = transfer_game(
        [
            (a, [Card(6, H), Card(7, H), Card(7, D), Card(13, C)]),
            (b, [Card(6, D), Card(9, C), Card(10, C)]),
        ]
    )
    game.play_bout()
    # A had to beat both the card they attacked with and the one passed back.
    assert game.discard == [Card(6, H), Card(7, H), Card(6, D), Card(7, D)]
    assert a.hand == [Card(13, C)]
    assert b.hand == [Card(9, C), Card(10, C)]
    assert game.attacker is a  # A beat everything, so A attacks next


def test_the_passer_becomes_the_attacker_in_a_two_player_game():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[Transfer(Card(6, D))])
    game = transfer_game(
        [(a, [Card(6, H), Card(9, C), Card(10, C)]), (b, [Card(6, D), Card(9, D), Card(10, D)])]
    )
    game._collect_attack(set())  # A opens
    game.table.append(TableEntry(Card(6, H)))
    a.hand.remove(Card(6, H))
    game._respond(0)
    assert game.defender is a  # the attacker now has to defend
    assert game.attacker is b  # and the passer is the attacker
    assert len(game.table) == 2


def test_the_defence_rotates_clockwise_with_three_players():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[Transfer(Card(6, D))])
    c = Scripted("C", defenses=[Card(7, H), Card(7, D)])
    game = transfer_game(
        [
            (a, [Card(6, H), Card(12, C), Card(13, D)]),
            (b, [Card(6, D), Card(9, C), Card(10, C)]),
            (c, [Card(7, H), Card(7, D), Card(13, C)]),
        ]
    )
    game.play_bout()
    # B passed it to C, the next player clockwise, who beat both cards.
    assert game.discard == [Card(6, H), Card(7, H), Card(6, D), Card(7, D)]
    assert b.hand == [Card(9, C), Card(10, C)]
    assert c.hand == [Card(13, C)]
    assert game.attacker is c
    # C was offered no transfer on the second card: it had already beaten one.
    assert c.offered_transfers[-1] == []


def test_a_transfer_can_be_passed_on_again():
    a = Scripted("A", defenses=[None])
    b = Scripted("B", defenses=[Transfer(Card(6, D))])
    c = Scripted("C", defenses=[Transfer(Card(6, C))])
    a.attacks = [Card(6, H)]
    game = transfer_game(
        [
            (a, [Card(6, H), Card(12, C), Card(13, D), Card(14, D)]),
            (b, [Card(6, D), Card(9, C), Card(10, C)]),
            (c, [Card(6, C), Card(9, D), Card(10, D)]),
        ]
    )
    game.play_bout()
    # It went A -> B -> C -> A, and A could not beat all three.
    for card in (Card(6, H), Card(6, D), Card(6, C)):
        assert card in a.hand
    assert game.discard == []
    assert b.hand == [Card(9, C), Card(10, C)]
    assert c.hand == [Card(9, D), Card(10, D)]


def test_the_new_defender_faces_every_card_at_once():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[Transfer(Card(6, D))])
    game = transfer_game(
        [
            (a, [Card(6, H), Card(9, C), Card(10, C)]),
            (b, [Card(6, D), Card(9, D), Card(10, D)]),
        ]
    )
    game.play_bout()
    # A cannot beat either six, so A picks both up.
    assert sorted(a.hand) == sorted([Card(9, C), Card(10, C), Card(6, H), Card(6, D)])
    assert game.discard == []


def test_a_passed_on_bout_is_settled_against_the_final_defender():
    a = Scripted("A", attacks=[Card(6, H)])
    b = Scripted("B", defenses=[Transfer(Card(6, D))])
    c = Scripted("C", defenses=[None])
    game = transfer_game(
        [
            (a, [Card(6, H), Card(12, C), Card(13, D)]),
            (b, [Card(6, D), Card(9, C), Card(10, C)]),
            (c, [Card(9, S), Card(10, S), Card(13, C)]),
        ]
    )
    game.play_bout()
    # C took, so the player after C attacks next.
    assert Card(6, H) in c.hand and Card(6, D) in c.hand
    assert game.attacker is a and game.defender is b


# ------------------------------------------------------------ bigger tables


@pytest.mark.parametrize("count", [2, 3, 4, 5, 6])
def test_the_engine_seats_two_to_six(count):
    players = [Scripted(f"p{i}") for i in range(count)]
    game = Durak(players, rng=random.Random(0), deck_size=52)
    game.deal()
    assert len(game.active) == count
    assert all(len(p.hand) == 6 for p in players)
    assert game.deck  # a stock is left over


def test_seven_players_are_refused():
    with pytest.raises(ValueError):
        Durak([Scripted(str(i)) for i in range(7)], deck_size=52)


def test_the_attack_passes_round_a_full_table():
    """Every seat gets a turn to attack, in order, as bouts are beaten off."""
    players = [Scripted(f"p{i}") for i in range(6)]
    game = Durak(players, rng=random.Random(0), deck_size=52)
    game.attacker_seat = 0
    seen = []
    for _ in range(6):
        seen.append(game.attacker_seat)
        # Beating off the attack hands it to the defender, i.e. the next seat.
        game.attacker_seat = game.defender_seat
        game.defender_seat = game._next_seat(game.attacker_seat)
    assert seen == [0, 1, 2, 3, 4, 5]


def test_everybody_but_the_defender_may_throw_in_at_a_full_table():
    players = [Scripted(f"p{i}") for i in range(6)]
    game = Durak(players, rng=random.Random(0), deck_size=52)
    game.attacker_seat, game.defender_seat = 0, 1
    order = game.attack_order()
    assert game.defender not in order
    assert len(order) == 5
    assert order[0] is game.attacker  # the attacker still goes first


def test_a_finished_player_is_skipped_when_the_turn_comes_round():
    players = [Scripted(f"p{i}") for i in range(6)]
    game = Durak(players, rng=random.Random(0), deck_size=52)
    game.finished = [players[1], players[2]]
    assert game._next_seat(0) == 3
    game.attacker_seat, game.defender_seat = 0, 3
    assert players[1] not in game.attack_order()
    assert players[2] not in game.attack_order()


def test_a_transfer_at_a_full_table_goes_to_the_next_live_seat():
    players = [Scripted(f"p{i}") for i in range(6)]
    game = Durak(players, rng=random.Random(0), deck_size=52, mode=TRANSFER)
    for player in players:
        player.hand = [Card(9, C), Card(10, C), Card(11, C)]
    game.attacker_seat, game.defender_seat = 0, 1
    game.table = [TableEntry(Card(6, H))]
    players[1].hand = [Card(6, D), Card(9, C)]
    assert game.receiver is players[2]
    game._pass_the_attack(Card(6, D))
    assert game.defender is players[2]
    assert game.attacker is players[0]  # unchanged: it did not wrap round
