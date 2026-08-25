"""Translation of everything the player reads.

The engine never formats prose. It emits :class:`Message` events — a key plus
parameters — and this module turns them into text in the chosen language. That
keeps the rules free of presentation, and means a future network protocol can
send the events themselves rather than a wall of English.

A note on the Russian: player names are never declined. Russian would want
"переводит на Ивана" (accusative) and "у Ольги" (genitive), which needs a
declension table per name and a gender for each — impossible for a name the
player types in. So every Russian string here is built so that names stay in
the nominative, usually by labelling them ("Защищается: Ольга"). Verbs are in
the present tense for the same reason: the past tense agrees with gender
("взял" / "взяла") while the present does not ("берёт").
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

ENGLISH = "en"
RUSSIAN = "ru"
LANGUAGES = (ENGLISH, RUSSIAN)

LANGUAGE_NAMES = {ENGLISH: "English", RUSSIAN: "Русский"}


@dataclass(frozen=True)
class Message:
    """Something that happened, in a form that has no language yet."""

    key: str
    params: dict = field(default_factory=dict)


# --------------------------------------------------------------- card names

# The canonical (English/international) rank letters, also used whenever the
# terminal cannot show Cyrillic.
RANKS_EN = {11: "J", 12: "Q", 13: "K", 14: "A"}
# Валет, Дама, Король, Туз.
RANKS_RU = {11: "В", 12: "Д", 13: "К", 14: "Т"}

RANK_LETTERS = {ENGLISH: RANKS_EN, RUSSIAN: RANKS_RU}

SUIT_NAMES = {
    ENGLISH: {"S": "Spades", "H": "Hearts", "D": "Diamonds", "C": "Clubs"},
    RUSSIAN: {"S": "Пики", "H": "Черви", "D": "Бубны", "C": "Трефы"},
}

BOT_NAMES = {
    ENGLISH: ["Ivan", "Olga", "Pyotr", "Nadya", "Grisha", "Vera", "Lyuba", "Misha"],
    RUSSIAN: ["Иван", "Ольга", "Пётр", "Надя", "Гриша", "Вера", "Люба", "Миша"],
}

DEFAULT_NAME = {ENGLISH: "You", RUSSIAN: "Вы"}


# ----------------------------------------------------------------- plurals


def plural_en(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def plural_ru(n: int, one: str, few: str, many: str) -> str:
    """Russian picks between three forms: 1 карта, 2 карты, 5 карт."""
    if n % 100 in range(11, 15):
        return many
    if n % 10 == 1:
        return one
    if n % 10 in (2, 3, 4):
        return few
    return many


def cards_noun(lang: str, n: int) -> str:
    """"card" as the object of a verb — "забирает 1 карту" (accusative)."""
    if lang == RUSSIAN:
        return plural_ru(n, "карту", "карты", "карт")
    return plural_en(n, "card", "cards")


def cards_noun_nom(lang: str, n: int) -> str:
    """"card" as a bare subject — "на столе 1 карта" (nominative).

    Russian only differs from the accusative in the singular, but it differs
    every time the count happens to be one, which is often.
    """
    if lang == RUSSIAN:
        return plural_ru(n, "карта", "карты", "карт")
    return plural_en(n, "card", "cards")


def opponents_noun(lang: str, n: int) -> str:
    if lang == RUSSIAN:
        return plural_ru(n, "соперник", "соперника", "соперников")
    return plural_en(n, "opponent", "opponents")


def players_noun(lang: str, n: int) -> str:
    if lang == RUSSIAN:
        return plural_ru(n, "игрок", "игрока", "игроков")
    return plural_en(n, "player", "players")


# ---------------------------------------------------------------- strings

# Keys ending in ".you" are used instead of the base key when the player who
# did the thing is the one reading the log.
STRINGS: dict[str, dict[str, str]] = {
    ENGLISH: {
        # engine events
        "first_attacker": "{actor} holds the lowest trump ({card}) and attacks first.",
        "first_attacker.you": "You hold the lowest trump ({card}) and attack first.",
        "no_trump_dealt": "Nobody was dealt a trump — {actor} opens.",
        "no_trump_dealt.you": "Nobody was dealt a trump — you open.",
        "bout": "— {actor} attacks {target} —",
        "attack": "{actor} attacks with {card}.",
        "attack.you": "You attack with {card}.",
        "add": "{actor} adds {card}.",
        "add.you": "You add {card}.",
        "beat": "{actor} beats {other} with {card}.",
        "beat.you": "You beat {other} with {card}.",
        "take": "{actor} takes the cards.",
        "take.you": "You take the cards.",
        "pick_up": "{actor} picks up {n} {cards}.",
        "pick_up.you": "You pick up {n} {cards}.",
        "beat_off": "{actor} beat off the attack — {n} {cards_nom} discarded.",
        "beat_off.you": "You beat off the attack — {n} {cards_nom} discarded.",
        "transfer": "{actor} passes the attack to {target} with {card} — {n} {cards_nom} to beat.",
        "transfer.you": "You pass the attack to {target} with {card} — {n} {cards_nom} to beat.",
        "out": "{actor} is out of cards and safe.",
        "out.you": "You are out of cards and safe.",
        # board
        "title": "D U R A K",
        "trump": "Trump",
        "stock": "stock {n} (bottom card {card})",
        "stock_empty": "stock empty — endgame",
        "discard": "beaten pile {n}",
        "transfer_mode": "transfer mode",
        "players": "Players",
        "you_marker": " (you)",
        "table": "Table",
        "table_taking": "(defender is taking)",
        "table_unbeaten": "(unbeaten card on the table)",
        "table_empty": "empty",
        "log": "Log",
        "hand": "Your hand ({n})",
        "hand_empty": "(empty)",
        "role_attacker": "attacking",
        "role_defender": "defending",
        "role_thrower": "may throw in",
        "role_idle": "waiting",
        "role_out": "out — safe",
        # prompts
        "keys_hint": "   (? help, q quit)",
        "prompt_attack": "Attack {target} — pick a card [{choices}]",
        "prompt_throw": "Throw in on {target}? [{choices}]",
        "prompt_done": "{key}=done",
        "prompt_beat": "Beat {card}",
        "prompt_beat_many": "Beat {card} ({n} to beat)",
        "prompt_pick": "pick a card [{choices}]",
        "prompt_pass": "{key}=pass to {target} [{choices}]",
        "prompt_take": "{key}=take",
        "prompt_continue": "press enter to continue ",
        "prompt_input": "  > ",
        "prompt_page": "  {counter} enter to continue, q to go back  ",
        "prompt_back": "  enter to go back  ",
        "prompt_choice": "  > [1-{n}, enter for {default}] ",
        # errors and hints
        "err_not_a_number": "'{text}' is not a card number. Press ? for help.",
        "err_cannot_play": "Card {n} cannot be played here.",
        "err_must_attack": "You must open the attack with a card.",
        "err_nothing_to_take": "You are attacking — nothing to take.",
        "err_not_an_option": "  '{text}' is not one of the options.",
        "err_which_card": "Which card? Add its number, e.g. {key}{n}.",
        "err_ambiguous": "{card} can beat it or pass it on — type b{n} to beat, p{n} to pass.",
        "hint_card": "Hint: try {card}.",
        "hint_pass": "Hint: pass / take.",
        # results
        "durak_you": "You are the DURAK.",
        "durak_other": "{actor} is the DURAK!",
        "draw": "A draw — everybody went out together!",
        "went_out": "  Went out: {names}",
        "bouts": "  Bouts played: {n}",
        "scoreboard": "  Durak count so far:",
        "another_game": "Another game?",
        "bye": "  Bye.",
        # menu and setup
        "menu_title": "Durak",
        "menu_play": "Play",
        "menu_play_blurb": "set up a game and deal",
        "menu_learn": "How to play",
        "menu_learn_blurb": "the rules, and where the game comes from",
        "menu_language": "Language",
        "menu_language_blurb": "English / Русский",
        "menu_quit": "Quit",
        "menu_quit_blurb": "leave",
        "tagline": "A Russian card game for 2 to 6 — last one holding cards loses",
        "setup_title": "Set up your game",
        "setup_mode": "Game mode",
        "mode_classic": "Classic",
        "mode_classic_blurb": "the defender must beat every card or take them all",
        "mode_transfer": "Transfer",
        "mode_transfer_blurb": "the defender may also pass the attack on with a matching rank",
        "setup_opponents": "How many opponents?",
        "opponents_option": "{n} {opponents}",
        "seats": "{n} at the table",
        "seats_deck": "{n} at the table, dealt from {deck} {deck_cards}",
        "setup_difficulty": "Difficulty",
        "easy": "Easy",
        "easy_blurb": "plays more or less at random",
        "normal": "Normal",
        "normal_blurb": "sheds cheap cards and hoards trumps",
        "hard": "Hard",
        "hard_blurb": "also counts the beaten pile",
        "setup_language": "Language",
        "deck_of": "{n} card deck",
        "tutorial_end": "That is all of it — good luck.",
        "yes_no": "[Y/n]",
        "no_yes": "[y/N]",
    },
    RUSSIAN: {
        # engine events
        "first_attacker": "Младший козырь ({card}). Первый ход: {actor}.",
        "first_attacker.you": "Младший козырь ({card}) у вас. Ваш ход первый.",
        "no_trump_dealt": "Козырей никому не досталось. Первый ход: {actor}.",
        "no_trump_dealt.you": "Козырей никому не досталось. Ваш ход первый.",
        "bout": "— Атакует: {actor} · Защищается: {target} —",
        "attack": "{actor} атакует: {card}.",
        "attack.you": "Вы атакуете: {card}.",
        "add": "{actor} подкидывает: {card}.",
        "add.you": "Вы подкидываете: {card}.",
        "beat": "{actor} бьёт {other} картой {card}.",
        "beat.you": "Вы бьёте {other} картой {card}.",
        "take": "{actor} берёт карты.",
        "take.you": "Вы берёте карты.",
        "pick_up": "{actor} забирает {n} {cards}.",
        "pick_up.you": "Вы забираете {n} {cards}.",
        "beat_off": "{actor} отбивается — в отбой: {n} {cards_nom}.",
        "beat_off.you": "Вы отбились — в отбой: {n} {cards_nom}.",
        "transfer": "{actor} переводит: {card}. Защищается: {target} — на столе {n} {cards_nom}.",
        "transfer.you": "Вы переводите: {card}. Защищается: {target} — на столе {n} {cards_nom}.",
        "out": "{actor} выходит из игры — карт больше нет.",
        "out.you": "Вы выходите из игры — карт больше нет.",
        # board
        "title": "Д У Р А К",
        "trump": "Козырь",
        "stock": "колода: {n} (нижняя карта {card})",
        "stock_empty": "колода пуста — эндшпиль",
        "discard": "отбой: {n}",
        "transfer_mode": "с переводом",
        "players": "Игроки",
        "you_marker": " (вы)",
        "table": "Стол",
        "table_taking": "(защитник берёт)",
        "table_unbeaten": "(на столе неотбитая карта)",
        "table_empty": "пусто",
        "log": "Ход игры",
        "hand": "Ваши карты ({n})",
        "hand_empty": "(пусто)",
        "role_attacker": "атакует",
        "role_defender": "защищается",
        "role_thrower": "может подкинуть",
        "role_idle": "ждёт",
        "role_out": "вне игры",
        # prompts
        "keys_hint": "   (? справка, q выход)",
        "prompt_attack": "Ваш ход. Защищается: {target} — выберите карту [{choices}]",
        "prompt_throw": "Подкинуть? Защищается: {target} [{choices}]",
        "prompt_done": "{key}=хватит",
        "prompt_beat": "Отбейте {card}",
        "prompt_beat_many": "Отбейте {card} (нужно отбить: {n})",
        "prompt_pick": "выберите карту [{choices}]",
        "prompt_pass": "{key}=перевод, защищается: {target} [{choices}]",
        "prompt_take": "{key}=взять",
        "prompt_continue": "нажмите Enter, чтобы продолжить ",
        "prompt_input": "  > ",
        "prompt_page": "  {counter} Enter — далее, q — назад  ",
        "prompt_back": "  Enter — назад  ",
        "prompt_choice": "  > [1-{n}, Enter — {default}] ",
        # errors and hints
        "err_not_a_number": "«{text}» — это не номер карты. Нажмите ? для справки.",
        "err_cannot_play": "Карту {n} сейчас сыграть нельзя.",
        "err_must_attack": "Атаку нужно начать картой.",
        "err_nothing_to_take": "Вы атакуете — брать нечего.",
        "err_not_an_option": "  «{text}» — такого варианта нет.",
        "err_which_card": "Какая карта? Добавьте номер, например {key}{n}.",
        "err_ambiguous": "{card} может и отбить, и перевести — b{n} отбить, p{n} перевести.",
        "hint_card": "Подсказка: {card}.",
        "hint_pass": "Подсказка: пас / взять.",
        # results
        "durak_you": "Вы — ДУРАК.",
        "durak_other": "{actor} — ДУРАК!",
        "draw": "Ничья — все вышли одновременно!",
        "went_out": "  Вышли из игры: {names}",
        "bouts": "  Сыграно раздач: {n}",
        "scoreboard": "  Счёт (кто сколько раз дурак):",
        "another_game": "Ещё партию?",
        "bye": "  До встречи.",
        # menu and setup
        "menu_title": "Дурак",
        "menu_play": "Играть",
        "menu_play_blurb": "выбрать настройки и раздать",
        "menu_learn": "Как играть",
        "menu_learn_blurb": "правила и немного истории",
        "menu_language": "Язык",
        "menu_language_blurb": "English / Русский",
        "menu_quit": "Выход",
        "menu_quit_blurb": "закрыть игру",
        "tagline": "Русская карточная игра на 2–6 человек — проигрывает последний с картами",
        "setup_title": "Настройки партии",
        "setup_mode": "Режим игры",
        "mode_classic": "Классический",
        "mode_classic_blurb": "защитник обязан отбить всё или взять карты",
        "mode_transfer": "С переводом",
        "mode_transfer_blurb": "защитник может перевести атаку картой того же достоинства",
        "setup_opponents": "Сколько соперников?",
        "opponents_option": "{n} {opponents}",
        "seats": "за столом {n}",
        "seats_deck": "за столом {n}, колода на {deck} {deck_cards}",
        "setup_difficulty": "Сложность",
        "easy": "Лёгкий",
        "easy_blurb": "ходит почти наугад",
        "normal": "Обычный",
        "normal_blurb": "сбрасывает мелочь и бережёт козыри",
        "hard": "Сложный",
        "hard_blurb": "ещё и считает отбой",
        "setup_language": "Язык",
        "deck_of": "колода {n}",
        "tutorial_end": "Вот и всё — удачи за столом.",
        "yes_no": "[Д/н]",
        "no_yes": "[д/Н]",
    },
}

# Commands accepted at a prompt. The single letters stay Latin in every
# language, because the prompt shows them literally ("t=взять", "p=перевод");
# the spelled-out Russian words are extra conveniences. Nothing here may
# overlap between sets — "в" once meant both "взять" and "выход", and quit
# was checked first, so taking cards quit the game instead.
YES_WORDS = {"y", "yes", "д", "да"}
NO_WORDS = {"n", "no", "н", "нет"}
QUIT_WORDS = {"q", "quit", "exit", "выход"}
HELP_WORDS = {"?", "h", "help", "справка"}
HINT_WORDS = {"s", "hint", "suggest", "подсказка"}
TAKE_WORDS = {"t", "take", "взять"}
# "p" means "no more throw-ins" at an attack prompt. At a defence prompt it
# means "pass the attack on", so ask_defense must check that intent first.
DONE_WORDS = {"d", "done", "p", "pass", "хватит"}
STOP_DEFENDING = {"d", "done"}
BACK_WORDS = {"q", "quit", "back", "b", "назад"}


class Translator:
    """Renders keys and :class:`Message` events in one language."""

    def __init__(self, lang: str = ENGLISH) -> None:
        if lang not in LANGUAGES:
            raise ValueError(f"unknown language: {lang}")
        self.lang = lang

    # -- lookup ------------------------------------------------------------

    # ``key`` is positional-only: several templates take a parameter literally
    # named "key" (the letter you press), which would otherwise collide.
    def __call__(self, key: str, /, **params: Any) -> str:
        return self.text(key, **params)

    def text(self, key: str, /, **params: Any) -> str:
        template = STRINGS[self.lang].get(key)
        if template is None:  # pragma: no cover - a missing key is a bug
            raise KeyError(f"no {self.lang} string for {key!r}")
        return template.format(**self._fill(template, params))

    def _fill(self, template: str, params: dict) -> dict:
        """Supply the derived parameters a template asks for."""
        filled = dict(params)
        n = params.get("n")
        if "{cards}" in template and isinstance(n, int):
            filled["cards"] = cards_noun(self.lang, n)
        if "{cards_nom}" in template and isinstance(n, int):
            filled["cards_nom"] = cards_noun_nom(self.lang, n)
        deck = params.get("deck")
        if "{deck_cards}" in template and isinstance(deck, int):
            # Derived from the deck size, not from {n}, which counts players.
            filled["deck_cards"] = cards_noun_nom(self.lang, deck)
        if "{opponents}" in template and isinstance(n, int):
            filled["opponents"] = opponents_noun(self.lang, n)
        return filled

    # -- events ------------------------------------------------------------

    def render(self, message: Message, you: str | None = None) -> str:
        """Turn an engine event into a sentence.

        When ``you`` names the player who acted, the second-person wording is
        used instead — "You take the cards" rather than "You takes the cards".
        """
        key = message.key
        if you is not None and message.params.get("actor") == you:
            if f"{key}.you" in STRINGS[self.lang]:
                key = f"{key}.you"
        return self.text(key, **message.params)

    # -- names -------------------------------------------------------------

    def rank_letters(self, ascii_only: bool = False) -> dict:
        """Face-card letters. ASCII mode always falls back to J/Q/K/A."""
        if ascii_only:
            return RANKS_EN
        return RANK_LETTERS[self.lang]

    def suit_name(self, suit: str) -> str:
        return SUIT_NAMES[self.lang][suit]

    def bot_names(self) -> list:
        return list(BOT_NAMES[self.lang])

    def default_name(self) -> str:
        return DEFAULT_NAME[self.lang]

    def is_second_person_name(self, name: str) -> bool:
        """True if this name is the stock "You", in either language."""
        return name.casefold() in {n.casefold() for n in DEFAULT_NAME.values()}


def detect_language(env: dict | None = None) -> str:
    """Guess from the locale, so Russian systems open in Russian."""
    env = os.environ if env is None else env
    for var in ("DURAK_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = (env.get(var) or "").strip().lower()
        if not value:
            continue
        if value.startswith("ru"):
            return RUSSIAN
        if value.startswith(("en", "c", "posix")):
            return ENGLISH
    return ENGLISH
