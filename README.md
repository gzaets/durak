# durak

The Russian card game **Durak**, played in a terminal against AI opponents.
Pure ASCII/ANSI, no graphics, no dependencies — just the standard library.

Single player for now: you plus one to three computer opponents, in either of
two modes — **classic**, or **transfer**, where a defender can pass the attack
on to the next player instead of beating it. Multiplayer is not implemented
yet, but the engine already deals with up to six seats, so adding it later
means adding a transport, not rewriting the rules.

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

It opens with a setup screen asking for the mode, the number of opponents and
the difficulty:

```
  Game mode
   * 1) Classic — the defender must beat every card or take them all
     2) Transfer — the defender may also pass the attack on with a matching rank
  > [1-2, enter for 1]

  How many opponents?
   * 1) 1 opponent — 2 at the table
     2) 2 opponents — 3 at the table
     3) 3 opponents — 4 at the table
  > [1-3, enter for 1]
```

Anything you pass as a flag is not asked about, and `--defaults` (or a
non-interactive stdin) skips the questions entirely.

Or install it and get a `durak` command:

```sh
pip install -e .
durak
```

## Options

```
-o, --opponents {1,2,3} number of computer opponents       (asked if omitted)
-p, --players {2,3,4}   total players, you included        (same thing, +1)
-m, --mode MODE         classic | transfer                 (asked if omitted)
-n, --name NAME         your name at the table             (default "You")
-d, --difficulty        easy | normal | hard               (asked if omitted)
-y, --defaults          skip the setup questions
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
durak -o 3 -d hard -m transfer   # a full table of the strongest bots, transfer mode
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
| `p`, `p3`   | pass the attack on (transfer mode)        |
| `b3`        | beat with card 3, when it could also pass |
| `s`         | suggest a move                            |
| `?`         | help                                      |
| `q`         | quit                                      |

Cards you cannot legally play right now are dimmed and lose their number.

`b3` / `p3` exist because one card can sometimes do both: if the six of hearts
is attacking you and trumps are spades, your six of spades *beats* it and is
*also* a legal transfer. The prompt asks which you meant only in that case.

## The rules, as implemented

Standard *podkidnoy* ("throw-in") Durak — throwing in is part of both modes:

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

### Transfer mode

Picked in the setup screen or with `--mode transfer`. It adds one option for
the defender, and changes nothing else:

- Before you have beaten anything, if you hold a card of the **same rank** as
  the card(s) attacking you, you may play it and pass the whole attack to the
  next player clockwise. They now have to beat every card on the table.
- They may pass it on again if they hold the rank too, and so on around the
  table.
- With two players it goes back to your attacker, who now has to beat what they
  just played you. Whoever passed it becomes the attacker.
- Two limits: you cannot pass once you have beaten a card in this bout (playing
  a card commits you to the defence), and you cannot pass onto somebody holding
  fewer cards than they would then have to beat.

A note on the name: this variant is *perevodnoy* (переводной, "transfer"),
while *podkidnoy* (подкидной) refers to the throwing-in of matching ranks by
the other attackers — which happens in **both** modes here, so naming the mode
"throw-in" would not distinguish it. `--mode` accepts `transfer`, `perevodnoy`,
`podkidnoy` and `throw-in` all the same, and `classic`/`traditional` for the
other one.

## The opponents

| difficulty | behaviour                                                                                                                                                    |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `easy`     | picks legal moves more or less at random                                                                                                                       |
| `normal`   | sheds its cheapest cards, hoards trumps, and takes a small pile rather than burn a high trump on a cheap card                                                   |
| `hard`     | also remembers the beaten pile, so it knows when a card of its own can no longer be beaten by anybody and leads those in the endgame; and it spots ranks it cannot survive being fed, and takes early instead |

In transfer mode every bot above `easy` also weighs passing the attack on
against blocking it, on the same card-cost yardstick: passing gets you out of
the bout, so it wins ties, but it loses to a clearly cheaper block. The size of
that tie-break was swept the same way as the other tactics — but unlike them it
came out **flat**: anything from 0 to 3 plays the same within noise, so the
default is simply a value in that range. Passing *whenever possible* is never
better, but how much worse is seed-dependent (50.3% and 54.2% loss over two
1000-hand samples), so no firm margin is claimed for it — which is why the
suite tests the behaviour rather than the win rate.

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
durak/engine.py    all state and every rule, both modes; players only ever pick from legal moves
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
