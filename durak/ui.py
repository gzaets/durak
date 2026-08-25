"""Everything the human sees and types. Pure presentation + input parsing."""

from __future__ import annotations

import shutil
import sys
import time
from typing import Optional, Sequence

from . import render
from .ai import suggest_defense, suggest_move
from .cards import Card
from .engine import GameView, Transfer
from .i18n import (
    BACK_WORDS,
    DONE_WORDS,
    HELP_WORDS,
    HINT_WORDS,
    NO_WORDS,
    QUIT_WORDS,
    STOP_DEFENDING,
    TAKE_WORDS,
    YES_WORDS,
    Message,
    Translator,
)
from .players import QuitGame
from .tutorial import help_text
from .render import BOLD, CYAN, DIM, GREEN, RED, YELLOW, Style

BANNER = r"""
 ____  _   _ ____      _    _  __
|  _ \| | | |  _ \    / \  | |/ /
| | | | | | | |_) |  / _ \ | ' /
| |_| | |_| |  _ <  / ___ \| . \
|____/ \___/|_| \_\/_/   \_\_|\_\
"""

# Tag and colour per role; the wording comes from the translator.
ROLE_TAGS = {
    "attacker": ("[A]", YELLOW),
    "defender": ("[D]", CYAN),
    "thrower": ("[+]", DIM),
    "idle": ("[ ]", DIM),
    "out": ("[x]", GREEN),
}

def _choices(options: dict) -> str:
    return ",".join(str(i) for i in sorted(options))


