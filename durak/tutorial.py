"""The in-game tutorial and help, in every language the game speaks.

Plain text with a couple of drawn examples rather than generated art, so it
reads the same in --ascii mode and in a narrow terminal.
"""

from __future__ import annotations

from .i18n import ENGLISH, RUSSIAN

EN_HISTORY = """\
A little history
================

  Durak (дурак) is Russian for "fool", and it is the fool the game is named
  after: there is no winner to speak of, only a loser. Play continues until
  one player is left holding cards after everyone else has run out, and that
  player is the durak. Tradition is unkind to them — in many households the
  durak deals the next hand, and is teased until somebody else takes the
  title.

  It is far and away the most played card game in Russia and across the
  former Soviet Union, the sort of game learned from family rather than from
  a rulebook. That is also why it has so many variants: the version played in
  one household often differs from the next, and the rules below are one
  common set rather than the definitive ones.

  Durak belongs to a family sometimes called "beating games", where players
  answer each other's cards directly instead of following suit into tricks
  that are scored. It is unusual among card games in having no score at all,
  and in reversing the usual goal — you are not trying to win, you are trying
  not to be last.
"""

EN_BASICS = """\
The basics
==========

  The deck is 36 cards: 6, 7, 8, 9, 10, J, Q, K, A in each of the four suits.
  Everyone is dealt six. The remaining cards form the stock, and the bottom
  card of the stock is turned face up — its suit is TRUMP for the whole game,
  and that card is the very last one anybody draws.

  Trumps beat everything outside their own suit, which makes them the cards
  worth keeping. In this game they are outlined in cyan and sit at the far
  LEFT of your hand, so they are always in the same place.

  Whoever holds the lowest trump attacks first.
"""

EN_BEATING = """\
Beating a card
==============

  The attacker plays a card. You, the defender, must beat it with either:

    * a HIGHER card of the SAME suit, or
    * ANY trump (if the attacking card is not itself a trump).

  A trump can only be beaten by a higher trump. Nothing beats a card of a
  different plain suit.

  Say trumps are spades, and the attack is the 9 of hearts:

      9♥  attacked with
      ───────────────────────────────────
      10♥  beats it   (same suit, higher)
       7♠  beats it   (a trump)
       8♥  does not   (same suit, lower)
       A♦  does not   (different plain suit — an Ace is no help here)

  If you cannot or will not beat it, you TAKE: every card on the table goes
  into your hand, including any you had already beaten this round.
"""

EN_THROWING_IN = """\
Throwing in
===========

  Once a card is on the table, the attackers may keep adding more — but only
  cards whose RANK already appears on the table, on either side.

      table:   6♥ beaten by 10♥
      ───────────────────────────────────
      may add: any 6, or any 10
      may not: anything else

  In a game of three or more, every other player gets to throw in too, not
  just the player who attacked. A round stops at six cards, and never has
  more cards than the defender held when it began.

  Beat everything and the cards are discarded for good, and you attack next.
  Take them and the turn passes you by.
"""

EN_TRANSFER = """\
Transfer mode
=============

  An optional rule, chosen at the start. Before you have beaten anything, if
  you hold a card of the SAME RANK as the card attacking you, you may add it
  and pass the whole attack to the next player clockwise:

      6♠ is played at you, and you hold a 6♦
      ───────────────────────────────────
      play the 6♦ and both sixes move on to the next player,
      who now has to beat TWO cards

  They may pass it on again if they hold the rank too. With two players it
  goes back to your attacker, who now has to beat what they just played you.

  Two limits: you cannot pass once you have beaten a card this round, and you
  cannot pass onto somebody holding fewer cards than they would have to beat.
"""

EN_ENDING = """\
How it ends
===========

  After each round everyone draws back up to six cards, attacker first and
  defender last, until the stock runs out. Once it is empty there are no more
  refills, and anyone who plays their last card is out and safe.

  The last player still holding cards is the DURAK. If the last players go
  out together, it is a draw.
"""

