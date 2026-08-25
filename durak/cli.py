"""Command line front end: argument parsing and the match loop."""

from __future__ import annotations

import argparse
import random
import sys
from typing import Optional, Sequence

from .ai import DIFFICULTIES, AIPlayer
from .cards import DECK_SIZES
from .engine import CLASSIC, HAND_SIZE, TRANSFER, Durak, GameResult
from .players import HumanPlayer, QuitGame
from .tutorial import SECTIONS as TUTORIAL_SECTIONS, text as tutorial_text
from .render import Style
from .ui import TerminalUI

# What the user may type for each mode. "Podkidnoy" and "throw-in" are listed
# for transfer because that is what many players call it, even though strictly
# podkidnoy is the throwing-in of matching ranks, which both modes allow, and
# the transfer variant is perevodnoy.
MODE_ALIASES = {
    "classic": CLASSIC,
    "traditional": CLASSIC,
    "basic": CLASSIC,
    "transfer": TRANSFER,
    "perevodnoy": TRANSFER,
    "podkidnoy": TRANSFER,
    "throw-in": TRANSFER,
    "throwin": TRANSFER,
}

MODE_BLURB = {
    CLASSIC: "the defender must beat every card or take them all",
    TRANSFER: "the defender may also pass the attack on with a matching rank",
}

BOT_NAMES = [
    "Ivan",
    "Olga",
    "Pyotr",
    "Nadya",
    "Grisha",
    "Vera",
]


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """Shows defaults, but stays quiet about the options that get asked for."""

    def _get_help_string(self, action):
        if action.default is None:
            return action.help
        return super()._get_help_string(action)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="durak",
        description="Play Durak against the computer in your terminal.",
        formatter_class=HelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--players",
        type=int,
        default=None,
        choices=range(2, 5),
        metavar="{2,3,4}",
        help="total number of players, you included (asked if omitted)",
    )
    parser.add_argument(
        "-o",
        "--opponents",
        type=int,
        default=None,
        choices=range(1, 4),
        metavar="{1,2,3}",
        help="number of computer opponents (an alternative to --players)",
    )
    parser.add_argument(
        "-m",
        "--mode",
        type=parse_mode,
        default=None,
        metavar="{classic,transfer}",
        help="classic, or transfer (aka perevodnoy): pass the attack on (asked if omitted)",
    )
    parser.add_argument("-n", "--name", default="You", help="your name at the table")
    parser.add_argument(
        "-d",
        "--difficulty",
        default=None,
        choices=DIFFICULTIES,
        help="how well the computer opponents play (asked if omitted)",
    )
    parser.add_argument(
        "--tutorial",
        action="store_true",
        help="print the rules and history, then exit",
    )
    parser.add_argument(
        "-y",
        "--defaults",
        action="store_true",
        help="skip the setup questions and use the defaults for anything not given",
    )
    parser.add_argument(
        "--deck",
        type=int,
        default=36,
        choices=DECK_SIZES,
        help="deck size (36 is the standard Durak deck)",
    )
    parser.add_argument("--seed", type=int, default=None, help="seed for a reproducible shuffle")
    parser.add_argument(
        "--speed",
        type=float,
        default=0.6,
        help="seconds to pause on each opponent move (0 for no pauses)",
    )
    parser.add_argument("--ascii", action="store_true", help="pure ASCII, no box drawing or suit glyphs")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    parser.add_argument("--no-clear", action="store_true", help="scroll instead of redrawing the screen")
    parser.add_argument(
        "--compact",
        action="store_true",
        help="one-line cards instead of card art (good for short terminals)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=0,
        help="play exactly N games then stop (0 asks after every game)",
    )
    parser.add_argument(
        "--simulate",
        type=int,
        default=0,
        metavar="N",
        help="play N games bot-vs-bot with no UI and print the tally",
    )
    return parser


def parse_mode(text: str) -> str:
    """Accept every name people use for the two modes."""
    key = text.strip().lower().replace("_", "-").replace(" ", "-")
    if key not in MODE_ALIASES:
        raise argparse.ArgumentTypeError(
            f"unknown mode {text!r}; choose classic or transfer"
        )
    return MODE_ALIASES[key]


DEFAULTS = {"players": 2, "difficulty": "normal", "mode": CLASSIC}


def resolve_table_size(args, parser) -> None:
    """Settle --players against --opponents; either may be given, not both."""
    if args.opponents is not None:
        implied = args.opponents + 1
        if args.players is not None and args.players != implied:
            parser.error(
                f"--players {args.players} and --opponents {args.opponents} disagree; "
                f"{args.opponents} opponents means {implied} players"
            )
        args.players = implied


def main_menu(ui: TerminalUI) -> None:
    """Show the front menu until the player chooses to start a game."""
    while True:
        choice = ui.ask_choice(
            "Durak",
            [
                ("play", "Play", "set up a game and deal"),
                ("learn", "How to play", "the rules, and where the game comes from"),
                ("quit", "Quit", "leave"),
            ],
        )
        if choice == "play":
            return
        if choice == "quit":
            raise QuitGame
        ui.show_pages(TUTORIAL_SECTIONS, footer="That is all of it — good luck.")


