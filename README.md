# BusBidder Spain

A command-line tool that ranks fictional Spanish long-distance bus offers
for 5 different traveller profiles, and lets a traveller book seats on
one of the ranked offers. Built for ACIT4420 exam candidate-806.

All data (companies, destinations, prices, offers) is synthetic,
generated for this course project only. No real company, traveller, or
personal data is used anywhere in this project.

## 1. Requirements

- Python 3.9 or newer (built and tested on Python 3.13). No third-party
  packages are needed - see `requirements.txt`.

## 2. Folder structure

```
busbidder/
├── README.md                  <- this file
├── requirements.txt            <- No third-party packages needed
├── VERSION.txt                 <- build number, increases by 1 each delivered build
├── data/                        <- input data the program reads (and writes to)
│   ├── destinations.csv         <- the 15 Spanish cities offers can go to
│   ├── companies.csv            <- the fictional bus companies
│   ├── offers.csv                <- the main set of valid, bookable offers
│   ├── offers_invalid.csv        <- deliberately broken rows, used to prove validation works
│   └── bookings.csv              <- created automatically the first time you run "book"
├── logs/                         <- created automatically; plain-text run logs
│   └── app.log
├── output/                       <- created automatically; the HTML report from "search"
│   └── results.html
├── scripts/
│   └── generate_dataset.py       <- one-off script that built the data/*.csv files
└── busbidder/                     <- the actual application code (a Python package)
    ├── __init__.py                 <- empty; just marks this folder as a Python package
    ├── models.py                   <- plain data containers: Destination, Company, Offer
    ├── exceptions.py                <- the two custom error types used everywhere else
    ├── loaders.py                   <- reads and validates the 3 input CSV files (Layer 1)
    ├── profiles.py                   <- the 5 fixed traveller profiles and their weights
    ├── filters.py                     <- checks which offers meet a profile's hard rules (Layer 2)
    ├── scoring.py                      <- turns surviving offers into a 0-100 ranked score
    ├── explain.py                       <- turns the winning offer's numbers into one sentence
    ├── booking.py                        <- seat-booking rules and saving to bookings.csv (Layer 4)
    ├── main.py                            <- the command-line entry point (search + book)
    ├── render.py                           <- writes the combined simple HTML report
    └── tests.py                             <- the automated test suite (40 tests)
```

## 3. What each file actually does

| File | What it is for |
|---|---|
| `main.py` | The program you actually run. Reads the 3 data files once, then does either a `search` (rank offers for all 5 profiles) or a `book` (reserve seats on one offer), based on which subcommand you typed. |
| `models.py` | Defines what a `Destination`, a `Company`, and an `Offer` *are* - just plain containers of fields, no logic. Every other file builds on these. |
| `exceptions.py` | Defines the two custom error types (`InvalidIdentifierError`, `InvalidRecordError`) that every validation step in the project raises, instead of letting the program crash with a generic Python error. |
| `loaders.py` | Reads `destinations.csv`, `companies.csv`, and `offers.csv` and checks every single row is valid (right format, right ranges, known IDs) before the rest of the program ever sees it. Rejects bad rows one at a time, with a reason, instead of crashing the whole run. |
| `profiles.py` | Holds the 5 fixed traveller profiles (Practical, Budget-friendly, Business-rush, Review-focused, Leisure) - each one's hard rules (e.g. max budget) and its weighting across 8 ranking criteria. |
| `filters.py` | For one profile, checks which offers survive both the universal rules (e.g. must have a free seat) and that profile's own hard rules (e.g. must be refundable). Offers that fail are dropped before scoring. |
| `scoring.py` | Takes the offers that survived `filters.py` and scores each one 0-100 per criterion (price, transfers, duration, etc.), using a decorator-based registry so a new criterion can be added later without touching this file's other code. Combines the 8 scores using the profile's weights into one final ranked list. |
| `explain.py` | Takes the single top-ranked offer and turns its strongest and weakest criteria into one plain-English sentence, so a traveller sees *why* it won, not just a number. |
| `booking.py` | Validates a booking request (1-6 seats, enough seats actually still free once existing bookings are subtracted), builds a booking record, and appends it to `data/bookings.csv`. |
| `render.py` | Takes the exact same numbers `main.py` already calculated for `search` and writes them out again as one combined HTML page (`output/results.html`), so you can see all 5 profiles side by side in a browser. Never recalculates anything itself. |
| `tests.py` | The automated test suite - 40 tests covering normal use, invalid input, missing files, and edge cases for every file above. See section 5 below. |
| `scripts/generate_dataset.py` | Not part of the running app - a separate one-off script that generated the `data/*.csv` files using a fixed random seed, so the dataset is reproducible. You do not need to run this to use the app; it is included to show how the data was made. |

