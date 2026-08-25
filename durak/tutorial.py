"""The in-game tutorial: what Durak is, where it comes from, and how to play.

Kept as plain text with a couple of drawn examples rather than generated art,
so it reads the same in --ascii mode and in a narrow terminal.
"""

from __future__ import annotations

HISTORY = """\
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

BASICS = """\
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

BEATING = """\
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

THROWING_IN = """\
Throwing in
===========

  Once a card is on the table, the attackers may keep adding more — but only
  cards whose RANK already appears on the table, on either side.

      table:   6♥ beaten by 10♥
      ───────────────────────────────────
      may add: any 6, or any 10
      may not: anything else

  In a game of three or four, every other player gets to throw in too, not
  just the player who attacked. A round stops at six cards, and never has
  more cards than the defender held when it began.

  Beat everything and the cards are discarded for good, and you attack next.
  Take them and the turn passes you by.
"""

TRANSFER = """\
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

ENDING = """\
How it ends
===========

  After each round everyone draws back up to six cards, attacker first and
  defender last, until the stock runs out. Once it is empty there are no more
  refills, and anyone who plays their last card is out and safe.

  The last player still holding cards is the DURAK. If the last players go
  out together, it is a draw.
"""

PLAYING = """\
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

SECTIONS = (HISTORY, BASICS, BEATING, THROWING_IN, TRANSFER, ENDING, PLAYING)


def text() -> str:
    """The whole tutorial as one string."""
    return "\n".join(SECTIONS)