class TerminalUI:
    def __init__(
        self,
        style: Optional[Style] = None,
        speed: float = 0.6,
        clear: bool = True,
        compact: Optional[bool] = None,
        log_lines: int = 5,
        lang: str = "en",
    ) -> None:
        self.style = style or Style.detect()
        self.t = Translator(lang)
        self.style.ranks = self.t.rank_letters(self.style.ascii_only)
        self.speed = max(0.0, speed)
        self.clear = clear
        self.log_lines = log_lines
        if compact is None:
            compact = shutil.get_terminal_size((80, 24)).lines < 26
        self.compact = compact
        self.engine = None
        self.human = None
        self.scores: dict[str, int] = {}
        self.status: str = ""

    @property
    def lang(self) -> str:
        return self.t.lang

    def set_language(self, lang: str) -> None:
        """Switch the whole interface, including how face cards are written."""
        self.t = Translator(lang)
        self.style.ranks = self.t.rank_letters(self.style.ascii_only)

    # ------------------------------------------------------------- plumbing

    def attach(self, engine, human) -> None:
        """Let the UI redraw the board whenever the engine reports something."""
        self.engine = engine
        self.human = human
        self.style.set_trump(engine.trump)

    def event(self, message: Message) -> None:
        """Engine log sink: animate the board so AI moves are watchable."""
        if self.engine is None or self.human is None:
            self.write(self.say(message) + "\n")
            return
        if self.speed <= 0:
            return
        # The message is already the last line of the log panel; just re-draw.
        self.draw(self.engine.view_for(self.human))
        time.sleep(self.speed)

    def _p(self, text: str, *codes: str) -> str:
        return self.style.paint(text, *codes)

    def write(self, text: str) -> None:
        """The single way anything reaches the terminal."""
        if self.style.ascii_only:
            text = render.to_ascii(text)
        sys.stdout.write("\n".join(line.rstrip() for line in text.split("\n")))
        sys.stdout.flush()

    # -------------------------------------------------------------- drawing

    def draw(self, view: GameView, legal: Sequence[Card] = (), note: str = "") -> None:
        """Redraw the whole board. ``legal`` dims the cards you may not play."""
        render.clear_screen(self.clear)
        out: list[str] = []
        out.extend(self._header(view))
        out.append("")
        out.extend(self._opponents(view))
        out.append("")
        out.extend(self._table(view))
        out.append("")
        out.extend(self._log(view))
        out.append("")
        out.extend(self._hand(view, legal))
        if note:
            out.append("")
            out.append("  " + note)
        self.write("\n".join(out) + "\n")

    def _header(self, view: GameView) -> list[str]:
        s, t = self.style, self.t
        trump = f"{s.suit(view.trump_suit)} {t.suit_name(view.trump_suit)}"
        if view.deck_count:
            face = view.trump_card.label(s.ascii_only, s.ranks) if view.trump_card else "?"
            stock = t("stock", n=view.deck_count, card=face)
        else:
            stock = self._p(t("stock_empty"), YELLOW)
        bar = (
            f"  {t('trump')} {self._p(trump, BOLD)}   {stock}   "
            f"{t('discard', n=view.discard_count)}"
        )
        mode = "" if view.mode == "classic" else self._p(f"  ·  {t('transfer_mode')}", GREEN)
        return [self._p("  " + t("title"), BOLD, CYAN) + mode, bar]

    def _opponents(self, view: GameView) -> list[str]:
        t = self.t
        lines = [self._p("  " + t("players"), DIM)]
        names = {info.name: self.style.fit(info.name) for info in view.players}
        width = max(len(name) for name in names.values())
        for info in view.players:
            tag, code = ROLE_TAGS.get(info.role, ("[ ]", DIM))
            label = t(f"role_{info.role}")
            you = self.style.fit(t("you_marker")) if info.name == view.you else ""
            pips = "" if info.role == "out" else self._pips(info.hand_count)
            count = "" if info.role == "out" else f"{info.hand_count:>2} "
            row = (
                f"  {self._p(tag, code)} {render.pad(names[info.name] + you, width + 6)}"
                f"{count}{pips}  {self._p(label, code)}"
            )
            lines.append(row)
        return lines

    def _pips(self, count: int) -> str:
        glyph = "▨"  # write() turns this into '#' in --ascii mode
        if count <= 12:
            return self._p(glyph * count, DIM)
        return self._p(glyph * 12 + f"+{count - 12}", DIM)

    def _table(self, view: GameView) -> list[str]:
        s = self.style
        header = f"  {self.t('table')}  {len(view.table)}/{view.attack_limit}"
        if view.taken:
            header += self._p("   " + self.t("table_taking"), YELLOW)
        elif view.unbeaten:
            header += self._p("   " + self.t("table_unbeaten"), RED)
        lines = [self._p(header, DIM)]
        if not view.table:
            lines.append(self._p("    " + self.t("table_empty"), DIM))
        elif self.compact:
            for entry in view.table:
                left = s.card_label(entry.attack)
                right = s.card_label(entry.defense) if entry.defense else self._p("---", RED)
                lines.append(f"    {left} ← {right}")
        else:
            lines.extend(render.table_art(view.table, s))
        return lines

    def say(self, message: Message, you: Optional[str] = None) -> str:
        """Turn an engine event into a sentence in the current language."""
        params = {
            key: value.label(self.style.ascii_only, self.style.ranks)
            if isinstance(value, Card)
            else value
            for key, value in message.params.items()
        }
        return self.t.render(Message(message.key, params), you=you)

    def _log(self, view: GameView) -> list[str]:
        entries = view.log[-self.log_lines :]
        lines = [self._p("  " + self.t("log"), DIM)]
        last = len(entries) - 1
        for index, message in enumerate(entries):
            text = self.say(message, view.you)
            lines.append("    " + self._p(text, BOLD if index == last else DIM))
        while len(lines) < self.log_lines + 1:
            lines.append("")
        return lines

    def _hand(self, view: GameView, legal: Sequence[Card] = ()) -> list[str]:
        s = self.style
        legal_set = set(legal)
        lines = [self._p("  " + self.t("hand", n=len(view.hand)), DIM)]
        if not view.hand:
            lines.append(self._p("    " + self.t("hand_empty"), DIM))
            return lines
        labels = [str(i + 1) for i in range(len(view.hand))]
        playable = [not legal or card in legal_set for card in view.hand]
        if self.compact:
            parts = []
            for index, card in enumerate(view.hand):
                text = f"{index + 1}:{card.label(s.ascii_only, s.ranks)}"
                if not playable[index]:
                    code = DIM
                else:
                    # Cyan and green both mean playable; cyan also means trump.
                    code = CYAN if s.is_trump(card) else GREEN
                parts.append(self._p(text, code))
            lines.append("    " + "  ".join(parts))
        else:
            art = render.hand_art(view.hand, s, labels=labels, playable=playable)
            lines.extend("  " + row for row in art)
        return lines

    def _prompt(self, view: GameView, legal: Sequence[Card], note: str) -> None:
        """Draw the board with a status line and the prompt hint underneath."""
        if self.status:
            note = self._p("! " + self.status, YELLOW) + "\n  " + note
            self.status = ""
        self.draw(view, legal, note)

    # ---------------------------------------------------------------- input

    def _read(self, prompt: str) -> str:
        if self.style.ascii_only:
            prompt = render.to_ascii(prompt)
        try:
            return input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            self.write("\n")
            raise QuitGame from None

    def _handle_meta(self, command: str, view: GameView, hint) -> Optional[str]:
        """Deal with the commands that are the same on every prompt."""
        if command in QUIT_WORDS:
            raise QuitGame
        if command in HELP_WORDS:
            self.write(help_text(self.lang) + "\n")
            self._read(self.t("prompt_continue"))
            return "redraw"
        if command in HINT_WORDS:
            card = hint()
            if card is None:
                self.status = self.t("hint_pass")
            else:
                self.status = self.t(
                    "hint_card", card=card.label(self.style.ascii_only, self.style.ranks)
                )
            return "redraw"
        return None

    def ask_attack(self, view: GameView, legal: list[Card], initial: bool) -> Optional[Card]:
        indices = {view.hand.index(card) + 1: card for card in legal}
        t, choices = self.t, _choices(indices)
        target = self._p(view.defender, CYAN)
        if initial:
            note = t("prompt_attack", target=target, choices=choices)
        else:
            note = t("prompt_throw", target=target, choices=choices)
            note += ", " + t("prompt_done", key=self._p("d", BOLD))
        note += self._p(t("keys_hint"), DIM)

        while True:
            self._prompt(view, legal, note)
            command = self._read(t("prompt_input"))
            meta = self._handle_meta(command, view, lambda: suggest_move(view, legal, initial))
            if meta == "redraw":
                continue
            if command == "" or command in DONE_WORDS:
                if initial:
                    self.status = t("err_must_attack")
                    continue
                return None
            if command in TAKE_WORDS:
                self.status = t("err_nothing_to_take")
                continue
            card = self._parse_index(command, indices)
            if card is None:
                continue
            return card

    def ask_defense(self, view, attack, legal, transfers=()):
        beat_at = {view.hand.index(card) + 1: card for card in legal}
        pass_at = {view.hand.index(card) + 1: card for card in transfers}
        note = self._defense_note(view, attack, beat_at, pass_at)

        while True:
            self._prompt(view, list(legal) + list(transfers), note)
            command = self._read(self.t("prompt_input"))
            meta = self._handle_meta(
                command, view, lambda: suggest_defense(view, attack, legal, transfers)
            )
            if meta == "redraw":
                continue
            # The p/b prefixes come first: "p" is also the "no more throw-ins"
            # key, and must not be read as "take" while a transfer is on offer.
            intent, number = command[:1], command[1:].strip()
            if pass_at and intent == "p":
                card = self._pick(number, pass_at, "p")
                if card is not None:
                    return Transfer(card)
                continue
            if intent == "b" and number:
                card = self._pick(number, beat_at, "b")
                if card is not None:
                    return card
                continue
            if command == "" or command in TAKE_WORDS or command in STOP_DEFENDING:
                return None

            card = self._parse_index(command, {**beat_at, **pass_at})
            if card is None:
                continue
            index = view.hand.index(card) + 1
            if index in beat_at and index in pass_at:
                self.status = self.t(
                    "err_ambiguous", card=self.style.card_label(card), n=index
                )
                continue
            return card if index in beat_at else Transfer(card)

    def _defense_note(self, view: GameView, attack: Card, beat_at: dict, pass_at: dict) -> str:
        t = self.t
        face = self.style.card_label(attack)
        unbeaten = len(view.unbeaten)
        head = (
            t("prompt_beat", card=face)
            if unbeaten < 2
            else t("prompt_beat_many", card=face, n=unbeaten)
        )
        if beat_at:
            head += " — " + t("prompt_pick", choices=_choices(beat_at))
        parts = [head]
        if pass_at:
            parts.append(
                t(
                    "prompt_pass",
                    key=self._p("p", BOLD),
                    target=self._p(view.receiver or "?", CYAN),
                    choices=_choices(pass_at),
                )
            )
        parts.append(t("prompt_take", key=self._p("t", BOLD)))
        return ", ".join(parts) + self._p(t("keys_hint"), DIM)

    def _pick(self, number: str, options: dict, prefix: str):
        """Resolve the number in a 'b12' / 'p12' style command.

        A bare prefix is enough when there is only one card it could mean.
        """
        if not number:
            if len(options) == 1:
                return next(iter(options.values()))
            self.status = self.t("err_which_card", key=prefix, n=min(options))
            return None
        return self._parse_index(number, options)

    def _parse_index(self, command: str, indices: dict[int, Card]) -> Optional[Card]:
        if not command.isdigit():
            self.status = self.t("err_not_a_number", text=command)
            return None
        number = int(command)
        if number not in indices:
            self.status = self.t("err_cannot_play", n=number)
            return None
        return indices[number]

    # ------------------------------------------------------------ endgame UI

    def splash(self, subtitle: str) -> None:
        render.clear_screen(self.clear)
        self.write(self._p(BANNER, CYAN, BOLD) + "\n  " + subtitle + "\n\n")

    def announce(self, result, view: Optional[GameView] = None) -> None:
        if view is not None:
            self.status = ""
            self.draw(view)
        t = self.t
        lost = self.human is not None and result.durak == self.human.name
        lines = [""]
        if result.durak is None:
            lines.append("  " + self._p(t("draw"), BOLD))
        elif lost:
            lines.append("  " + self._p(t("durak_you"), RED, BOLD))
            lines.append(self._p(FOOL_ART, RED))
        else:
            lines.append("  " + self._p(t("durak_other", actor=result.durak), GREEN, BOLD))
        # Anyone who is not the durak got out safe, a draw included.
        if self.human is not None and not lost:
            lines.append(self._p(CROWN_ART, YELLOW))
        if result.order_out:
            lines.append(t("went_out", names=", ".join(result.order_out)))
        lines.append(t("bouts", n=result.bouts))
        if self.scores:
            lines.append("\n" + t("scoreboard"))
            for name, count in sorted(self.scores.items(), key=lambda kv: -kv[1]):
                lines.append(f"    {render.pad(self.style.fit(name), 14)} {count}")
        self.write("\n".join(lines) + "\n")

    def ask_choice(self, question: str, options: list, default: int = 0):
        """Numbered menu used by the setup screen. ``options`` is (value, name, blurb)."""
        while True:
            lines = ["  " + self._p(question, BOLD)]
            for index, (_, name, blurb) in enumerate(options, start=1):
                marker = self._p("*", GREEN) if index == default + 1 else " "
                lines.append(f"   {marker} {index}) {self._p(name, BOLD)} — {blurb}")
            self.write("\n".join(lines) + "\n")
            answer = self._read(
                self.t("prompt_choice", n=len(options), default=default + 1)
            )
            if not answer:
                return options[default][0]
            if answer in QUIT_WORDS:
                raise QuitGame
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return options[int(answer) - 1][0]
            self.write(self._p(self.t("err_not_an_option", text=answer) + "\n", YELLOW))

    def show_pages(self, pages: Sequence[str], footer: str = "") -> None:
        """Print long text a page at a time, so it does not scroll past."""
        total = len(pages)
        for number, page in enumerate(pages, start=1):
            render.clear_screen(self.clear)
            self.write(page + "\n")
            if number < total:
                counter = self._p(f"({number}/{total})", DIM)
                if self._read(self.t("prompt_page", counter=counter)) in BACK_WORDS:
                    return
        if footer:
            self.write("\n  " + footer + "\n")
        self._read(self.t("prompt_back"))

    def ask_yes_no(self, question: str, default: bool = True) -> bool:
        suffix = self.t("yes_no" if default else "no_yes")
        while True:
            answer = self._read(f"  {question} {suffix} ")
            if not answer:
                return default
            if answer in YES_WORDS:
                return True
            if answer in NO_WORDS or answer in QUIT_WORDS:
                return False


CROWN_ART = r"""
       .      .      .
      (o)    (o)    (o)
       |      |      |
     \ |      |      | /
     \_|______|______|_/
     |                 |
     | *      *      * |
     |_________________|
     `-----------------'
"""

FOOL_ART = r"""
        .-"      "-.
       /            \
      |,  .-.  .-.  ,|
      | )(_o/  \o_)( |
      |/     /\     \|
      (_     ^^     _)
       \__|IIIIII|__/
        | \IIIIII/ |
        \          /
         `--------`
"""
