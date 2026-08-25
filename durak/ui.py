"""Everything the human sees and types. Pure presentation + input parsing."""

from __future__ import annotations

import shutil
import sys
import time
from typing import Optional, Sequence

from . import render
from .ai import suggest_defense, suggest_move
from .cards import Card, SUIT_NAMES
from .engine import GameView, Transfer
from .players import QuitGame
from .render import BOLD, CYAN, DIM, GREEN, RED, YELLOW, Style

BANNER = r"""
 ____  _   _ ____      _    _  __
|  _ \| | | |  _ \    / \  | |/ /
| | | | | | | |_) |  / _ \ | ' /
| |_| | |_| |  _ <  / ___ \| . \
|____/ \___/|_| \_\/_/   \_\_|\_\
"""

# Verbs the engine logs, in the form to use when the actor is the reader.
SECOND_PERSON = {
    "attacks": "attack",
    "adds": "add",
    "beats": "beat",
    "takes": "take",
    "picks": "pick",
    "passes": "pass",
    "holds": "hold",
    "is": "are",
}

ROLE_TAGS = {
    "attacker": ("[A]", "attacking", YELLOW),
    "defender": ("[D]", "defending", CYAN),
    "thrower": ("[+]", "may throw in", DIM),
    "idle": ("[ ]", "waiting", DIM),
    "out": ("[x]", "out — safe", GREEN),
}

