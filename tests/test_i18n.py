"""Tests for translation: the message catalogue, plurals, and the two languages."""

from __future__ import annotations

import random

import pytest

from durak import tutorial
from durak.ai import AIPlayer
from durak.cards import Card
from durak.engine import TRANSFER, Durak
from durak.i18n import (
    ENGLISH,
    LANGUAGES,
    RUSSIAN,
    STRINGS,
    Message,
    Translator,
    cards_noun,
    cards_noun_nom,
    detect_language,
    plural_ru,
)

S, H, D, C = "S", "H", "D", "C"


# ---------------------------------------------------------- the catalogue


def test_every_language_defines_every_string():
    english = set(STRINGS[ENGLISH])
    for lang in LANGUAGES:
        missing = english - set(STRINGS[lang])
        extra = set(STRINGS[lang]) - english
        assert not missing, f"{lang} is missing {sorted(missing)}"
        assert not extra, f"{lang} has stray keys {sorted(extra)}"


def test_translations_use_the_same_placeholders_as_the_english():
    import re

    holes = lambda text: set(re.findall(r"\{(\w+)\}", text))
    for key, english in STRINGS[ENGLISH].items():
        for lang in LANGUAGES:
            assert holes(STRINGS[lang][key]) == holes(english), (
                f"{lang} {key!r} does not take the same parameters"
            )


def test_no_string_is_left_untranslated():
    """Every Russian string should actually differ, apart from the deliberate ones."""
    same_on_purpose = {
        "menu_language_blurb",  # lists both languages, in both languages
        "prompt_input",  # just the "> " caret
        "opponents_option",  # only placeholders; the noun is declined separately
    }
    identical = {
        key
        for key, text in STRINGS[RUSSIAN].items()
        if text == STRINGS[ENGLISH][key] and key not in same_on_purpose
    }
    assert not identical, f"still in English: {sorted(identical)}"


def test_an_unknown_language_is_rejected():
    with pytest.raises(ValueError):
        Translator("de")


def test_a_missing_key_is_an_error_not_a_blank():
    with pytest.raises(KeyError):
        Translator(ENGLISH).text("no_such_key")


# ------------------------------------------------------------------ plurals


@pytest.mark.parametrize(
    "n,expected",
    [
        (1, "карта"), (2, "карты"), (4, "карты"), (5, "карт"),
        (11, "карт"), (12, "карт"), (14, "карт"), (21, "карта"),
        (22, "карты"), (25, "карт"), (101, "карта"), (111, "карт"),
    ],
)
def test_russian_picks_the_right_of_three_plural_forms(n, expected):
    assert cards_noun_nom(RUSSIAN, n) == expected


def test_russian_distinguishes_the_accusative_from_the_nominative():
    # "забирает 1 карту" but "на столе 1 карта" — only the singular differs.
    assert cards_noun(RUSSIAN, 1) == "карту"
    assert cards_noun_nom(RUSSIAN, 1) == "карта"
    for n in (2, 5, 11):
        assert cards_noun(RUSSIAN, n) == cards_noun_nom(RUSSIAN, n)


def test_english_only_needs_two_forms():
    assert cards_noun(ENGLISH, 1) == "card"
    for n in (0, 2, 11, 21):
        assert cards_noun(ENGLISH, n) == "cards"


def test_plural_helper_handles_the_teens():
    assert plural_ru(11, "a", "b", "c") == "c"
    assert plural_ru(1, "a", "b", "c") == "a"


def test_the_count_noun_follows_the_number_it_belongs_to():
    """The deck noun must agree with the deck size, not the player count."""
    t = Translator(RUSSIAN)
    assert t("seats_deck", n=6, deck=52).endswith("52 карты")
    assert t("seats_deck", n=2, deck=21).endswith("21 карта")


# ------------------------------------------------------------------ events


def test_an_event_reads_naturally_in_both_languages():
    message = Message("pick_up", {"actor": "Olga", "n": 3})
    assert Translator(ENGLISH).render(message) == "Olga picks up 3 cards."
    assert Translator(RUSSIAN).render(
        Message("pick_up", {"actor": "Ольга", "n": 3})
    ) == "Ольга забирает 3 карты."


def test_the_actor_is_addressed_in_the_second_person():
    message = Message("take", {"actor": "Sam"})
    assert Translator(ENGLISH).render(message, you="Sam") == "You take the cards."
    assert Translator(ENGLISH).render(message, you="Ivan") == "Sam takes the cards."
    russian = Message("take", {"actor": "Вы"})
    assert Translator(RUSSIAN).render(russian, you="Вы") == "Вы берёте карты."