def run_setup(ui: TerminalUI, args) -> None:
    """Ask about anything the command line did not already settle."""
    if args.mode is None:
        args.mode = ui.ask_choice(
            "Game mode",
            [
                (CLASSIC, "Classic", MODE_BLURB[CLASSIC]),
                (TRANSFER, "Transfer", MODE_BLURB[TRANSFER]),
            ],
        )
    if args.players is None:
        args.players = ui.ask_choice(
            "How many opponents?",
            [(n + 1, f"{n} opponent{'s' if n > 1 else ''}", f"{n + 1} at the table")
             for n in (1, 2, 3)],
        )
    if args.difficulty is None:
        args.difficulty = ui.ask_choice(
            "Difficulty",
            [
                ("easy", "Easy", "plays more or less at random"),
                ("normal", "Normal", "sheds cheap cards and hoards trumps"),
                ("hard", "Hard", "also counts the beaten pile"),
            ],
            default=1,
        )


def make_opponents(count: int, difficulty: str, rng: random.Random, taken: str) -> list[AIPlayer]:
    names = [n for n in BOT_NAMES if n.lower() != taken.lower()]
    rng.shuffle(names)
    return [AIPlayer(names[i], difficulty, rng) for i in range(count)]


def seat_players(human, bots, rng: random.Random) -> list:
    """Drop the human into a random seat so they do not always lead."""
    seats = list(bots)
    seats.insert(rng.randrange(len(seats) + 1), human)
    return seats


def play_one_game(args, ui: TerminalUI, rng: random.Random) -> GameResult:
    human = HumanPlayer(args.name, ui)
    bots = make_opponents(args.players - 1, args.difficulty, rng, taken=args.name)
    players = seat_players(human, bots, rng)
    game = Durak(
        players, rng=rng, deck_size=args.deck, log_sink=ui.event, mode=args.mode
    )
    ui.attach(game, human)
    result = game.run()
    if result.durak:
        ui.scores[result.durak] = ui.scores.get(result.durak, 0) + 1
    ui.announce(result, game.view_for(human))
    return result


def simulate(args, rng: random.Random) -> int:
    """Bot-vs-bot batch mode — handy for sanity checking the rules and the AI."""
    tally: dict[str, int] = {}
    draws = 0
    for _ in range(args.simulate):
        players = [
            AIPlayer(f"bot{i + 1}", args.difficulty, rng) for i in range(args.players)
        ]
        result = Durak(players, rng=rng, deck_size=args.deck, mode=args.mode).run()
        if result.durak is None:
            draws += 1
        else:
            tally[result.durak] = tally.get(result.durak, 0) + 1
    print(
        f"{args.simulate} games, {args.players} players, "
        f"difficulty {args.difficulty}, {args.mode} mode"
    )
    for name in sorted(tally):
        share = 100 * tally[name] / args.simulate
        print(f"  {name}: durak {tally[name]:>5} times ({share:5.1f}%)")
    if draws:
        print(f"  draws: {draws}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    rng = random.Random(args.seed)
    resolve_table_size(args, parser)

    if args.tutorial:
        print(tutorial_text())
        return 0

    style = Style.detect(color=False if args.no_color else None, ascii_only=args.ascii)
    ui = TerminalUI(
        style=style,
        speed=args.speed,
        clear=not args.no_clear,
        compact=True if args.compact else None,
    )

    try:
        # Ask about whatever was not given on the command line, unless there is
        # nobody at the keyboard to ask.
        if not args.simulate and not args.defaults and sys.stdin.isatty():
            ui.splash("A Russian card game for 2 to 4 — last one holding cards loses")
            main_menu(ui)
            ui.splash("Set up your game")
            run_setup(ui, args)
        for field, value in DEFAULTS.items():
            if getattr(args, field) is None:
                setattr(args, field, value)

        needed = args.players * HAND_SIZE + 1
        if args.deck < needed:
            parser.error(
                f"--deck {args.deck} is too small for {args.players} players "
                f"(need at least {needed} cards); try --deck 36"
            )
        if args.simulate:
            return simulate(args, rng)

        ui.splash(
            f"{args.players} players · {args.difficulty} opponents · "
            f"{args.mode} mode · {args.deck} card deck   (? for help once you are in)"
        )

        played = 0
        while True:
            play_one_game(args, ui, rng)
            played += 1
            if args.rounds and played >= args.rounds:
                break
            ui.write("\n")
            if not ui.ask_yes_no("Another game?"):
                break
    except QuitGame:
        ui.write("\n  Bye.\n")
        return 0
    except KeyboardInterrupt:  # pragma: no cover
        ui.write("\n  Bye.\n")
        return 130
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