HELP_TEXT = """
How to play
-----------
  Beat the attacking card with a higher card of the SAME suit, or with any
  trump. A trump can only be beaten by a bigger trump.
  Attackers may keep throwing in cards whose rank already appears on the
  table, up to 6 cards or the number of cards the defender started with.
  Beat everything and the cards are discarded; take them and the next player
  attacks instead. The last player still holding cards is the durak.

  In TRANSFER mode you have a third option while defending: if you hold a card
  of the same rank as the card(s) attacking you, and you have not beaten
  anything yet, you can add it and pass the whole attack to the next player
  clockwise, who then has to beat all of them. With two players it goes back to
  your attacker. They can pass it on again if they hold the rank too.

Commands
--------
  1 2 3 ...   play the card with that number
  d / enter   done attacking (pass the throw-in)
  t           take the cards on the table
  p / p3      pass the attack on (transfer mode only)
  b3          beat with card 3, when that card could also pass the attack on
  s           suggest a move
  ?           this help
  q           quit the game
"""


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
    ) -> None:
        self.style = style or Style.detect()
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

    # ------------------------------------------------------------- plumbing

    def attach(self, engine, human) -> None:
        """Let the UI redraw the board whenever the engine reports something."""
        self.engine = engine
        self.human = human

    def event(self, message: str) -> None:
        """Engine log sink: animate the board so AI moves are watchable."""
        if not message.strip():
            return
        if self.engine is None or self.human is None:
            self.write(message + "\n")
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
        s = self.style
        trump_face = view.trump_card.label(s.ascii_only) if view.trump_card else "?"
        trump = f"{s.suit(view.trump_suit)} {SUIT_NAMES[view.trump_suit]}"
        if view.deck_count:
            stock = f"stock {view.deck_count} (bottom card {trump_face})"
        else:
            stock = self._p("stock empty — endgame", YELLOW)
        bar = (
            f"  Trump {self._p(trump, BOLD)}   {stock}   "
            f"beaten pile {view.discard_count}"
        )
        mode = "" if view.mode == "classic" else self._p("  ·  transfer mode", GREEN)
        title = self._p("  D U R A K", BOLD, CYAN) + mode
        return [title, bar]

    def _opponents(self, view: GameView) -> list[str]:
        s = self.style
        lines = [self._p("  Players", DIM)]
        width = max(len(p.name) for p in view.players)
        for info in view.players:
            tag, label, code = ROLE_TAGS.get(info.role, ("[ ]", "", DIM))
            you = " (you)" if info.name == view.you else ""
            pips = "" if info.role == "out" else self._pips(info.hand_count)
            count = "" if info.role == "out" else f"{info.hand_count:>2} "
            row = (
                f"  {self._p(tag, code)} {render.pad(info.name + you, width + 6)}"
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
        header = f"  Table  {len(view.table)}/{view.attack_limit}"
        if view.taken:
            header += self._p("   (defender is taking)", YELLOW)
        elif view.unbeaten:
            header += self._p("   (unbeaten card on the table)", RED)
        lines = [self._p(header, DIM)]
        if not view.table:
            lines.append(self._p("    empty", DIM))
        elif self.compact:
            for entry in view.table:
                left = s.card_label(entry.attack)
                right = s.card_label(entry.defense) if entry.defense else self._p("---", RED)
                lines.append(f"    {left} ← {right}")
        else:
            lines.extend(render.table_art(view.table, s))
        return lines

    def _log(self, view: GameView) -> list[str]:
        entries = [line for line in view.log if line.strip()][-self.log_lines :]
        lines = [self._p("  Log", DIM)]
        last = len(entries) - 1
        for index, line in enumerate(entries):
            line = self._second_person(line, view.you)
            lines.append("    " + self._p(line, BOLD if index == last else DIM))
        while len(lines) < self.log_lines + 1:
            lines.append("")
        return lines

    def _second_person(self, line: str, you: str) -> str:
        """"You takes the cards" reads badly — say "You take the cards".

        Only applies when the player kept the default name; a real name stays
        in the third person, which is already correct English.
        """
        if you.lower() != "you" or not line.startswith(you + " "):
            return line
        verb, _, rest = line[len(you) + 1 :].partition(" ")
        return f"{you} {SECOND_PERSON.get(verb, verb)} {rest}".rstrip()

    def _hand(self, view: GameView, legal: Sequence[Card] = ()) -> list[str]:
        s = self.style
        legal_set = set(legal)
        header = f"  Your hand ({len(view.hand)})"
        lines = [self._p(header, DIM)]
        if not view.hand:
            lines.append(self._p("    (empty)", DIM))
            return lines
        labels = [str(i + 1) for i in range(len(view.hand))]
        playable = [not legal or card in legal_set for card in view.hand]
        if self.compact:
            parts = []
            for index, card in enumerate(view.hand):
                text = f"{index + 1}:{card.label(s.ascii_only)}"
                parts.append(self._p(text, GREEN if playable[index] else DIM))
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
        if command in ("q", "quit", "exit"):
            raise QuitGame
        if command in ("?", "h", "help"):
            self.write(HELP_TEXT + "\n")
            self._read("  press enter to continue ")
            return "redraw"
        if command in ("s", "hint", "suggest"):
            card = hint()
            if card is None:
                self.status = "Hint: pass / take."
            else:
                self.status = f"Hint: try {card.label(self.style.ascii_only)}."
            return "redraw"
        return None

    def ask_attack(self, view: GameView, legal: list[Card], initial: bool) -> Optional[Card]:
        indices = {view.hand.index(card) + 1: card for card in legal}
        choices = ",".join(str(i) for i in sorted(indices))
        if initial:
            note = f"Attack {self._p(view.defender, CYAN)} — pick a card [{choices}]"
            note += self._p("   (? help, q quit)", DIM)
        else:
            note = f"Throw in on {self._p(view.defender, CYAN)}? [{choices}]"
            note += f", {self._p('d', BOLD)}=done" + self._p("   (? help, q quit)", DIM)

        while True:
            self._prompt(view, legal, note)
            command = self._read("  > ")
            meta = self._handle_meta(command, view, lambda: suggest_move(view, legal, initial))
            if meta == "redraw":
                continue
            if command in ("", "d", "done", "p", "pass"):
                if initial:
                    self.status = "You must open the attack with a card."
                    continue
                return None
            if command in ("t", "take"):
                self.status = "You are attacking — nothing to take."
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
            command = self._read("  > ")
            meta = self._handle_meta(
                command, view, lambda: suggest_defense(view, attack, legal, transfers)
            )
            if meta == "redraw":
                continue
            if command in ("t", "take", "", "d"):
                return None

            # An explicit b12 / p12 settles a card that could do either.
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

            card = self._parse_index(command, {**beat_at, **pass_at})
            if card is None:
                continue
            index = view.hand.index(card) + 1
            if index in beat_at and index in pass_at:
                label = self.style.card_label(card)
                self.status = (
                    f"{label} can beat it or pass it on — "
                    f"type b{index} to beat, p{index} to pass."
                )
                continue
            return card if index in beat_at else Transfer(card)

    def _defense_note(self, view: GameView, attack: Card, beat_at: dict, pass_at: dict) -> str:
        face = self.style.card_label(attack)
        unbeaten = len(view.unbeaten)
        target = f"Beat {face}" if unbeaten < 2 else f"Beat {face} ({unbeaten} to beat)"
        parts = [f"{target} — pick a card [{_choices(beat_at)}]" if beat_at else target]
        if pass_at:
            parts.append(
                f"{self._p('p', BOLD)}=pass to {self._p(view.receiver or '?', CYAN)} "
                f"[{_choices(pass_at)}]"
            )
        parts.append(f"{self._p('t', BOLD)}=take")
        return ", ".join(parts) + self._p("   (? help, q quit)", DIM)

    def _pick(self, number: str, options: dict, prefix: str):
        """Resolve the number in a 'b12' / 'p12' style command.

        A bare prefix is enough when there is only one card it could mean.
        """
        if not number:
            if len(options) == 1:
                return next(iter(options.values()))
            self.status = f"Which card? Add its number, e.g. {prefix}{min(options)}."
            return None
        return self._parse_index(number, options)

    def _parse_index(self, command: str, indices: dict[int, Card]) -> Optional[Card]:
        if not command.isdigit():
            self.status = f"'{command}' is not a card number. Press ? for help."
            return None
        number = int(command)
        if number not in indices:
            self.status = f"Card {number} cannot be played here."
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
        lines = [""]
        if result.durak is None:
            lines.append("  " + self._p("A draw — everybody went out together!", BOLD))
        elif self.human is not None and result.durak == self.human.name:
            lines.append("  " + self._p("You are the DURAK.", RED, BOLD))
            lines.append(self._p(FOOL_ART, RED))
        else:
            lines.append("  " + self._p(f"{result.durak} is the DURAK!", GREEN, BOLD))
        if result.order_out:
            lines.append("  Went out: " + ", ".join(result.order_out))
        lines.append(f"  Bouts played: {result.bouts}")
        if self.scores:
            lines.append("\n  Durak count so far:")
            for name, count in sorted(self.scores.items(), key=lambda kv: -kv[1]):
                lines.append(f"    {render.pad(name, 14)} {count}")
        self.write("\n".join(lines) + "\n")

    def ask_choice(self, question: str, options: list, default: int = 0):
        """Numbered menu used by the setup screen. ``options`` is (value, name, blurb)."""
        while True:
            lines = ["  " + self._p(question, BOLD)]
            for index, (_, name, blurb) in enumerate(options, start=1):
                marker = self._p("*", GREEN) if index == default + 1 else " "
                lines.append(f"   {marker} {index}) {self._p(name, BOLD)} — {blurb}")
            self.write("\n".join(lines) + "\n")
            answer = self._read(f"  > [1-{len(options)}, enter for {default + 1}] ")
            if not answer:
                return options[default][0]
            if answer in ("q", "quit", "exit"):
                raise QuitGame
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return options[int(answer) - 1][0]
            self.write(self._p(f"  '{answer}' is not one of the options.\n", YELLOW))

    def ask_yes_no(self, question: str, default: bool = True) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            answer = self._read(f"  {question} {suffix} ")
            if not answer:
                return default
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no", "q", "quit"):
                return False


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
