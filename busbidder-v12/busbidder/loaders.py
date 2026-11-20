# MEMO: This file is loaders.py.
# Its only job is to read destinations.csv, companies.csv and offers.csv
# (or offers_invalid.csv) from disk, check every value in every row, and
# turn the good rows into Destination/Company/Offer objects (from
# models.py). A row with a real problem (bad price, unknown destination,
# wrong pattern, etc.) is REJECTED - it is logged and skipped, not
# crashed on and not silently kept. This matches the spec's own wording:
# invalid records are rejected, not corrected, and the reason is written
# to the log file so it can be checked afterwards.
#
# This file contains no real personal data - it only reads the
# fictional, generated CSV files for this course project.

import csv
import logging
import re
from pathlib import Path

from busbidder.exceptions import InvalidIdentifierError, InvalidRecordError
from busbidder.models import Company, Destination, Offer

# logger is the single object every function in this file uses to write
# log messages. logging.getLogger(__name__) is the standard way to get a
# logger tied to this specific file's name ("busbidder.loaders"), which
# shows up in the log file so it is obvious which file logged what.
logger = logging.getLogger(__name__)


def setup_logging(log_path="logs/app.log"):
    """
    Turns on writing log messages to the given file. Called once, from
    main.py, before any loading happens - not automatically on import,
    so importing this file never has a surprising side effect.
    """
    # Path(...).parent gives the folder part of the path (e.g. "logs").
    # mkdir(parents=True, exist_ok=True) creates that folder if it does
    # not already exist, and does nothing (no error) if it does.
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    # basicConfig sets up where log messages go (the file) and what the
    # lowest level worth recording is (INFO and above).
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


# re.compile(...) turns a pattern string into a reusable pattern object,
# built once here instead of being rebuilt every time a row is checked.
# OFFER_ID_PATTERN matches exactly "OFR-" then 4 digits, "-", then 4
# digits, e.g. "OFR-2026-0001" - anything else fails the match.
OFFER_ID_PATTERN = re.compile(r"^OFR-\d{4}-\d{4}$")

# RATING_MIN / RATING_MAX are floats because customer_rating itself is a
# float (a decimal star rating like 4.1), so the limits need to be the
# same type to compare against it correctly.
RATING_MIN = 1.0
RATING_MAX = 5.0

# A plain Python set of the only 3 text values seat_type is allowed to
# be. A set (not a list) is used because checking "is this value in the
# set" is exactly what a set is for, and the order of the 3 values does
# not matter here.
VALID_SEAT_TYPES = {"window", "aisle", "other"}


def _convert_float(value_text, field_name):
    """
    Turns a text value (as read from a CSV cell) into a float, or raises
    InvalidRecordError if that text is not actually a number at all
    (e.g. an empty cell or a typo like "4O.5").
    """
    try:
        # float(...) does the actual conversion from text to a number.
        return float(value_text)
    except ValueError:
        # This except only runs if float() itself failed - value_text
        # was not a valid number in the first place.
        raise InvalidRecordError(field_name, f"'{value_text}' is not a valid number")


def _convert_int(value_text, field_name):
    """Same idea as _convert_float, but for whole-number fields."""
    try:
        return int(value_text)
    except ValueError:
        raise InvalidRecordError(field_name, f"'{value_text}' is not a valid whole number")


def _convert_bool(value_text, field_name):
    """
    Converts the text "True" or "False" (exactly how Python's csv writer
    stores a bool) into a real bool. Any other text is rejected, instead
    of guessing what it might have meant.
    """
    if value_text == "True":
        return True
    if value_text == "False":
        return False
    raise InvalidRecordError(field_name, f"'{value_text}' is not 'True' or 'False'")


def load_destinations(path):
    """
    Reads destinations.csv and returns a dict mapping destination_id to
    a Destination object, e.g. {"D01": Destination(...), ...}. A dict is
    used (not a list) because other code needs to look up a destination
    by its id quickly, over and over, while checking offers.
    """
    destinations = {}
    # newline="" is the standard way to open a CSV file in Python, so the
    # csv module handles line endings correctly on every operating system.
    with open(path, newline="", encoding="utf-8") as f:
        # csv.DictReader reads each row as a dict using the header row
        # as the keys, e.g. {"destination_id": "D01", "name": "Barcelona", ...}
        reader = csv.DictReader(f)
        for row in reader:
            destination = Destination(
                destination_id=row["destination_id"],
                name=row["name"],
                # destinations.csv stores this as a whole number of km,
                # so it is converted to int here.
                approx_distance_km=int(row["approx_distance_km"]),
            )
            destinations[destination.get_destination_id()] = destination
    logger.info(f"loaded {len(destinations)} destinations from {path}")
    return destinations


def load_companies(path):
    """Same idea as load_destinations, but for companies.csv."""
    companies = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = Company(
                company_id=row["company_id"],
                name=row["name"],
                profile_description=row["profile_description"],
            )
            companies[company.get_company_id()] = company
    logger.info(f"loaded {len(companies)} companies from {path}")
    return companies


