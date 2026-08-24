# durak

The Russian card game **Durak**, played in a terminal against AI opponents.
Pure ASCII/ANSI, no graphics, no dependencies — just the standard library.

Single player for now: you plus one to three computer opponents. Multiplayer
is not implemented yet, but the engine already deals with up to six seats, so
adding it later means adding a transport, not rewriting the rules.

```
  D U R A K
  Trump ♦ Diamonds   stock 15 (bottom card J♦)   beaten pile 6

  Players
  [+] You (you)   6 ▨▨▨▨▨▨  may throw in
  [A] Pyotr       5 ▨▨▨▨▨  attacking
  [D] Ivan        4 ▨▨▨▨  defending

  Table  3/6
  ┌─────┐ ┌─────┐ ┌─────┐
  │J    │ │J    │ │Q    │
  │  ♥  │ │  ♦  │ │  ♦  │
  │    J│ │    J│ │    Q│
  └─────┘ └─────┘ └─────┘
    ┌─────┐ ┌─────┐ ┌─────┐
    │Q    │ │A    │ │6    │
    │  ♥  │ │  ♦  │ │  ♣  │
    │    Q│ │    A│ │    6│
    └─────┘ └─────┘ └─────┘

  Log
    Pyotr adds Q♦.
    Ivan beats Q♦ with 6♣.

  Your hand (6)
  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
  │6    │ │9    │ │A    │ │7    │ │10   │ │Q    │
  │  ♠  │ │  ♠  │ │  ♠  │ │  ♥  │ │  ♥  │ │  ♣  │
  │    6│ │    9│ │    A│ │    7│ │   10│ │    Q│
  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘
     1       ·       3       ·       ·       6

  Throw in on Ivan? [1,3,6], d=done   (? help, q quit)
  >
```

## Play

No installation needed:

```sh
python3 -m durak
```

Or install it and get a `durak` command:

```sh
pip install -e .
durak
```

## Options

```
-p, --players {2,3,4}   total players, you included        (default 2)
-n, --name NAME         your name at the table             (default "You")
-d, --difficulty        easy | normal | hard               (default normal)
    --deck {20,24,36,52}  deck size                        (default 36)
    --seed N            reproducible shuffle
    --speed SECONDS     pause per opponent move, 0 = instant  (default 0.6)
    --rounds N          play exactly N games then stop     (default: ask)
    --ascii             no box drawing, no suit glyphs
    --no-color          no ANSI colour (also honours NO_COLOR)
    --no-clear          scroll instead of redrawing the screen
    --compact           one-line cards, for short terminals
    --simulate N        play N games bot-vs-bot and print the tally
```

Some combinations worth knowing:

```sh
durak -p 4 -d hard          # a full table of the strongest bots
durak --ascii --no-color    # for a terminal with no Unicode or colour
durak --seed 42 --speed 0   # deterministic and instant, handy for debugging
durak --simulate 1000 -p 3  # no UI: 1000 bot games, printed as a tally
```

## Commands during a game

| key         | meaning                                   |
| ----------- | ----------------------------------------- |
| `1` `2` `3` | play the card with that number            |
| `d`, enter  | done attacking / pass the throw-in        |
| `t`         | take the cards on the table               |
| `s`         | suggest a move                            |
| `?`         | help                                      |
| `q`         | quit                                      |

Cards you cannot legally play right now are dimmed and lose their number.

## The rules, as implemented

Standard *podkidnoy* ("throw-in") Durak:

- 36 cards, six to ace. Everyone is dealt six. The bottom card of the stock is
  turned face up — its suit is trump, and it is the last card anybody draws.
- Whoever holds the lowest trump attacks first.
- The defender must beat each attacking card with a **higher card of the same
  suit**, or with **any trump**. A trump is only beaten by a bigger trump.
- Once a card is on the table, every attacker (not just the first) may throw in
  more cards, but only of ranks already on the table. A bout is capped at six
  cards, and never more cards than the defender held when it began.
- Beat everything and the cards go to the beaten pile; the defender attacks
  next. Take, and you pick up everything on the table — including the cards you
  already beat — and the player after you attacks.
- After each bout everyone draws back up to six, attacker first, defender last.
- When the stock is gone, anyone who empties their hand is out. The last player
  still holding cards is the **durak**. Going out together is a draw.

## The opponents

| difficulty | behaviour                                                                                                                                                    |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `easy`     | picks legal moves more or less at random                                                                                                                       |
| `normal`   | sheds its cheapest cards, hoards trumps, and takes a small pile rather than burn a high trump on a cheap card                                                   |
| `hard`     | also remembers the beaten pile, so it knows when a card of its own can no longer be beaten by anybody and leads those in the endgame; and it spots ranks it cannot survive being fed, and takes early instead |

The `hard` tactics were chosen by measurement, not by taste. Every combination
of candidate heuristics was played thousands of hands against plain `normal`,
and only the ones that actually won more often were kept — two others
(preferring to lead ranks it held duplicates of, and refusing to hand over high
plain cards) measured *worse* and were dropped. Over 3000 seeded hands the
ladder comes out as hard > normal > easy:

```sh
python3 -m durak --simulate 2000 -d hard    # try it yourself
```

## Layout

```
durak/cards.py     cards, deck, and the "what beats what" rule
durak/engine.py    all state and every rule; players only ever pick from legal moves
durak/players.py   the Player interface and the interactive player
durak/ai.py        the computer opponents
durak/ui.py        board drawing and input parsing
durak/render.py    ASCII/ANSI primitives — knows nothing about Durak
durak/cli.py       argument parsing and the match loop
```

The engine never reads from the terminal and the UI never enforces a rule, so
the same engine can back a networked game later.

## Tests

```sh
pip install -e '.[dev]'
python3 -m pytest
```

74 tests covering the card rules, bout resolution, drawing and elimination,
the AI's tactics and relative strength, rendering, and input parsing. The AI
strength tests play thousands of hands but use fixed seeds, so they are
deterministic rather than flaky.