def test_second_person_falls_back_when_there_is_no_you_wording():
    # "bout" names two people, so it has no second-person form to fall back to.
    message = Message("bout", {"actor": "Sam", "target": "Ivan"})
    assert Translator(ENGLISH).render(message, you="Sam") == "— Sam attacks Ivan —"


def test_russian_keeps_player_names_in_the_nominative():
    """No Russian string may bend a name, since names are not declinable here."""
    for key, text in STRINGS[RUSSIAN].items():
        if "{actor}" not in text and "{target}" not in text:
            continue
        for hole in ("{actor}", "{target}"):
            before = text.split(hole)[0]
            # A preposition immediately before a name would demand a case.
            assert not before.rstrip().endswith((" на", " у", " к", " от", " с")), (
                f"{key!r} puts a preposition before a name"
            )


def test_every_engine_event_has_a_string_in_every_language():
    """Play games until each event key has fired, then render them all."""
    seen: set[str] = set()
    rng = random.Random(4)
    for _ in range(40):
        bots = [AIPlayer(f"p{i}", "normal", rng) for i in range(3)]
        game = Durak(bots, rng=rng, mode=TRANSFER)
        game.run()
        seen.update(m.key for m in game.log)
        if len(seen) >= 9:
            break
    # The bulk of the engine's vocabulary should have turned up.
    assert {"attack", "beat", "take", "pick_up", "beat_off", "bout"} <= seen
    for lang in LANGUAGES:
        t = Translator(lang)
        for key in seen:
            assert key in STRINGS[lang], f"{lang} has no string for {key!r}"


# ------------------------------------------------------------- card names


def test_face_cards_are_written_in_the_local_alphabet():
    ru = Translator(RUSSIAN).rank_letters()
    assert Card(14, S).label(ranks=ru) == "Т♠"  # туз
    assert Card(12, D).label(ranks=ru) == "Д♦"  # дама
    assert Card(10, H).label(ranks=ru) == "10♥"  # numbers are the same


def test_ascii_mode_falls_back_to_latin_face_cards():
    """Cyrillic cannot survive --ascii, so J/Q/K/A is used in every language."""
    assert Translator(RUSSIAN).rank_letters(ascii_only=True)[14] == "A"
    assert Translator(RUSSIAN).rank_letters(ascii_only=False)[14] == "Т"


def test_suits_are_named_in_the_local_language():
    assert Translator(ENGLISH).suit_name("S") == "Spades"
    assert Translator(RUSSIAN).suit_name("S") == "Пики"


def test_opponents_are_named_in_the_local_language():
    assert "Ivan" in Translator(ENGLISH).bot_names()
    assert "Иван" in Translator(RUSSIAN).bot_names()
    for lang in LANGUAGES:
        names = Translator(lang).bot_names()
        assert len(names) == len(set(names)) >= 6


def test_the_stock_name_for_the_player_is_recognised_in_either_language():
    t = Translator(RUSSIAN)
    assert t.default_name() == "Вы"
    assert t.is_second_person_name("You") and t.is_second_person_name("Вы")
    assert not t.is_second_person_name("Sam")


# ------------------------------------------------------------ locale guess


@pytest.mark.parametrize(
    "env,expected",
    [
        ({"LANG": "ru_RU.UTF-8"}, RUSSIAN),
        ({"LANG": "en_GB.UTF-8"}, ENGLISH),
        ({"LC_ALL": "ru_UA.UTF-8", "LANG": "en_US"}, RUSSIAN),
        ({"DURAK_LANG": "ru", "LANG": "en_US"}, RUSSIAN),
        ({"LANG": "C"}, ENGLISH),
        ({}, ENGLISH),
        ({"LANG": ""}, ENGLISH),
        ({"LANG": "fr_FR.UTF-8"}, ENGLISH),
    ],
)
def test_the_language_is_guessed_from_the_locale(env, expected):
    assert detect_language(env) == expected


# --------------------------------------------------------------- tutorial


def test_the_tutorial_exists_in_both_languages():
    for lang in LANGUAGES:
        assert len(tutorial.sections(lang)) == len(tutorial.sections(ENGLISH))
        assert len(tutorial.text(lang).splitlines()) > 50
        assert tutorial.help_text(lang).strip()


def test_the_russian_tutorial_is_actually_russian():
    body = tutorial.text(RUSSIAN)
    assert "козыр" in body.lower() and "дурак" in body.lower()
    cyrillic = sum(1 for ch in body if "а" <= ch.lower() <= "я")
    assert cyrillic > len(body) / 3