EN_PLAYING = """\
Playing this version
====================

  Your cards are numbered; type a number to play that card. Cards you cannot
  legally play right now are dimmed and lose their number, so anything still
  showing a number is a legal move.

    1 2 3 ...   play the card with that number
    d, enter    done attacking (pass up the chance to throw in)
    t           take the cards on the table
    p, p3       pass the attack on          (transfer mode only)
    b3          beat with card 3, when that card could also pass it on
    s           suggest a move
    ?           this help
    q           quit

  A tip worth knowing: taking cards is not always a loss. Swallowing one
  cheap card early can be much better than spending the Ace of trumps to
  avoid it.
"""

RU_HISTORY = """\
Немного истории
===============

  Слово «дурак» и дало игре имя: победителя здесь, по сути, нет — есть
  только проигравший. Игра идёт до тех пор, пока у всех, кроме одного, не
  закончатся карты. Тот, кто остался с картами на руках, и есть дурак.
  Обходятся с ним не слишком любезно: во многих домах дурак раздаёт
  следующую партию, и подшучивают над ним, пока кто-нибудь другой не займёт
  его место.

  Это самая популярная карточная игра в России и на всём постсоветском
  пространстве — из тех, которым учатся дома, а не по книжке правил. Отсюда
  и множество вариантов: в каждой семье играют немного по-своему, и правила
  ниже — один из распространённых вариантов, а не единственно верный.

  Дурак относится к семейству так называемых «игр с побитием», где игроки
  отвечают на карты друг друга напрямую, а не собирают взятки. Среди
  карточных игр он необычен тем, что в нём вообще нет очков, и тем, что цель
  перевёрнута: вы стараетесь не выиграть, а не остаться последним.
"""

RU_BASICS = """\
Основы
======

  В колоде 36 карт: 6, 7, 8, 9, 10, В, Д, К, Т каждой масти. Каждому
  раздаётся шесть. Остальные образуют колоду, а нижняя карта колоды
  открывается — её масть становится КОЗЫРЕМ на всю партию, и эта карта
  достанется кому-то самой последней.

  Козырь бьёт любую карту другой масти, поэтому козыри стоит беречь. В этой
  игре они обведены голубым и стоят в самом ЛЕВОМ краю вашей руки, так что
  всегда находятся на одном и том же месте.

  Первым ходит тот, у кого младший козырь.
"""

RU_BEATING = """\
Как бить карту
==============

  Атакующий кладёт карту. Вы, защищаясь, обязаны побить её:

    * СТАРШЕЙ картой ТОЙ ЖЕ масти, либо
    * ЛЮБЫМ козырем (если атакующая карта сама не козырь).

  Козырь бьётся только более старшим козырем. Карта другой некозырной масти
  не бьёт ничего.

  Допустим, козыри — пики, а ходят девяткой червей:

      атакуют 9♥
      ───────────────────────────────────
      10♥  бьёт      (та же масть, старше)
       7♠  бьёт      (козырь)
       8♥  не бьёт   (та же масть, но младше)
       Т♦  не бьёт   (другая некозырная масть — туз тут не поможет)

  Если побить нечем или не хочется — вы БЕРЁТЕ: все карты со стола уходят к
  вам в руку, включая те, которые вы уже успели побить в этом кругу.
"""

RU_THROWING_IN = """\
Подкидывание
============

  Как только на столе появилась карта, атакующие могут подкидывать ещё — но
  только карты того ДОСТОИНСТВА, которое уже есть на столе, с любой стороны.

      на столе:  6♥ побита 10♥
      ───────────────────────────────────
      можно:     любую шестёрку или любую десятку
      нельзя:    всё остальное

  Втроём и больше подкидывать могут все, а не только тот, кто ходил. В одном
  кругу не бывает больше шести карт, и никогда больше, чем было на руках у
  защищающегося в начале круга.

  Отбились — карты уходят в отбой навсегда, и следующий ход ваш. Взяли —
  ход переходит мимо вас.
"""