## 4. How to run it

Open a terminal, move into this folder (the one this README is in), and
run one of the two commands below.

### Search for offers

```
python3 -m busbidder.main search --destination Barcelona --date-from 2026-11-25 --date-to 2026-12-05
```

- `--destination` accepts either a destination **name** (e.g. `Barcelona`,
  not case-sensitive) or a destination **ID** (e.g. `D02`). Run with an
  unrecognised destination to see the full list of valid ID-name pairs.
- `--date-from` / `--date-to` must be in `YYYY-MM-DD` format, and
  `--date-from` cannot be in the past.

This prints a ranked top-5 list for each of the 5 traveller profiles
straight to the terminal, and also writes a combined HTML version of the
same results to `output/results.html` (open that file in any browser).

Example output (shortened):

```
============================================================
Profile: Practical
============================================================
2 offer(s) matched. Top 2 shown below:
  1. OFR-2026-0010  VerdeBus  EUR 44.87  score 70.0
  2. OFR-2026-0008  Camino Express  EUR 50.53  score 65.0

For the Practical profile, OFR-2026-0010 is the top-ranked offer. Its
advantages are a low price, few transfers, this profile's preferred seat
type. Its main disadvantage is a long journey time. This is only the
best choice under the Practical profile's own constraints and weights -
a different profile could rank this same offer lower.
```

### Book seats on an offer

Pick an `offer_id` from a `search` result above, then run:

```
python3 -m busbidder.main book --offer-id OFR-2026-0010 --seats 2
```

- `--seats` must be a whole number from 1 to 6, and no more than the
  seats still actually free on that offer (existing bookings are
  subtracted automatically).

Example output:

```
Booking confirmed.
  Booking reference: BKG-2026-000001
  Offer: OFR-2026-0010 (VerdeBus) to D02
  Seats booked: 2
  Total price: EUR 89.74
  Booked on: 2026-11-18
```

This appends one row to `data/bookings.csv` (the file is created
automatically the first time you book something).

### Run the automated tests

```
python3 -m busbidder.tests
```

Add `-v` for a detailed, test-by-test listing:

```
python3 -m busbidder.tests -v
```

You should see `OK` and `Ran 40 tests` at the end, with no failures.

## 5. Notes on the data

- `data/offers.csv` is the real dataset the app uses - 92 valid, fictional
  bus offers across 15 Spanish destinations and several companies.
- `data/offers_invalid.csv` is **not** used by `main.py` at all. It
  exists only to prove the validation in `loaders.py` actually works -
  `tests.py` loads this file and checks that every single row in it is
  correctly rejected, each for a different reason (negative price, bad
  rating, unknown destination, badly formatted ID, impossible arrival
  time, negative seat count).
- Every offer's `travel_date` is generated relative to *today's date* at
  the time `scripts/generate_dataset.py` was run (today + roughly 7 to
  17 days), not a fixed calendar date. This keeps the dataset usable no
  matter when you run the app, but it is the one field that will not be
  byte-for-byte identical if you regenerate the dataset on a different
  day - everything else in the dataset is fully reproducible from the
  fixed random seed.