def parse_offer_row(row, known_destination_ids, known_company_ids):
    """
    Turns one offers.csv row (a dict of text values) into one Offer
    object. Raises InvalidIdentifierError or InvalidRecordError if
    anything about the row is wrong - the caller (load_offers_file,
    below) is the part that decides what to do about that error.
    """
    offer_id = row["offer_id"]
    # .fullmatch(...) checks the WHOLE string against the pattern, not
    # just part of it - this is the "genuinely suitable" use of a
    # regular expression the spec asks for, checking a structured id.
    if not OFFER_ID_PATTERN.fullmatch(offer_id):
        raise InvalidIdentifierError("offer_id", offer_id, OFFER_ID_PATTERN.pattern)

    destination_id = row["destination_id"]
    if destination_id not in known_destination_ids:
        raise InvalidRecordError(
            "destination_id", f"'{destination_id}' is not a known destination"
        )

    company_id = row["company_id"]
    if company_id not in known_company_ids:
        raise InvalidRecordError("company_id", f"'{company_id}' is not a known company")

    price_eur = _convert_float(row["price_eur"], "price_eur")
    if price_eur < 0:
        raise InvalidRecordError("price_eur", f"{price_eur} is negative")

    customer_rating = _convert_float(row["customer_rating"], "customer_rating")
    if customer_rating < RATING_MIN or customer_rating > RATING_MAX:
        raise InvalidRecordError(
            "customer_rating",
            f"{customer_rating} is outside the allowed {RATING_MIN}-{RATING_MAX} range",
        )

    seats_available = _convert_int(row["seats_available"], "seats_available")
    if seats_available < 0:
        raise InvalidRecordError("seats_available", f"{seats_available} is negative")

    duration_minutes = _convert_int(row["duration_minutes"], "duration_minutes")
    transfers = _convert_int(row["transfers"], "transfers")
    luggage_allowance_kg = _convert_int(row["luggage_allowance_kg"], "luggage_allowance_kg")
    co2_estimate_kg = _convert_float(row["co2_estimate_kg"], "co2_estimate_kg")

    changeable = _convert_bool(row["changeable"], "changeable")
    refundable = _convert_bool(row["refundable"], "refundable")
    scenic_route = _convert_bool(row["scenic_route"], "scenic_route")

    seat_type = row["seat_type"]
    if seat_type not in VALID_SEAT_TYPES:
        raise InvalidRecordError("seat_type", f"'{seat_type}' is not one of {VALID_SEAT_TYPES}")

    arrival_day_offset = _convert_int(row["arrival_day_offset"], "arrival_day_offset")
    if arrival_day_offset not in (0, 1):
        raise InvalidRecordError(
            "arrival_day_offset", f"{arrival_day_offset} must be 0 or 1"
        )

    departure_time = row["departure_time"]
    arrival_time = row["arrival_time"]
    # Only check arrival-vs-departure for a same-day trip. HH:MM strings
    # compare correctly as plain text here because every hour and minute
    # in this dataset is zero-padded (e.g. "08:00", never "8:0").
    if arrival_day_offset == 0 and arrival_time <= departure_time:
        raise InvalidRecordError(
            "arrival_time",
            f"'{arrival_time}' is not after departure_time '{departure_time}' "
            f"on the same day (arrival_day_offset=0)",
        )

    return Offer(
        offer_id=offer_id,
        company_id=company_id,
        destination_id=destination_id,
        origin=row["origin"],
        travel_date=row["travel_date"],
        departure_time=departure_time,
        arrival_time=arrival_time,
        arrival_day_offset=arrival_day_offset,
        duration_minutes=duration_minutes,
        price_eur=price_eur,
        transfers=transfers,
        luggage_allowance_kg=luggage_allowance_kg,
        changeable=changeable,
        refundable=refundable,
        seats_available=seats_available,
        customer_rating=customer_rating,
        co2_estimate_kg=co2_estimate_kg,
        seat_type=seat_type,
        scenic_route=scenic_route,
    )


def load_offers_file(path, known_destination_ids, known_company_ids):
    """
    Reads one offers CSV file (could be the valid file or the
    deliberately-invalid demo file) and returns a list of only the
    Offer objects that passed every check. Every rejected row is logged
    with the file name, row number, field name and reason - never just
    silently dropped.
    """
    valid_offers = []
    rejected_count = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # enumerate(reader, start=2) counts rows starting at 2, because
        # row 1 is the header line, so the first data row really is
        # "row 2" if you opened the file in a spreadsheet.
        for row_number, row in enumerate(reader, start=2):
            try:
                offer = parse_offer_row(row, known_destination_ids, known_company_ids)
            except (InvalidIdentifierError, InvalidRecordError) as error:
                # This row is rejected: log exactly what happened, then
                # move on to the next row with continue - the whole
                # program does not stop just because one row is bad.
                logger.warning(
                    f"rejected row {row_number} in {path}: {error}"
                )
                rejected_count += 1
                continue
            valid_offers.append(offer)

    logger.info(
        f"loaded {len(valid_offers)} valid offers and rejected {rejected_count} "
        f"rows from {path}"
    )
    return valid_offers
