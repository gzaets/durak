"""Tests for rendering, input parsing and the command line entry point."""

from __future__ import annotations

import io
import random

import pytest

from durak import cli, render, tutorial
from durak.ai import AIPlayer
from durak.cards import Card
from durak.engine import Durak, TableEntry, Transfer
from durak.players import QuitGame
from durak.render import Style
from durak.ui import TerminalUI

S, H, D, C = "S", "H", "D", "C"


def a_view(hand, trump=S, table=()):
    """A GameView built from a real game, so it stays in sync with the engine."""
    you = AIPlayer("You", "normal")
    them = AIPlayer("Ivan", "normal")
    game = Durak([you, them], rng=random.Random(0))
    game.trump = trump
    you.hand = list(hand)
    them.hand = [Card(9, C)]
    game.table = list(table)
    return game.view_for(you)


class ScriptedUI(TerminalUI):
    """A UI that answers its own prompts and throws away the drawing."""

    def __init__(self, commands, **kwargs):
        kwargs.setdefault("style", Style(color=False))
        kwargs.setdefault("clear", False)
        super().__init__(**kwargs)
        self.commands = list(commands)
        self.frames = 0
        self.last_note = ""

    def draw(self, view, legal=(), note=""):
        self.frames += 1
        self.last_note = note

    def write(self, text):
        pass

    def _read(self, prompt=""):
        if not self.commands:
            raise QuitGame
        return self.commands.pop(0)


# ------------------------------------------------------------------ drawing


def test_a_card_renders_as_a_box_of_the_right_size():
    art = render.card_art(Card(10, H), Style(color=False))
    assert len(art) == render.CARD_HEIGHT
    assert all(len(line) == render.CARD_WIDTH for line in art)
    assert "10" in art[1] and "♥" in art[2]


def test_ascii_mode_uses_no_box_drawing_characters():
    art = render.card_art(Card(14, S), Style(color=False, ascii_only=True))
    joined = "\n".join(art)
    assert joined.isascii()
    assert "+" in joined and "A" in joined and "S" in joined


def test_a_wide_hand_wraps_onto_several_rows():
    cards = [Card(r, H) for r in range(6, 15)]
    narrow = render.hand_art(cards, Style(color=False), width=40)
    wide = render.hand_art(cards, Style(color=False), width=200)
    assert len(narrow) > len(wide)


def test_unplayable_cards_lose_their_number():
    cards = [Card(6, H), Card(7, H)]
    lines = render.hand_art(
        cards,
        Style(color=False),
        labels=["1", "2"],
        playable=[True, False],
        width=200,
    )
    caption = lines[-1]
    assert "1" in caption and "2" not in caption


def test_the_table_shows_defences_under_their_attacks():
    entries = [TableEntry(Card(6, H), Card(10, H)), TableEntry(Card(7, D))]
    lines = "\n".join(render.table_art(entries, Style(color=False)))
    assert "10" in lines and "6" in lines and "7" in lines


def test_colour_can_be_switched_off():
    plain = Style(color=False).card_label(Card(6, H))
    coloured = Style(color=True).card_label(Card(6, H))
    assert "\033" not in plain
    assert "\033" in coloured


def test_ansi_codes_do_not_count_towards_padding():
    coloured = Style(color=True).paint("abc", render.RED)
    assert render._visible_len(coloured) == 3
    assert render.pad(coloured, 6).endswith("   ")


def test_to_ascii_transliterates_suits_and_dashes():
    assert render.to_ascii("6♥ — 7♠") == "6H - 7S"
    assert render.to_ascii("plain").isascii()


# ------------------------------------------------------------ input parsing


def test_picking_a_number_plays_that_card():
    hand = [Card(6, H), Card(9, D), Card(14, S)]
    ui = ScriptedUI(["2"])
    assert ui.ask_attack(a_view(hand), list(hand), initial=True) == Card(9, D)


