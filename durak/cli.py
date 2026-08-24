"""Command line front end: argument parsing and the match loop."""

from __future__ import annotations

import argparse
import random
import sys
from typing import Optional, Sequence

from .ai import DIFFICULTIES, AIPlayer
from .cards import DECK_SIZES
from .engine import HAND_SIZE, Durak, GameResult
from .players import HumanPlayer, QuitGame
from .render import Style
from .ui import TerminalUI

BOT_NAMES = [
    "Ivan",
    "Olga",
    "Pyotr",
    "Nadya",
    "Grisha",
    "Vera",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="durak",
        description="Play Durak against the computer in your terminal.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--players",
        type=int,
        default=2,
        choices=range(2, 5),
        metavar="{2,3,4}",
        help="total number of players, you included",
    )
    parser.add_argument("-n", "--name", default="You", help="your name at the table")
    parser.add_argument(
        "-d",
        "--difficulty",
        default="normal",
        choices=DIFFICULTIES,
        help="how well the computer opponents play",
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
    game = Durak(players, rng=rng, deck_size=args.deck, log_sink=ui.event)
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
        result = Durak(players, rng=rng, deck_size=args.deck).run()
        if result.durak is None:
            draws += 1
        else:
            tally[result.durak] = tally.get(result.durak, 0) + 1
    print(f"{args.simulate} games, {args.players} players, difficulty {args.difficulty}")
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

    needed = args.players * HAND_SIZE + 1
    if args.deck < needed:
        parser.error(
            f"--deck {args.deck} is too small for {args.players} players "
            f"(need at least {needed} cards); try --deck 36"
        )

    if args.simulate:
        return simulate(args, rng)

    style = Style.detect(color=False if args.no_color else None, ascii_only=args.ascii)
    ui = TerminalUI(
        style=style,
        speed=args.speed,
        clear=not args.no_clear,
        compact=True if args.compact else None,
    )
    ui.splash(
        f"{args.players} players · {args.difficulty} opponents · "
        f"{args.deck} card deck   (? for help once you are in)"
    )

    played = 0
    try:
        while True:
            play_one_game(args, ui, rng)
            played += 1
            if args.rounds and played >= args.rounds:
                break
            print()
            if not ui.ask_yes_no("Another game?"):
                break
    except QuitGame:
        print("\n  Bye.")
        return 0
    except KeyboardInterrupt:  # pragma: no cover
        print("\n  Bye.")
        return 130
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
