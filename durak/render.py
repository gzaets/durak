"""ASCII/ANSI rendering helpers. Nothing here knows the rules of the game."""

from __future__ import annotations

import os
import shutil
import sys

from .cards import Card, RED_SUITS, SUIT_SYMBOLS

CARD_WIDTH = 7
CARD_HEIGHT = 5
GAP = 1

RESET = "\033[0m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"


# Enough of the Russian alphabet to transliterate the handful of words the
# tutorial uses, so --ascii shows "durak" rather than a row of question marks.
CYRILLIC = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}
CYRILLIC.update({upper: latin.capitalize() for upper, latin in
                 ((c.upper(), t) for c, t in list(CYRILLIC.items()) if t)})

# Applied to every line of output in --ascii mode, so that text coming from the
# engine (card names, em dashes) survives on terminals with no Unicode support.
ASCII_FALLBACKS = str.maketrans(
    {
        **CYRILLIC,
        "♠": "S",
        "♥": "H",
        "♦": "D",
        "♣": "C",
        "—": "-",
        "–": "-",
        "→": ">",
        "←": "<",
        "·": ".",
        "▨": "#",
        "░": "#",
        "│": "|",
        "─": "-",
        "┌": "+",
        "┐": "+",
        "└": "+",
        "┘": "+",
    }
)


def to_ascii(text: str) -> str:
    """Best-effort ASCII transliteration; anything unmapped becomes '?'."""
    return text.translate(ASCII_FALLBACKS).encode("ascii", "replace").decode("ascii")


class Style:
    """Presentation switches: colour, pure-ASCII mode, and the trump suit.

    The trump suit lives here rather than being threaded through every drawing
    call because it is fixed for a whole game and only ever affects colour —
    trumps are outlined in cyan so they stand out from the suit they happen to
    share a colour with. Set it with :meth:`set_trump` when a game starts.
    """

    def __init__(
        self,
        color: bool = True,
        ascii_only: bool = False,
        trump: str | None = None,
        ranks: dict | None = None,
    ) -> None:
        self.color = color
        self.ascii_only = ascii_only
        self.trump = trump
        # Face-card letters for the current language; None means J/Q/K/A.
        self.ranks = ranks

    @classmethod
    def detect(cls, color: bool | None = None, ascii_only: bool = False) -> "Style":
        if color is None:
            color = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
        return cls(color=color, ascii_only=ascii_only)

    def set_trump(self, suit: str | None) -> None:
        self.trump = suit

    def fit(self, text: str) -> str:
        """Text as it will actually be printed, for anything width-sensitive.

        write() transliterates at the last moment, which changes how wide a
        string is ("Люба" becomes "Lyuba"). Anything that gets padded into a
        column has to be converted before its width is measured.
        """
        return to_ascii(text) if self.ascii_only else text

    def rank_text(self, card: Card) -> str:
        """The rank as written in the current language."""
        return (self.ranks or {}).get(card.rank) or card.rank_name

    def is_trump(self, card: Card) -> bool:
        return self.trump is not None and card.suit == self.trump

    def border_code(self, card: Card) -> str:
        """Colour for a card's outline: cyan marks a trump."""
        if self.is_trump(card):
            return CYAN
        return RED if card.suit in RED_SUITS else BOLD

    def pip_code(self, card: Card) -> str:
        """Colour for the rank and suit inside the card, which keep suit colour."""
        return RED if card.suit in RED_SUITS else BOLD

    def paint(self, text: str, *codes: str) -> str:
        if not self.color or not codes:
            return text
        return "".join(codes) + text + RESET

    def suit(self, suit: str) -> str:
        return suit if self.ascii_only else SUIT_SYMBOLS[suit]

    def card_label(self, card: Card) -> str:
        """One-line name, cyan when it is a trump."""
        text = card.label(self.ascii_only, self.ranks)
        if self.is_trump(card):
            return self.paint(text, CYAN, BOLD)
        return self.paint(text, self.pip_code(card))

    def cards_label(self, cards) -> str:
        return " ".join(self.card_label(c) for c in cards)


def _frame(style: Style) -> tuple[str, str, str]:
    """The three pieces of a card's outline: top, bottom, and one side char."""
    span = CARD_WIDTH - 2
    if style.ascii_only:
        edge = "+" + "-" * span + "+"
        return edge, edge, "|"
    return "┌" + "─" * span + "┐", "└" + "─" * span + "┘", "│"