def test_an_out_of_range_number_is_rejected_and_re_asked():
    hand = [Card(6, H), Card(9, D)]
    ui = ScriptedUI(["9", "1"])
    assert ui.ask_attack(a_view(hand), list(hand), initial=True) == Card(6, H)


def test_nonsense_input_is_rejected_and_re_asked():
    hand = [Card(6, H), Card(9, D)]
    ui = ScriptedUI(["banana", "2"])
    assert ui.ask_attack(a_view(hand), list(hand), initial=True) == Card(9, D)


def test_a_card_that_is_not_a_legal_throw_in_is_refused():
    hand = [Card(6, H), Card(9, D)]
    view = a_view(hand, table=[TableEntry(Card(6, S))])
    ui = ScriptedUI(["2", "1"])  # the 9 does not match the table, the 6 does
    assert ui.ask_attack(view, [Card(6, H)], initial=False) == Card(6, H)


def test_enter_passes_on_a_throw_in():
    hand = [Card(6, H)]
    view = a_view(hand, table=[TableEntry(Card(6, S))])
    assert ScriptedUI([""]).ask_attack(view, [Card(6, H)], initial=False) is None


def test_the_opening_attack_cannot_be_passed():
    hand = [Card(6, H), Card(9, D)]
    ui = ScriptedUI(["", "d", "1"])
    assert ui.ask_attack(a_view(hand), list(hand), initial=True) == Card(6, H)


def test_t_takes_the_cards():
    hand = [Card(10, H)]
    view = a_view(hand, table=[TableEntry(Card(6, H))])
    assert ScriptedUI(["t"]).ask_defense(view, Card(6, H), [Card(10, H)]) is None


def test_defending_picks_the_chosen_card():
    hand = [Card(10, H), Card(14, S)]
    view = a_view(hand, table=[TableEntry(Card(6, H))])
    ui = ScriptedUI(["1"])
    assert ui.ask_defense(view, Card(6, H), [Card(10, H), Card(14, S)]) == Card(10, H)


def test_a_card_that_cannot_beat_the_attack_is_refused():
    hand = [Card(6, D), Card(10, H)]
    view = a_view(hand, table=[TableEntry(Card(9, H))])
    ui = ScriptedUI(["1", "2"])  # the 6 of diamonds cannot beat the 9 of hearts
    assert ui.ask_defense(view, Card(9, H), [Card(10, H)]) == Card(10, H)


def test_q_quits_from_any_prompt():
    hand = [Card(6, H)]
    with pytest.raises(QuitGame):
        ScriptedUI(["q"]).ask_attack(a_view(hand), list(hand), initial=True)
    with pytest.raises(QuitGame):
        ScriptedUI(["quit"]).ask_defense(a_view(hand), Card(6, S), list(hand))


def test_running_out_of_input_quits_cleanly():
    hand = [Card(6, H)]
    with pytest.raises(QuitGame):
        ScriptedUI([]).ask_attack(a_view(hand), list(hand), initial=True)


def test_help_and_hints_redraw_without_consuming_the_turn():
    hand = [Card(6, H), Card(9, D)]
    ui = ScriptedUI(["?", "", "s", "2"])  # help, dismiss, hint, then play
    assert ui.ask_attack(a_view(hand), list(hand), initial=True) == Card(9, D)


def test_second_person_fixes_the_log_grammar():
    ui = ScriptedUI([])
    assert ui._second_person("You takes the cards.", "You") == "You take the cards."
    assert ui._second_person("Ivan takes the cards.", "You") == "Ivan takes the cards."
    # A real name is already correct in the third person.
    assert ui._second_person("Sam takes the cards.", "Sam") == "Sam takes the cards."


# --------------------------------------------------------------------- cli


def test_simulate_mode_prints_a_tally(capsys):
    assert cli.main(["--simulate", "5", "--seed", "1"]) == 0
    out = capsys.readouterr().out
    assert "5 games" in out and "durak" in out


