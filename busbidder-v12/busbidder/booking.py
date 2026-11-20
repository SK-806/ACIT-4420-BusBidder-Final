# MEMO: This file is booking.py.
# Its only job is Layer 4 of the validation framework (see
# report's section 3.2): checking and recording an actual seat booking,
# AFTER a traveller has already picked one offer from a ranked list.
# Everything before this file (loaders -> filters -> scoring -> explain)
# only ever LOOKS at offers; this file is the only place in the whole
# program that commits to taking seats out of an offer's pool and writes
# a permanent record of that booking to disk.
#
# Two rules live here because they can only be checked once a traveller
# has chosen how many seats they want, which is not known any earlier in
# the pipeline:
#   - seats_selected must be at least 1 (booking 0 or negative seats
#     makes no sense)
#   - seats_selected must be at most 6 (the course spec's own cap on how
#     many seats one single booking is allowed to take, to stop one
#     booking from silently draining an entire offer's seats)
# Both are checked by raising an error rather than quietly rounding the
# number up or down, so a bad request is rejected outright instead of
# being "fixed" into something the traveller did not actually ask for.
#
# This file contains no real personal data - "bookings" here only ever
# refer to the fictional offers generated for this course project.

import csv
import logging
import re
from datetime import date
from pathlib import Path

from busbidder.exceptions import InvalidRecordError

logger = logging.getLogger(__name__)

# seats_selected is an int (not a float) because seats are always a
# whole-number count - there is no such thing as half a seat.
MIN_SEATS_PER_BOOKING = 1
MAX_SEATS_PER_BOOKING = 6

# A booking reference follows the same style as OFFER_ID_PATTERN in
# loaders.py (a short prefix, a 4-digit year, a dash, then digits), so
# anyone reading both files recognises the same pattern at a glance.
# "BKG" stands for "booking"; the final group is 6 digits (wider than
# the offer ID's 4) because many separate bookings can be made against
# the same small pool of offers over time.
BOOKING_REFERENCE_PATTERN = re.compile(r"^BKG-\d{4}-\d{6}$")

# The exact column order used when a booking is written to, or read
# back from, the bookings CSV file. Kept as one shared list so writing
# and reading can never silently drift out of sync with each other.
BOOKING_CSV_FIELDS = [
    "booking_reference",
    "offer_id",
    "destination_id",
    "seats_selected",
    "total_price_eur",
    "booked_on_date",
]


def validate_seats_selected(seats_selected):
    """
    Checks the Layer 4 rule on its own, so it can be tested or reused
    without needing a real Offer object. Raises InvalidRecordError if
    seats_selected is not a whole number, or is outside the allowed
    range [MIN_SEATS_PER_BOOKING, MAX_SEATS_PER_BOOKING]. Returns
    nothing - if this function does not raise, the value is valid.
    """
    # isinstance(..., bool) is excluded on purpose: in Python, True/False
    # are technically a kind of int, and a seat count of True/False would
    # be a mistake further up the program, not a real booking request.
    if not isinstance(seats_selected, int) or isinstance(seats_selected, bool):
        raise InvalidRecordError("seats_selected", "must be a whole number")

    if seats_selected < MIN_SEATS_PER_BOOKING:
        raise InvalidRecordError(
            "seats_selected",
            f"must be at least {MIN_SEATS_PER_BOOKING} - cannot book {seats_selected} seats",
        )

    if seats_selected > MAX_SEATS_PER_BOOKING:
        raise InvalidRecordError(
            "seats_selected",
            f"must be at most {MAX_SEATS_PER_BOOKING} per booking - {seats_selected} seats "
            f"is too many for one booking",
        )


def load_existing_bookings(path):
    """
    Reads the bookings CSV file at `path` and returns a list of plain
    dicts, one per booking already made. If the file does not exist
    yet (no bookings have ever been made), returns an empty list rather
    than raising an error - a fresh project with no bookings yet is a
    completely normal, expected state.
    """
    bookings_path = Path(path)
    if not bookings_path.exists():
        return []

    bookings = []
    # newline="" on open is required by Python's own csv module docs,
    # to stop it from adding extra blank lines on some operating
    # systems.
    with open(bookings_path, "r", newline="", encoding="utf-8") as bookings_file:
        reader = csv.DictReader(bookings_file)
        for row in reader:
            # seats_selected and total_price_eur come back from
            # csv.DictReader as plain text, so they are converted back
            # to int / float here - everything else stays as text.
            row["seats_selected"] = int(row["seats_selected"])
            row["total_price_eur"] = float(row["total_price_eur"])
            bookings.append(row)
    return bookings