RU_TRANSFER = """\
Режим с переводом
=================

  Необязательное правило, выбирается в начале. Пока вы ещё ничего не побили,
  если у вас есть карта ТОГО ЖЕ ДОСТОИНСТВА, что и карта, которой вас
  атакуют, вы можете подложить её и перевести всю атаку на следующего игрока
  по часовой стрелке:

      вам сходили 6♠, а у вас есть 6♦
      ───────────────────────────────────
      кладёте 6♦ — и обе шестёрки уходят следующему игроку,
      которому теперь надо отбить ДВЕ карты

  Он может перевести дальше, если у него тоже есть такая карта. Вдвоём атака
  возвращается к тому, кто ходил: теперь ему бить то, чем он только что
  пошёл.

  Два ограничения: перевести нельзя, если вы уже побили карту в этом кругу,
  и нельзя переводить на того, у кого карт меньше, чем ему придётся бить.
"""

RU_ENDING = """\
Чем всё кончается
=================

  После каждого круга все добирают до шести карт — сначала атакующий,
  защищающийся последним, — пока колода не кончится. Когда она пуста, добирать
  больше нечего, и тот, кто сыграл последнюю карту, выходит из игры.

  Последний, у кого остались карты, и есть ДУРАК. Если последние игроки
  выходят одновременно — ничья.
"""

RU_PLAYING = """\
Как играть в этой версии
========================

  Ваши карты пронумерованы: наберите номер, чтобы сходить этой картой. Карты,
  которыми сейчас ходить нельзя, показаны тускло и без номера — значит, любая
  карта с номером является допустимым ходом.

    1 2 3 ...   сходить картой с этим номером
    d, Enter    хватит подкидывать
    t           взять карты со стола
    p, p3       перевести атаку            (только в режиме с переводом)
    b3          побить картой 3, если ею же можно и перевести
    s           подсказка
    ?           эта справка
    q           выход

  Небольшой совет: взять карты — не всегда поражение. Иногда проглотить одну
  мелкую карту в начале куда выгоднее, чем тратить на неё козырного туза.
"""

SECTIONS = {
    ENGLISH: (
        EN_HISTORY,
        EN_BASICS,
        EN_BEATING,
        EN_THROWING_IN,
        EN_TRANSFER,
        EN_ENDING,
        EN_PLAYING,
    ),
    RUSSIAN: (
        RU_HISTORY,
        RU_BASICS,
        RU_BEATING,
        RU_THROWING_IN,
        RU_TRANSFER,
        RU_ENDING,
        RU_PLAYING,
    ),
}

HELP = {
    ENGLISH: """
How to play
-----------
  Beat the attacking card with a higher card of the SAME suit, or with any
  trump. A trump can only be beaten by a bigger trump.
  Attackers may keep throwing in cards whose rank already appears on the
  table, up to six cards or the number the defender started with.
  Beat everything and the cards are discarded; take them and the next player
  attacks instead. The last player still holding cards is the durak.

  In TRANSFER mode you have a third option while defending: if you hold a card
  of the same rank as the card(s) attacking you, and you have not beaten
  anything yet, you can add it and pass the whole attack to the next player
  clockwise. With two players it goes back to your attacker.

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
""",
    RUSSIAN: """
Как играть
----------
  Побейте атакующую карту старшей картой ТОЙ ЖЕ масти или любым козырем.
  Козырь бьётся только более старшим козырем.
  Атакующие могут подкидывать карты того достоинства, которое уже есть на
  столе — до шести карт и не больше, чем было на руках у защищающегося.
  Отбились — карты уходят в отбой; взяли — ход переходит к следующему.
  Последний, у кого остались карты, и есть дурак.

  В режиме С ПЕРЕВОДОМ у защищающегося есть третий вариант: если у вас есть
  карта того же достоинства, что и атакующая, и вы ещё ничего не побили,
  можно подложить её и перевести всю атаку на следующего игрока. Вдвоём
  атака возвращается к тому, кто ходил.

Команды
-------
  1 2 3 ...   сходить картой с этим номером
  d / Enter   хватит подкидывать
  t           взять карты со стола
  p / p3      перевести атаку (только в режиме с переводом)
  b3          побить картой 3, если ею же можно и перевести
  s           подсказка
  ?           эта справка
  q           выход
""",
}


def sections(lang: str = ENGLISH) -> tuple:
    return SECTIONS[lang]


def help_text(lang: str = ENGLISH) -> str:
    return HELP[lang]


def text(lang: str = ENGLISH) -> str:
    """The whole tutorial as one string."""
    return "\n".join(SECTIONS[lang])