def _box(style: Style, top: str, mid: str, bot: str) -> list[str]:
    """Frame three pre-padded content rows in a card-sized box (uncoloured)."""
    head, foot, side = _frame(style)
    return [head, *(f"{side}{row}{side}" for row in (top, mid, bot)), foot]


def card_art(card: Card, style: Style) -> list[str]:
    """Five lines of art for a single card.

    The outline and the pip are coloured separately so a trump can be outlined
    in cyan while its rank and suit keep the usual red or black.
    """
    inner = CARD_WIDTH - 2
    rank = style.rank_text(card)
    rows = (rank.ljust(inner), style.suit(card.suit).center(inner), rank.rjust(inner))
    if not style.color:
        return _box(style, *rows)

    head, foot, side = _frame(style)
    edge = style.border_code(card)
    bar = style.paint(side, edge)
    return [
        style.paint(head, edge),
        *(f"{bar}{style.paint(row, style.pip_code(card))}{bar}" for row in rows),
        style.paint(foot, edge),
    ]


def card_back(style: Style) -> list[str]:
    inner = CARD_WIDTH - 2
    fill = "#" * inner if style.ascii_only else "░" * inner
    lines = _box(style, fill, fill, fill)
    return [style.paint(line, DIM) for line in lines]


def blank_art() -> list[str]:
    return [" " * CARD_WIDTH] * CARD_HEIGHT


def _visible_len(text: str) -> int:
    """Length of ``text`` ignoring ANSI escape sequences."""
    out = 0
    i = 0
    while i < len(text):
        if text[i] == "\033":
            while i < len(text) and text[i] != "m":
                i += 1
            i += 1
            continue
        out += 1
        i += 1
    return out


def join_art(columns: list[list[str]], gap: int = GAP) -> list[str]:
    """Place card-art columns side by side."""
    if not columns:
        return []
    height = max(len(c) for c in columns)
    spacer = " " * gap
    rows = []
    for row in range(height):
        parts = []
        for col in columns:
            parts.append(col[row] if row < len(col) else " " * CARD_WIDTH)
        rows.append(spacer.join(parts))
    return rows


def terminal_width(default: int = 80) -> int:
    return max(40, shutil.get_terminal_size((default, 24)).columns)


def cards_per_row(width: int | None = None) -> int:
    width = width or terminal_width()
    return max(1, (width + GAP) // (CARD_WIDTH + GAP))


def hand_art(
    cards: list[Card],
    style: Style,
    labels: list[str] | None = None,
    playable: list[bool] | None = None,
    width: int | None = None,
) -> list[str]:
    """Render a hand, wrapping onto several rows if the terminal is narrow.

    ``labels`` are printed under each card (usually the selection number);
    cards marked not ``playable`` are dimmed and their label is replaced by dots.
    """
    if not cards:
        return [style.paint("(no cards)", DIM)]
    per_row = cards_per_row(width)
    lines: list[str] = []
    for start in range(0, len(cards), per_row):
        chunk = cards[start : start + per_row]
        columns = []
        caption = []
        for offset, card in enumerate(chunk):
            index = start + offset
            usable = playable[index] if playable else True
            art = card_art(card, style)
            if not usable and style.color:
                art = [style.paint(line, DIM) for line in card_art(card, Style(False, style.ascii_only))]
            columns.append(art)
            if labels is not None:
                text = labels[index] if usable else "·" * len(labels[index])
                text = text.center(CARD_WIDTH)
                caption.append(style.paint(text, GREEN) if usable and style.color else text)
        lines.extend(join_art(columns))
        if caption:
            lines.append((" " * GAP).join(caption))
    return lines


def table_art(entries, style: Style, width: int | None = None) -> list[str]:
    """Attack cards on the top row, the card that beat them tucked underneath."""
    if not entries:
        return [style.paint("  (table is empty)", DIM)]
    per_row = cards_per_row((width or terminal_width()) - 2)
    lines: list[str] = []
    for start in range(0, len(entries), per_row):
        chunk = entries[start : start + per_row]
        attacks = [card_art(e.attack, style) for e in chunk]
        defenses = [card_art(e.defense, style) if e.defense else blank_art() for e in chunk]
        lines.extend("  " + row for row in join_art(attacks))
        lines.extend("    " + row for row in join_art(defenses))
    return lines


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _visible_len(text))


def clear_screen(enabled: bool = True) -> None:
    if enabled:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
