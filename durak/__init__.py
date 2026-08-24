"""A terminal-only implementation of the Russian card game Durak."""

from .cards import Card, beats, build_deck
from .engine import Durak, GameResult, GameView, TableEntry
from .players import Player

__version__ = "0.1.0"
__all__ = [
    "Card",
    "Durak",
    "GameResult",
    "GameView",
    "Player",
    "TableEntry",
    "beats",
    "build_deck",
    "__version__",
]