def seats_already_booked_for_offer(bookings, offer_id):
    """
    Adds up seats_selected across every existing booking that was made
    against this one offer_id. bookings is the list returned by
    load_existing_bookings(). Returns an int - 0 if no booking has ever
    been made against this offer_id.
    """
    total = 0
    for booking in bookings:
        if booking["offer_id"] == offer_id:
            total += booking["seats_selected"]
    return total


def seats_still_available(offer, bookings):
    """
    Works out how many seats are actually still free on one offer right
    now: the seat count the offer started with, minus every seat
    already taken by an earlier booking recorded in `bookings`. This is
    the "capacity reduction" step - offer.get_seats_available() alone
    only tells you the ORIGINAL pool size from the dataset, not what is
    left after real bookings.
    """
    already_booked = seats_already_booked_for_offer(bookings, offer.get_offer_id())
    return offer.get_seats_available() - already_booked


def make_booking_reference(booking_number):
    """
    Builds one booking reference string, e.g. "BKG-2026-000001".
    booking_number is a plain int (1, 2, 3, ...) chosen by whatever code
    calls this function - normally "how many bookings already exist,
    plus 1". The year used is today's real calendar year, read fresh
    each time rather than hard-coded, so this keeps working correctly in
    any year the program is actually run in.
    """
    this_year = date.today().year
    # :06d formats booking_number as 6 digits with leading zeros, e.g.
    # 1 -> "000001", matching BOOKING_REFERENCE_PATTERN above exactly.
    return f"BKG-{this_year}-{booking_number:06d}"


def create_booking(offer, seats_selected, bookings, booking_number):
    """
    Checks every Layer 4 rule for one booking attempt, and if all of
    them pass, returns a new booking dict (NOT yet saved to disk - see
    save_booking() for that). Raises InvalidRecordError if any rule
    fails, in which case no booking dict is returned at all.

    offer is the Offer object being booked. seats_selected is the
    traveller's requested seat count. bookings is the list from
    load_existing_bookings(), used to check real remaining capacity.
    booking_number is passed straight to make_booking_reference().
    """
    # Rule 1: seats_selected itself must be a sane whole number in the
    # allowed [1, 6] range, checked first since it is the cheapest check
    # and the one most likely to be a simple typo.
    validate_seats_selected(seats_selected)

    # Rule 2: there must actually be enough real seats left on this
    # specific offer, after accounting for every earlier booking.
    remaining = seats_still_available(offer, bookings)
    if seats_selected > remaining:
        raise InvalidRecordError(
            "seats_selected",
            f"only {remaining} seat(s) remain on offer {offer.get_offer_id()}, "
            f"cannot book {seats_selected}",
        )

    total_price_eur = offer.get_price_eur() * seats_selected

    booking = {
        "booking_reference": make_booking_reference(booking_number),
        "offer_id": offer.get_offer_id(),
        "destination_id": offer.get_destination_id(),
        "seats_selected": seats_selected,
        "total_price_eur": total_price_eur,
        # str(date.today()) gives "YYYY-MM-DD" text, the same date
        # format already used everywhere else in this project (e.g.
        # Offer.travel_date), so every date field in the whole program
        # reads the same way.
        "booked_on_date": str(date.today()),
    }
    return booking


def save_booking(booking, path):
    """
    Appends one booking dict as a new row to the bookings CSV file at
    `path`, creating the file (with a header row) first if it does not
    exist yet. This is the "confirmation persistence" step: once this
    function returns, the booking is permanently on disk and will be
    counted by seats_still_available() on every future run, not just
    this one.
    """
    bookings_path = Path(path)
    file_already_exists = bookings_path.exists()

    # Make sure the folder the file lives in actually exists (e.g.
    # "data/"), the same pattern used by setup_logging() in loaders.py.
    bookings_path.parent.mkdir(parents=True, exist_ok=True)

    # "a" = append mode: adds this one row to the end of the file
    # without erasing any booking that was already saved there before.
    with open(bookings_path, "a", newline="", encoding="utf-8") as bookings_file:
        writer = csv.DictWriter(bookings_file, fieldnames=BOOKING_CSV_FIELDS)
        if not file_already_exists:
            writer.writeheader()
        writer.writerow(booking)

    logger.info(
        "Booking %s saved: %s seat(s) on offer %s",
        booking["booking_reference"],
        booking["seats_selected"],
        booking["offer_id"],
    )
