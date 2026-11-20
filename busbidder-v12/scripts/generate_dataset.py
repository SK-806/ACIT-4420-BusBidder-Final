"""
This file builds the fictional BusBidder Spain dataset (companies,
destinations, offers) using a fixed random seed, so the same command
always produces the exact same data files. That reproducibility is a
deliberate design choice (see the report's traceability section): anyone
re-running this script gets byte-identical output, which is what lets the
rest of the pipeline (filtering, scoring, booking) be demonstrated and
re-checked consistently.

It writes four files into data/:
  destinations.csv   - the 15 destinations served from the Madrid hub
  companies.csv       - the 5 fictional companies and their "personality"
                         parameters (used to generate realistic offers)
  offers.csv          - the main, valid offer dataset
  offers_invalid.csv  - a small, deliberately broken file (bad price,
                         out-of-range rating, unknown destination,
                         incorrect_ID, arrival before departure, negative
                         seats) used later to demonstrate that loaders.py
                         actually rejects and logs bad records instead of
                         crashing or silently accepting them.

Every offer also now includes two simple, randomly-chosen fields added
after the traveller profiles were updated to care about them:
  seat_type     - "window", "aisle" or "other" (plain text, equal chance)
  scenic_route  - True or False (about a 30% chance of True)

Every one of the 75 company-destination pairs gets at least one offer
(the spec's own stated minimum). On top of that, each pair also has a
25% chance of getting a second offer on the same route - the same
company and destination, just a different departure time, giving
travellers more than one real choice on some routes without needing any
extra logic: generating a second offer just lands on a different random
time in that company's usual departure window.

Run: python3 scripts/generate_dataset.py
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 4420  # course code, chosen for a reproducible, documented seed
random.seed(SEED)

# SEAT_TYPES is a list of strings - the three seat choices an offer can
# have. A list (not a tuple) is fine here since nothing in this script
# ever changes it, but a list reads just as clearly for a simple lookup.
SEAT_TYPES = ["window", "aisle", "other"]

# SCENIC_ROUTE_PROBABILITY is a float between 0.0 and 1.0 - the chance
# that any one offer is marked as a scenic route. 0.30 means "about 3
# offers out of every 10", chosen as a plausible-but-not-dominant share.
SCENIC_ROUTE_PROBABILITY = 0.30

# SECOND_OFFER_PROBABILITY is a float between 0.0 and 1.0 - the chance
# that a given (destination, company) pair gets a second offer on top of
# its guaranteed first one, representing a second departure time on the
# same route. 0.25 means roughly 1 in 4 routes get this extra variety.
SECOND_OFFER_PROBABILITY = 0.25

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# TRAVEL_DATE_START used to be a fixed calendar date (2026-07-10). That
# was a bug: a real booking system can never have travel dates frozen
# in one month forever, because the real calendar keeps moving forward
# and eventually that month is in the past - which is exactly what
# happened here (main.py's own valid_dates check, built later, caught
# every single offer as "in the past" once enough real time had passed).
# Computing it as "today + 7 days", read fresh every time this script
# runs, means every regenerated dataset is always safely bookable from
# whatever day it is actually generated on - this is the one place in
# the whole generator where the output is deliberately NOT byte-
# identical across different days (everything else - price, rating,
# seats, etc. - still is, because SEED fixes every other random draw).
TRAVEL_DATE_START = datetime.today() + timedelta(days=7)
TRAVEL_DATE_RANGE_DAYS = 10  # offers scattered across 10 days

# Destinations: (name, approximate one-way distance from Madrid in km).
# Distances are illustrative, not sourced from a real routing API - this
# is a fictional dataset, the distances only need to be plausible enough
# to drive believable price/duration numbers.
# No destination_id here yet on purpose - see DESTINATIONS below, which
# assigns "D01", "D02", etc AFTER sorting this list alphabetically, so
# the IDs always line up with alphabetical order too (D01 is always
# whichever city comes first A-to-Z), instead of depending on whatever
# order someone happened to type the cities in here.
DESTINATIONS_RAW = [
    ("Barcelona", 620),
    ("Valencia", 360),
    ("Seville", 530),
    ("Malaga", 530),
    ("Granada", 420),
    ("Cordoba", 400),
    ("Bilbao", 400),
    ("San Sebastian", 450),
    ("Zaragoza", 320),
    ("Alicante", 420),
    ("Murcia", 400),
    ("Salamanca", 210),
    ("Toledo", 70),
    ("Santiago de Compostela", 600),
    ("Cadiz", 640),
]

# sorted(DESTINATIONS_RAW) sorts the tuples above by their first item
# (the name) alphabetically, since that is the first thing Python
# compares when sorting a list of tuples. enumerate(..., start=1) then
# numbers that alphabetical list 1, 2, 3, ..., and f"D{number:02d}"
# turns each number into the same zero-padded ID text this whole
# program already expects elsewhere, e.g. 1 -> "D01", 15 -> "D15".
DESTINATIONS = [
    (f"D{number:02d}", name, distance_km)
    for number, (name, distance_km) in enumerate(sorted(DESTINATIONS_RAW), start=1)
]

# Companies: each row encodes a "personality" as parameters that drive the
# offer generator below, instead of hand-authoring every offer. Suggested
# profiles come from the spec; the exact numbers behind each profile are
# our own design decision (documented here and in the report).
#
# price_mult        multiplies the distance-based base price
# dur_mult          multiplies the distance-based base duration
# co2_mult          multiplies the distance-based base CO2 estimate
# transfer_weights  probabilities for 0 / 1 / 2 transfers
# changeable_prob, refundable_prob
# rating_mean, rating_std
# baggage_mean, baggage_std (kg)
# window            (earliest, latest) departure time the company offers
COMPANIES = [
    dict(
        id="C1", name="SolRuta", profile="Low-cost daytime services",
        price_mult=0.75, dur_mult=1.15, co2_mult=1.00,
        transfer_weights=(0.35, 0.45, 0.20),
        changeable_prob=0.15, refundable_prob=0.10,
        rating_mean=3.5, rating_std=0.4,
        baggage_mean=15, baggage_std=3,
        window=("06:30", "17:00"),
    ),
    dict(
        id="C2", name="Camino Express", profile="Fast direct connections between major cities",
        price_mult=1.15, dur_mult=0.85, co2_mult=1.05,
        transfer_weights=(0.80, 0.18, 0.02),
        changeable_prob=0.85, refundable_prob=0.80,
        rating_mean=4.3, rating_std=0.3,
        baggage_mean=25, baggage_std=3,
        window=("06:00", "20:00"),
    ),
    dict(
        id="C3", name="CostaLink", profile="Strong coverage of coastal destinations",
        price_mult=1.00, dur_mult=1.00, co2_mult=1.00,
        transfer_weights=(0.55, 0.35, 0.10),
        changeable_prob=0.40, refundable_prob=0.35,
        rating_mean=3.8, rating_std=0.35,
        baggage_mean=20, baggage_std=4,
        window=("07:00", "19:00"),
    ),
    dict(
        id="C4", name="VerdeBus", profile="Environment-focused services and modern vehicles",
        price_mult=1.05, dur_mult=1.05, co2_mult=0.60,
        transfer_weights=(0.60, 0.33, 0.07),
        changeable_prob=0.70, refundable_prob=0.50,
        rating_mean=4.0, rating_std=0.3,
        baggage_mean=22, baggage_std=3,
        window=("07:00", "18:00"),
    ),
    dict(
        id="C5", name="NocheVia", profile="Overnight and late-evening services",
        price_mult=0.85, dur_mult=1.05, co2_mult=1.00,
        transfer_weights=(0.50, 0.40, 0.10),
        changeable_prob=0.20, refundable_prob=0.15,
        rating_mean=3.6, rating_std=0.4,
        baggage_mean=18, baggage_std=3,
        window=("18:00", "21:30"),
    ),
]

BASE_PRICE_PER_KM = 0.065       # EUR per km before company multiplier
BASE_SPEED_KMH = 70             # assumed average bus speed incl. stops
TRANSFER_PENALTY_MIN = 25       # extra minutes per transfer
BASE_CO2_PER_KM = 0.06          # kg CO2 per km before company multiplier


def hhmm_to_minutes(hhmm):
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def minutes_to_hhmm(total_minutes):
    total_minutes = int(total_minutes) % (24 * 60)
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def weighted_choice(values, weights):
    return random.choices(values, weights=weights, k=1)[0]


def generate_offer(offer_num, destination, company):
    dest_id, dest_name, distance_km = destination

    transfers = weighted_choice([0, 1, 2], company["transfer_weights"])

    base_duration = (distance_km / BASE_SPEED_KMH) * 60
    duration = base_duration * company["dur_mult"] + transfers * TRANSFER_PENALTY_MIN
    duration *= random.uniform(0.95, 1.08)
    duration_minutes = max(45, round(duration))

    base_price = distance_km * BASE_PRICE_PER_KM
    price = base_price * company["price_mult"] * random.uniform(0.92, 1.10)
    price_eur = round(price, 2)

    co2 = distance_km * BASE_CO2_PER_KM * company["co2_mult"] * random.uniform(0.95, 1.05)
    co2_estimate_kg = round(co2, 1)

    window_start = hhmm_to_minutes(company["window"][0])
    window_end = hhmm_to_minutes(company["window"][1])
    departure_minutes = random.randint(window_start, window_end)
    departure_time = minutes_to_hhmm(departure_minutes)
    arrival_total_minutes = departure_minutes + duration_minutes
    arrival_time = minutes_to_hhmm(arrival_total_minutes)
    # A genuine overnight trip (e.g. a long NocheVia route) can legitimately
    # arrive on the next calendar day. Rather than pretending every trip
    # fits before midnight, we record that explicitly, so loaders.py can
    # tell a real overnight arrival apart from a data-entry mistake.
    arrival_day_offset = arrival_total_minutes // (24 * 60)

    travel_date = TRAVEL_DATE_START + timedelta(days=random.randint(0, TRAVEL_DATE_RANGE_DAYS - 1))

    rating = random.gauss(company["rating_mean"], company["rating_std"])
    customer_rating = round(min(5.0, max(1.0, rating)), 1)

    baggage = random.gauss(company["baggage_mean"], company["baggage_std"])
    luggage_allowance_kg = int(round(min(30, max(5, baggage))))

    changeable = random.random() < company["changeable_prob"]
    refundable = random.random() < company["refundable_prob"]

    # ~5% of offers are intentionally sold out, to give filters.py and the
    # tests a real "no seats available" boundary case instead of a
    # hand-crafted one only.
    seats_available = 0 if random.random() < 0.05 else random.randint(1, 40)

    # random.choice picks one item from the list with equal chance for
    # each - a simple way to assign a seat type with no extra logic.
    seat_type = random.choice(SEAT_TYPES)

    # random.random() gives a float between 0.0 and 1.0. Comparing it to
    # SCENIC_ROUTE_PROBABILITY is the same trick used for seats_available
    # above: on average, this is True that fraction of the time.
    scenic_route = random.random() < SCENIC_ROUTE_PROBABILITY

    return {
        "offer_id": f"OFR-2026-{offer_num:04d}",
        "company_id": company["id"],
        "destination_id": dest_id,
        "origin": "Madrid",
        "travel_date": travel_date.strftime("%Y-%m-%d"),
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "arrival_day_offset": arrival_day_offset,
        "duration_minutes": duration_minutes,
        "price_eur": price_eur,
        "transfers": transfers,
        "luggage_allowance_kg": luggage_allowance_kg,
        "changeable": changeable,
        "refundable": refundable,
        "seats_available": seats_available,
        "customer_rating": customer_rating,
        "co2_estimate_kg": co2_estimate_kg,
        "seat_type": seat_type,
        "scenic_route": scenic_route,
    }


def build_offers():
    """
    Builds at least one offer for every (destination, company) pair - 15
    destinations x 5 companies = 75 pairs, the spec's own stated minimum
    ("Minimum dataset: 75 company-destination combinations"). On top of
    that guaranteed first offer, each pair also has a
    SECOND_OFFER_PROBABILITY chance of getting a second offer too - the
    same route, just a different departure time - so the final total is
    75 or a bit more, not capped at exactly 75.
    """
    offers = []
    offer_num = 1
    for destination in DESTINATIONS:
        for company in COMPANIES:
            # This first call is mandatory - it is what guarantees all
            # 75 pairs are covered, no matter what the random numbers do.
            offers.append(generate_offer(offer_num, destination, company))
            offer_num += 1

            # This second call only happens sometimes. Calling
            # generate_offer again for the exact same (destination,
            # company) pair naturally produces a different departure
            # time, price and so on, since those are drawn fresh from
            # random numbers each time it runs - no extra code is needed
            # to force the two offers to look different.
            if random.random() < SECOND_OFFER_PROBABILITY:
                offers.append(generate_offer(offer_num, destination, company))
                offer_num += 1

    return offers


def write_destinations():
    path = DATA_DIR / "destinations.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["destination_id", "name", "approx_distance_km"])
        for dest_id, name, distance_km in DESTINATIONS:
            writer.writerow([dest_id, name, distance_km])
    return path


def write_companies():
    path = DATA_DIR / "companies.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["company_id", "name", "profile_description"])
        for c in COMPANIES:
            writer.writerow([c["id"], c["name"], c["profile"]])
    return path


def write_offers(offers):
    path = DATA_DIR / "offers.csv"
    fieldnames = list(offers[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(offers)
    return path


def write_invalid_offers():
    """
    A small, hand-picked file of deliberately broken rows, same column
    layout as offers.csv, one clear problem per row, for loaders.py to
    reject and log rather than crash on.
    """
    path = DATA_DIR / "offers_invalid.csv"
    fieldnames = [
        "offer_id", "company_id", "destination_id", "origin", "travel_date",
        "departure_time", "arrival_time", "arrival_day_offset", "duration_minutes",
        "price_eur", "transfers", "luggage_allowance_kg", "changeable", "refundable",
        "seats_available", "customer_rating", "co2_estimate_kg", "seat_type",
        "scenic_route",
    ]
    # Every bad row below also gets a plain, valid-looking seat_type and
    # scenic_route, since those two fields are not the thing being
    # tested as broken in this file - only one field per row is wrong,
    # on purpose, so it is always obvious which rule caught it.
    bad_rows = [
        # negative price
        dict(offer_id="OFR-2026-9001", company_id="C1", destination_id="D01",
             origin="Madrid", travel_date="2026-07-12", departure_time="08:00",
             arrival_time="12:00", arrival_day_offset=0, duration_minutes=240,
             price_eur=-15.0, transfers=0, luggage_allowance_kg=20, changeable=True,
             refundable=True, seats_available=10, customer_rating=4.0,
             co2_estimate_kg=30.0, seat_type="window", scenic_route=False),
        # rating outside the 1.0-5.0 scale
        dict(offer_id="OFR-2026-9002", company_id="C2", destination_id="D02",
             origin="Madrid", travel_date="2026-07-13", departure_time="09:00",
             arrival_time="12:30", arrival_day_offset=0, duration_minutes=210,
             price_eur=28.0, transfers=0, luggage_allowance_kg=25, changeable=True,
             refundable=True, seats_available=5, customer_rating=6.5,
             co2_estimate_kg=15.0, seat_type="aisle", scenic_route=False),
        # unknown destination_id (not in destinations.csv)
        dict(offer_id="OFR-2026-9003", company_id="C3", destination_id="D99",
             origin="Madrid", travel_date="2026-07-14", departure_time="10:00",
             arrival_time="15:00", arrival_day_offset=0, duration_minutes=300,
             price_eur=34.0, transfers=1, luggage_allowance_kg=20, changeable=False,
             refundable=False, seats_available=8, customer_rating=3.5,
             co2_estimate_kg=25.0, seat_type="window", scenic_route=True),
        # incorrect_ID: offer_id doesn't match the OFR-YYYY-NNNN pattern
        dict(offer_id="OFFER_ABC", company_id="C4", destination_id="D05",
             origin="Madrid", travel_date="2026-07-15", departure_time="11:00",
             arrival_time="14:00", arrival_day_offset=0, duration_minutes=180,
             price_eur=30.0, transfers=0, luggage_allowance_kg=22, changeable=True,
             refundable=False, seats_available=12, customer_rating=4.1,
             co2_estimate_kg=18.0, seat_type="other", scenic_route=False),
        # arrival before departure on the SAME declared day (arrival_day_offset=0)
        # with a duration that doesn't justify it either - a clear data-entry
        # error, not a real overnight trip (those use arrival_day_offset=1)
        dict(offer_id="OFR-2026-9005", company_id="C5", destination_id="D07",
             origin="Madrid", travel_date="2026-07-16", departure_time="10:00",
             arrival_time="09:30", arrival_day_offset=0, duration_minutes=240,
             price_eur=27.0, transfers=1, luggage_allowance_kg=18, changeable=False,
             refundable=False, seats_available=6, customer_rating=3.6,
             co2_estimate_kg=20.0, seat_type="window", scenic_route=False),
        # negative seats available
        dict(offer_id="OFR-2026-9006", company_id="C1", destination_id="D13",
             origin="Madrid", travel_date="2026-07-17", departure_time="12:00",
             arrival_time="13:00", arrival_day_offset=0, duration_minutes=60,
             price_eur=8.0, transfers=0, luggage_allowance_kg=15, changeable=False,
             refundable=False, seats_available=-2, customer_rating=3.4,
             co2_estimate_kg=4.0, seat_type="aisle", scenic_route=False),
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(bad_rows)
    return path


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = write_destinations()
    comp_path = write_companies()
    offers = build_offers()
    offers_path = write_offers(offers)
    invalid_path = write_invalid_offers()

    print(f"seed = {SEED}")
    print(f"wrote {dest_path} ({len(DESTINATIONS)} destinations)")
    print(f"wrote {comp_path} ({len(COMPANIES)} companies)")
    print(f"wrote {offers_path} ({len(offers)} valid offers)")
    print(f"wrote {invalid_path} (6 deliberately invalid rows)")
    zero_seat = sum(1 for o in offers if o["seats_available"] == 0)
    print(f"  of which {zero_seat} valid offers have 0 seats available (boundary case)")


if __name__ == "__main__":
    main()