def test_bad_player_count_is_rejected():
    with pytest.raises(SystemExit):
        cli.main(["--players", "9"])


def test_the_human_is_not_always_seated_first():
    rng = random.Random(0)
    seats = set()
    for _ in range(20):
        human = AIPlayer("You", "normal")
        bots = [AIPlayer("A", "normal"), AIPlayer("B", "normal")]
        seats.add(cli.seat_players(human, bots, rng).index(human))
    assert len(seats) > 1


def test_opponents_never_reuse_the_players_name():
    rng = random.Random(0)
    bots = cli.make_opponents(3, "normal", rng, taken="Ivan")
    assert "Ivan" not in {b.name for b in bots}
    assert len({b.name for b in bots}) == 3


@pytest.mark.parametrize("players", [2, 3, 4])
def test_a_whole_game_can_be_played_through_stdin(monkeypatch, capsys, players):
    # "1" is always legal as an opening attack; a bare newline passes a throw-in
    # and takes on defence, so this stream can never get stuck.
    monkeypatch.setattr("sys.stdin", io.StringIO("1\n\n" * 3000))
    code = cli.main(
        [
            "--players", str(players),
            "--rounds", "1",
            "--speed", "0",
            "--no-clear",
            "--no-color",
            "--seed", "7",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "DURAK" in out
    assert "Bouts played:" in out


# ------------------------------------------------------------ transfer mode


def transfer_view(hand, table, trump=S, receiver="Ivan"):
    view = a_view(hand, trump=trump, table=table)
    view.mode = "transfer"
    view.receiver = receiver
    return view


def test_a_number_that_can_only_pass_the_attack_on_passes_it():
    hand = [Card(6, D), Card(10, C)]
    view = transfer_view(hand, [TableEntry(Card(6, H))])
    ui = ScriptedUI(["1"])
    assert ui.ask_defense(view, Card(6, H), [], [Card(6, D)]) == Transfer(Card(6, D))


def test_a_number_that_can_only_beat_still_beats():
    hand = [Card(6, D), Card(10, H)]
    view = transfer_view(hand, [TableEntry(Card(6, H))])
    ui = ScriptedUI(["2"])
    assert ui.ask_defense(view, Card(6, H), [Card(10, H)], [Card(6, D)]) == Card(10, H)


def test_a_card_that_could_do_either_has_to_be_spelled_out():
    # The six of trumps beats the six of hearts and is also a legal transfer.
    hand = [Card(6, S), Card(10, C)]
    view = transfer_view(hand, [TableEntry(Card(6, H))])
    ui = ScriptedUI(["1", "b1"])
    assert ui.ask_defense(view, Card(6, H), [Card(6, S)], [Card(6, S)]) == Card(6, S)
    assert "can beat it or pass it on" in ui.last_note

    ui = ScriptedUI(["1", "p1"])
    move = ui.ask_defense(view, Card(6, H), [Card(6, S)], [Card(6, S)])
    assert move == Transfer(Card(6, S))


def test_a_bare_p_works_when_only_one_card_could_pass():
    hand = [Card(6, D), Card(10, C)]
    view = transfer_view(hand, [TableEntry(Card(6, H))])
    ui = ScriptedUI(["p"])
    assert ui.ask_defense(view, Card(6, H), [], [Card(6, D)]) == Transfer(Card(6, D))


def test_a_bare_p_asks_which_when_several_cards_could_pass():
    hand = [Card(6, D), Card(6, C)]
    view = transfer_view(hand, [TableEntry(Card(6, H))])
    ui = ScriptedUI(["p", "p2"])
    move = ui.ask_defense(view, Card(6, H), [], [Card(6, D), Card(6, C)])
    assert move == Transfer(Card(6, C))
    assert "Add its number" in ui.last_note


def test_taking_still_works_when_a_transfer_is_on_offer():
    hand = [Card(6, D)]
    view = transfer_view(hand, [TableEntry(Card(6, H))])
    assert ScriptedUI(["t"]).ask_defense(view, Card(6, H), [], [Card(6, D)]) is None


def test_the_prompt_names_who_the_attack_would_go_to():
    hand = [Card(6, D)]
    view = transfer_view(hand, [TableEntry(Card(6, H))], receiver="Olga")
    ui = ScriptedUI(["t"])
    ui.ask_defense(view, Card(6, H), [], [Card(6, D)])
    assert "pass to" in ui.last_note and "Olga" in ui.last_note


def test_classic_mode_never_shows_the_pass_option():
    hand = [Card(10, H)]
    view = a_view(hand, table=[TableEntry(Card(6, H))])
    ui = ScriptedUI(["1"])
    ui.ask_defense(view, Card(6, H), [Card(10, H)], [])
    assert "pass to" not in ui.last_note


# ------------------------------------------------------------- setup screen


def test_the_setup_menu_returns_the_chosen_value():
    ui = ScriptedUI(["2"])
    options = [("classic", "Classic", "..."), ("transfer", "Transfer", "...")]
    assert ui.ask_choice("Game mode", options) == "transfer"


def test_the_setup_menu_falls_back_to_the_default_on_enter():
    ui = ScriptedUI([""])
    options = [("classic", "Classic", "..."), ("transfer", "Transfer", "...")]
    assert ui.ask_choice("Game mode", options, default=1) == "transfer"


def test_the_setup_menu_re_asks_on_nonsense():
    ui = ScriptedUI(["banana", "9", "1"])
    options = [("classic", "Classic", "..."), ("transfer", "Transfer", "...")]
    assert ui.ask_choice("Game mode", options) == "classic"


def test_quitting_the_setup_menu_leaves_the_game():
    with pytest.raises(QuitGame):
        ScriptedUI(["q"]).ask_choice("Game mode", [("a", "A", ""), ("b", "B", "")])


# --------------------------------------------------------- modes and setup


@pytest.mark.parametrize(
    "text,expected",
    [
        ("classic", "classic"),
        ("Traditional", "classic"),
        ("transfer", "transfer"),
        ("perevodnoy", "transfer"),
        ("podkidnoy", "transfer"),
        ("throw-in", "transfer"),
        ("Throw In", "transfer"),
    ],
)
def test_every_name_people_use_for_the_modes_is_accepted(text, expected):
    assert cli.parse_mode(text) == expected


def test_an_unknown_mode_name_is_rejected():
    with pytest.raises(Exception):
        cli.parse_mode("bridge")


def test_opponents_and_players_are_two_ways_of_saying_the_same_thing():
    parser = cli.build_parser()
    args = parser.parse_args(["--opponents", "3"])
    cli.resolve_table_size(args, parser)
    assert args.players == 4


def test_contradicting_opponents_and_players_is_an_error():
    parser = cli.build_parser()
    args = parser.parse_args(["--opponents", "3", "--players", "2"])
    with pytest.raises(SystemExit):
        cli.resolve_table_size(args, parser)


def test_agreeing_opponents_and_players_are_fine():
    parser = cli.build_parser()
    args = parser.parse_args(["--opponents", "3", "--players", "4"])
    cli.resolve_table_size(args, parser)
    assert args.players == 4


def test_setup_asks_for_everything_that_was_not_given():
    args = cli.build_parser().parse_args([])
    ui = ScriptedUI(["2", "3", "3"])  # transfer, 3 opponents, hard
    cli.run_setup(ui, args)
    assert (args.mode, args.players, args.difficulty) == ("transfer", 4, "hard")


def test_setup_skips_whatever_the_flags_already_settled():
    args = cli.build_parser().parse_args(["--mode", "transfer", "--opponents", "2"])
    cli.resolve_table_size(args, cli.build_parser())
    ui = ScriptedUI(["1"])  # only difficulty is still open
    cli.run_setup(ui, args)
    assert (args.mode, args.players, args.difficulty) == ("transfer", 3, "easy")
    assert not ui.commands  # exactly one question was asked


def test_setup_is_skipped_when_nothing_is_attached_to_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert cli.main(["--simulate", "3", "--seed", "1"]) == 0
    assert "classic mode" in capsys.readouterr().out


def test_simulate_reports_the_mode(capsys):
    assert cli.main(["--simulate", "3", "--mode", "podkidnoy", "--seed", "1"]) == 0
    assert "transfer mode" in capsys.readouterr().out


@pytest.mark.parametrize("players", [2, 3, 4])
def test_a_whole_transfer_game_can_be_played_through_stdin(monkeypatch, capsys, players):
    monkeypatch.setattr("sys.stdin", io.StringIO("1\n\n" * 3000))
    code = cli.main(
        [
            "--players", str(players),
            "--mode", "transfer",
            "--rounds", "1",
            "--speed", "0",
            "--no-clear",
            "--no-color",
            "--seed", "13",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "DURAK" in out and "Bouts played:" in out
    assert "transfer mode" in out


# ---------------------------------------------------- trump colour and order


def test_a_trump_is_outlined_in_cyan():
    style = Style(color=True, trump=H)
    art = "\n".join(render.card_art(Card(10, H), style))
    assert render.CYAN in art


def test_a_plain_card_is_not_outlined_in_cyan():
    style = Style(color=True, trump=H)
    for card in (Card(10, D), Card(10, S)):
        assert render.CYAN not in "\n".join(render.card_art(card, style))


def test_a_trump_keeps_its_suit_colour_inside_the_cyan_outline():
    """A red trump is still recognisably red: only the outline turns cyan."""
    style = Style(color=True, trump=H)
    art = render.card_art(Card(10, H), style)
    border, pip = art[0], art[2]
    assert render.CYAN in border and render.RED not in border
    assert render.RED in pip


def test_the_same_card_is_only_cyan_when_it_is_trump():
    plain = "\n".join(render.card_art(Card(10, H), Style(color=True, trump=S)))
    trump = "\n".join(render.card_art(Card(10, H), Style(color=True, trump=H)))
    assert render.CYAN not in plain and render.CYAN in trump


def test_trump_colouring_switches_off_with_colour():
    art = "\n".join(render.card_art(Card(10, H), Style(color=False, trump=H)))
    assert "\033" not in art


def test_cards_keep_their_shape_whether_or_not_they_are_trump():
    for style in (Style(color=True, trump=H), Style(color=True, trump=S)):
        art = render.card_art(Card(10, H), style)
        assert len(art) == render.CARD_HEIGHT
        assert all(render._visible_len(line) == render.CARD_WIDTH for line in art)


def test_a_one_line_card_label_is_cyan_for_a_trump():
    style = Style(color=True, trump=H)
    assert render.CYAN in style.card_label(Card(10, H))
    assert render.CYAN not in style.card_label(Card(10, D))


def test_the_ui_picks_up_the_trump_when_a_game_starts():
    ui = ScriptedUI([])
    assert ui.style.trump is None
    bots = [AIPlayer("a", "normal"), AIPlayer("b", "normal")]
    game = Durak(bots, rng=random.Random(0))
    ui.attach(game, bots[0])
    assert ui.style.trump == game.trump


def test_cyrillic_survives_ascii_mode():
    assert render.to_ascii("дурак") == "durak"
    assert render.to_ascii("Дурак").lower() == "durak"


# ------------------------------------------------------- tutorial and menu


def test_the_tutorial_covers_the_rules_it_needs_to():
    body = tutorial.text().lower()
    for topic in ("trump", "beat", "throw", "transfer", "durak", "history"):
        assert topic in body


def test_the_tutorial_is_paged_rather_than_dumped():
    assert len(tutorial.SECTIONS) > 1
    assert all(section.strip() for section in tutorial.SECTIONS)


def test_the_tutorial_survives_ascii_mode():
    assert render.to_ascii(tutorial.text()).isascii()


def test_the_tutorial_flag_prints_and_exits(capsys):
    assert cli.main(["--tutorial"]) == 0
    assert "Durak" in capsys.readouterr().out


def test_paging_stops_early_when_asked():
    ui = ScriptedUI(["", "q"])
    ui.show_pages(["one", "two", "three", "four"])
    assert not ui.commands  # it stopped at the q rather than reading on


def test_paging_walks_every_page_to_the_end():
    ui = ScriptedUI(["", "", ""])
    ui.show_pages(["one", "two", "three"])  # 2 gaps, then the closing prompt
    assert not ui.commands


def test_the_menu_starts_a_game():
    ui = ScriptedUI(["1"])
    cli.main_menu(ui)  # returns rather than raising


def test_the_menu_quits():
    with pytest.raises(QuitGame):
        cli.main_menu(ScriptedUI(["3"]))


def test_the_menu_shows_the_tutorial_then_comes_back():
    # 2 = how to play, then page through, then 1 = play.
    ui = ScriptedUI(["2"] + [""] * len(tutorial.SECTIONS) + ["1"])
    cli.main_menu(ui)
    assert not ui.commands


# --------------------------------------------------------- bigger tables


@pytest.mark.parametrize("players,deck", [(2, 36), (3, 36), (4, 36), (5, 36), (6, 52)])
def test_the_default_deck_seats_everyone_and_leaves_a_stock(players, deck):
    assert cli.default_deck_for(players) == deck
    assert deck >= players * 6 + 1


def test_the_standard_deck_is_preferred_while_it_still_fits():
    # Two players would fit in 20 cards, but Durak is a 36 card game.
    assert cli.default_deck_for(2) == cli.DEFAULT_DECK


@pytest.mark.parametrize("opponents", [1, 2, 3, 4, 5])
def test_up_to_five_opponents_can_be_asked_for(opponents):
    parser = cli.build_parser()
    args = parser.parse_args(["--opponents", str(opponents)])
    cli.resolve_table_size(args, parser)
    assert args.players == opponents + 1


def test_seven_players_is_still_refused():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--players", "7"])
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--opponents", "6"])


def test_there_is_always_a_spare_name_for_a_full_table():
    rng = random.Random(0)
    for taken in ("You", "Ivan", "Misha"):
        bots = cli.make_opponents(5, "normal", rng, taken=taken)
        assert len(bots) == 5
        assert len({b.name for b in bots}) == 5
        assert taken not in {b.name for b in bots}


def test_six_players_are_told_which_deck_they_need():
    assert "52" in cli._table_blurb(6)
    assert "52" not in cli._table_blurb(4)


def test_a_deck_too_small_for_six_names_the_one_that_works(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--players", "6", "--deck", "36", "-y"])
    assert "try --deck 52" in capsys.readouterr().err


def test_the_counting_bot_is_told_the_real_deck_size():
    """A 52 card game must not leave the hard bot modelling 36 cards."""
    rng = random.Random(0)
    bots = cli.make_opponents(2, "hard", rng, taken="You", deck_size=52)
    assert all(len(b._full_deck) == 52 for b in bots)


@pytest.mark.parametrize("players", [5, 6])
@pytest.mark.parametrize("mode", ["classic", "transfer"])
def test_a_whole_big_table_game_can_be_played_through_stdin(
    monkeypatch, capsys, players, mode
):
    monkeypatch.setattr("sys.stdin", io.StringIO("1\n\n" * 6000))
    code = cli.main(
        [
            "--players", str(players),
            "--mode", mode,
            "--rounds", "1",
            "--speed", "0",
            "--no-clear",
            "--no-color",
            "--seed", "21",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "DURAK" in out and "Bouts played:" in out
