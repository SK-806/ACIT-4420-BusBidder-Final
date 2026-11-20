# MEMO: This file is main.py.
# Its only job is to be the one place a traveller actually runs. It now
# supports 2 separate commands:
#   search - "load the data, check the search is valid, then for each
#             of the 5 fixed profiles, filter -> score -> explain, and
#             print + save the result." (everything this file did
#             before booking.py was added in)
#   book   - "take one real offer_id from a search's results and a seat
#             count, check Layer 4's rules, and save a real booking."
# Every other file in busbidder/ only defines functions - nothing runs
# on its own until this file calls them in the right order.
#
# This is also where Layer 3 of the validation framework (section 3.1 report)
# lives: valid_dates, the rule that says a
# traveller's search dates must not be in the past. It belongs here
# and nowhere else, because it is the only rule that depends on the
# real-world date the program happens to be run on, not on anything
# stored in a CSV file.
#
# This file contains no real personal data - every destination, date
# and price it prints comes from the fictional dataset generated for
# this project.

import argparse
import sys
from datetime import date, timedelta

from busbidder.booking import create_booking, load_existing_bookings, save_booking
from busbidder.exceptions import InvalidRecordError
from busbidder.explain import explain_top_offer
from busbidder.filters import filter_offers
from busbidder.loaders import load_companies, load_destinations, load_offers_file, setup_logging
from busbidder.profiles import PROFILES, all_profile_keys
from busbidder.render import render_results_to_html
from busbidder.scoring import rank_offers

# These 4 paths are strings pointing at the fixed input/output files
# this program always reads from or writes to. Kept as named constants
# here, in one place, rather than typed out again every time a file is
# opened.
DESTINATIONS_CSV_PATH = "data/destinations.csv"
COMPANIES_CSV_PATH = "data/companies.csv"
OFFERS_CSV_PATH = "data/offers.csv"
BOOKINGS_CSV_PATH = "data/bookings.csv"

# MAX_OFFERS_TO_PRINT is an int - how many ranked offers to show per
# profile in the console output, so a destination with many offers does
# not flood the screen. The top offer always gets the full explanation
# underneath it regardless of this limit.
MAX_OFFERS_TO_PRINT = 5

# MAX_DAYS_AHEAD_ALLOWED is an int - the furthest into the future a
# search date is allowed to be, counted from today's REAL calendar date
# (not a fixed date), so this ceiling always slides forward with
# whatever day the program is actually run on. 90 was chosen as a
# generous but bounded planning window (about 3 months) - comfortably
# past the dataset's own travel_date range (today + roughly 7 to 17
# days, see scripts/generate_dataset.py), while still refusing clearly
# unreasonable requests such as a date 10 years from now.
MAX_DAYS_AHEAD_ALLOWED = 90


def validate_date_not_in_past(field_name, date_string):
    """
    Layer 3 rule: valid_dates. date_string must be a REAL, well-formed
    "YYYY-MM-DD" calendar date - not just text that happens to look
    like one - and must fall between today and MAX_DAYS_AHEAD_ALLOWED
    days from today, both read fresh from the computer's own clock
    every time this runs (not a fixed value), so this check behaves
    correctly no matter what day the program is actually run on.
    Raises InvalidRecordError if date_string cannot be parsed as a real
    date, or is in the past, or is too far in the future; returns
    nothing if the date is valid and within that window.
    """
    # date.fromisoformat() actually parses date_string as a calendar
    # date (checking the month is 1-12, the day exists in that month,
    # and so on) instead of just comparing it as text. A string that
    # looks date-shaped but is not a real date - e.g. "2027-0-20"
    # (month 0 does not exist) or "2026-02-30" (no 30th of February) -
    # fails this parse step and raises ValueError, which is caught
    # below and turned into our own InvalidRecordError. This closes
    # the gap plain string comparison had: text comparison only checks
    # characters, never whether the date itself could really happen.
    try:
        parsed_date = date.fromisoformat(date_string)
    except ValueError:
        raise InvalidRecordError(
            field_name,
            f"'{date_string}' is not a real calendar date in YYYY-MM-DD format",
        )

    # today and latest_allowed_date are both real date objects (not
    # text), read fresh from the computer's clock every call, so the
    # comparisons below use real calendar-date arithmetic rather than
    # string comparison.
    today = date.today()
    latest_allowed_date = today + timedelta(days=MAX_DAYS_AHEAD_ALLOWED)

    if parsed_date < today:
        raise InvalidRecordError(
            field_name,
            f"'{date_string}' is in the past - today is {today}",
        )

    if parsed_date > latest_allowed_date:
        raise InvalidRecordError(
            field_name,
            f"'{date_string}' is more than {MAX_DAYS_AHEAD_ALLOWED} days ahead "
            f"of today ({today}) - the latest allowed date is {latest_allowed_date}",
        )


def resolve_destination_id(typed_text, destinations):
    """
    Lets the traveller type EITHER a real destination_id (e.g. "D02")
    OR the destination's plain name (e.g. "Barcelona", any mix of
    upper/lower case) on the command line - whichever is easier to
    remember. destinations is the dict returned by load_destinations().
    Returns the matching destination_id string, or None if typed_text
    does not match any real ID or any real name.
    """
    # Trying it as an ID first: destination_id values are always written
    # the same exact way everywhere else in this project ("D" plus 2
    # digits), so this is a plain, case-sensitive dictionary lookup.
    if typed_text in destinations:
        return typed_text

    # Not a known ID - trying it as a name instead. .strip() removes any
    # accidental leading/trailing spaces, and .lower() makes the
    # comparison ignore capitalisation, so "Barcelona", "barcelona" and
    # "BARCELONA" are all treated as the same match.
    typed_name = typed_text.strip().lower()
    for destination in destinations.values():
        if destination.get_name().lower() == typed_name:
            return destination.get_destination_id()

    # typed_text did not match any real ID or any real name at all.
    return None


def parse_command_line_arguments():
    """
    Defines and reads the command-line input for both commands this
    program supports. add_subparsers(dest="command", required=True)
    means the traveller must type one of "search" or "book" as the
    very first word after main.py - the 2 commands take different
    input, so they are kept as 2 separate, clearly-named modes instead
    of trying to guess what a single flat list of flags was meant for.
    """
    parser = argparse.ArgumentParser(
        description="BusBidder Spain - rank and book bus offers for 5 fixed traveller profiles."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # "search" takes the same 3 inputs this program always has: a
    # destination and a travel-date window. Everything else (the 5
    # profiles, their weights and constraints) stays fixed in
    # profiles.py, never typed in on the command line.
    search_parser = subparsers.add_parser(
        "search", help="Rank offers for a destination/date search, across all 5 profiles"
    )
    search_parser.add_argument(
        "--destination", required=True,
        help="Destination ID (e.g. D02) OR destination name (e.g. Barcelona)",
    )
    search_parser.add_argument(
        "--date-from", required=True, help="Earliest travel date, format YYYY-MM-DD"
    )
    search_parser.add_argument(
        "--date-to", required=True, help="Latest travel date, format YYYY-MM-DD"
    )

    # "book" takes one real offer_id (as shown by a previous "search")
    # and how many seats to book on it.
    book_parser = subparsers.add_parser(
        "book", help="Book seats on one specific offer_id from an earlier search"
    )
    book_parser.add_argument(
        "--offer-id", required=True, help="The exact offer_id to book, e.g. OFR-2026-0010"
    )
    # type=int means argparse itself converts the typed text straight
    # to an int - typing a non-number here (e.g. "--seats two") is
    # rejected by argparse before this program's own code even runs.
    book_parser.add_argument(
        "--seats", required=True, type=int, help="Number of seats to book (1-6)"
    )

    return parser.parse_args()


def print_profile_results(profile_key, profile, surviving_offers, ranked_offers, scores, companies):
    """
    Prints one profile's ranked results to the console: a header, a
    short list of the top few offers (now including which company
    offers each one) with their scores, then a full plain-language
    explanation of the single best one. Prints nothing and returns
    early if no offers survived this profile's constraints at all,
    since there is nothing to rank or explain in that case.

    companies is the dict returned by load_companies() - used only to
    turn an offer's company_id (e.g. "C3") into a real company name
    (e.g. "CostaLink") for display, the same way destination_id is
    already turned into a destination name elsewhere in this file.
    """
    # "=" * 60 repeats the character 60 times, just as a plain visual
    # divider between one profile's results and the next.
    print("=" * 60)
    print(f"Profile: {profile['display_name']}")
    print("=" * 60)

    if not ranked_offers:
        print("No offers matched this profile's own constraints for this search.")
        print()
        return

    print(f"{len(ranked_offers)} offer(s) matched. Top {min(MAX_OFFERS_TO_PRINT, len(ranked_offers))} shown below:")
    # enumerate(..., start=1) numbers the printed list starting at 1,
    # which reads more naturally than starting at 0 for a human.
    for rank_number, offer in enumerate(ranked_offers[:MAX_OFFERS_TO_PRINT], start=1):
        score = scores[offer.get_offer_id()]
        # companies[offer.get_company_id()] looks up the one Company
        # object matching this offer, so its plain name can be shown
        # instead of only the "C3"-style code.
        company_name = companies[offer.get_company_id()].get_name()
        # :.1f formats the score to 1 decimal place, e.g. 72.3, instead
        # of a long raw float like 72.34999999999999.
        print(
            f"  {rank_number}. {offer.get_offer_id()}  "
            f"{company_name}  "
            f"EUR {offer.get_price_eur():.2f}  "
            f"score {score:.1f}"
        )

    print()
    print(explain_top_offer(surviving_offers, profile, ranked_offers[0]))
    print()


def run_search(destination_id, destination_name, date_from, date_to, offers, companies):
    """
    Runs the full filter -> score -> explain pipeline once per profile,
    for the one destination/date search the traveller asked for, and
    prints every profile's result. offers is the already-loaded, already
    -valid list of Offer objects shared by all 5 profiles - each profile
    just filters and scores that same shared pool differently. companies
    is passed straight through to print_profile_results() and render.py
    so both can show each offer's company name.

    Also collects every profile's own filter/rank results into one
    list (profile_results) and hands that same list to render.py at
    the end, so the combined HTML page is built from the EXACT same
    numbers just printed to the terminal - nothing is recalculated.
    """
    # profile_results starts as an empty list and gets one dict added
    # to it per profile, in the same order the profiles are searched.
    profile_results = []

    for profile_key in all_profile_keys():
        profile = PROFILES[profile_key]
        surviving_offers = filter_offers(offers, destination_id, date_from, date_to, profile)
        ranked_offers, scores = rank_offers(surviving_offers, profile)
        print_profile_results(profile_key, profile, surviving_offers, ranked_offers, scores, companies)

        profile_results.append({
            "profile": profile,
            "surviving_offers": surviving_offers,
            "ranked_offers": ranked_offers,
            "scores": scores,
        })

    html_path = render_results_to_html(
        destination_id, destination_name, date_from, date_to, profile_results, companies
    )
    print(f"Combined HTML report written to: {html_path}")


def run_search_command(arguments, destinations, companies, offers):
    """
    Handles `python3 -m busbidder.main search ...`: validates the
    search request itself (Layer 3), then runs the full ranking
    pipeline. Exits with a clear message (not a crash) if the dates or
    the destination are not valid.
    """
    # Layer 3 validation: the search request itself must be valid before
    # any filtering/scoring is even attempted. Both ends of the date
    # window are checked, not just one, since a search entirely in the
    # past is just as meaningless as one that merely starts in the past.
    try:
        validate_date_not_in_past("date_from", arguments.date_from)
        validate_date_not_in_past("date_to", arguments.date_to)
    except InvalidRecordError as error:
        print(f"Invalid search: {error}")
        sys.exit(1)

    # The destination itself is checked here too: an unknown destination
    # (whether typed as an ID or as a name) would otherwise just
    # silently produce zero offers for every profile, which reads like
    # a bug rather than a clear "you typed something wrong" message.
    destination_id = resolve_destination_id(arguments.destination, destinations)
    if destination_id is None:
        print(f"Unknown destination '{arguments.destination}'.")
        print("Valid destinations (ID - name):")
        # sorted(destinations.values(), key=...) lists every real
        # destination ID next to its own name, in alphabetical order by
        # name - this is clearer than printing the ID list and the name
        # list separately, since a separate list never tells you which
        # ID actually belongs to which city.
        for destination in sorted(destinations.values(), key=lambda d: d.get_name()):
            print(f"  {destination.get_destination_id()} - {destination.get_name()}")
        sys.exit(1)

    # destinations[destination_id] looks up the one Destination object
    # that matches - used just to pass its plain name into run_search
    # (and from there into render.py), so the HTML page can show a
    # readable city name instead of only the "D02"-style code.
    destination_name = destinations[destination_id].get_name()
    run_search(
        destination_id, destination_name, arguments.date_from, arguments.date_to,
        offers, companies,
    )


def run_book_command(arguments, offers, companies):
    """
    Handles `python3 -m busbidder.main book --offer-id ... --seats ...`:
    finds the one real offer matching the typed offer_id, runs every
    Layer 4 rule on the seat count via booking.create_booking(), and if
    everything passes, saves the booking and prints a confirmation.
    Any failure (unknown offer_id, bad seat count, not enough seats
    left) prints a clear message and exits with a non-zero code,
    rather than crashing or silently doing nothing.
    """
    # Find the one Offer object whose offer_id matches what was typed.
    # A plain loop (not a dict lookup) is used because offers is just
    # the flat list already loaded for searching - there is no
    # separate offer_id -> Offer dict kept anywhere else in this file.
    matching_offer = None
    for offer in offers:
        if offer.get_offer_id() == arguments.offer_id:
            matching_offer = offer
            break

    if matching_offer is None:
        print(
            f"Unknown offer_id '{arguments.offer_id}'. "
            f"Run the 'search' command first to see real offer IDs for your destination/dates."
        )
        sys.exit(1)

    # load_existing_bookings() returns [] the first time this is ever
    # run (no bookings.csv yet) - that is a normal, expected state, not
    # an error.
    existing_bookings = load_existing_bookings(BOOKINGS_CSV_PATH)

    try:
        booking = create_booking(
            matching_offer,
            arguments.seats,
            existing_bookings,
            booking_number=len(existing_bookings) + 1,
        )
    except InvalidRecordError as error:
        print(f"Booking failed: {error}")
        sys.exit(1)

    # Only reached if create_booking() did not raise - every Layer 4
    # rule passed, so this booking is now saved permanently.
    save_booking(booking, BOOKINGS_CSV_PATH)

    # companies[matching_offer.get_company_id()] looks up the real
    # company name for this offer, the same way search's results do -
    # shown here too so a booking confirmation says WHO the traveller
    # is actually booking with, not just the offer_id.
    company_name = companies[matching_offer.get_company_id()].get_name()

    print("Booking confirmed.")
    print(f"  Booking reference: {booking['booking_reference']}")
    print(f"  Offer: {booking['offer_id']} ({company_name}) to {booking['destination_id']}")
    print(f"  Seats booked: {booking['seats_selected']}")
    # :.2f formats the total price to exactly 2 decimal places, the
    # same formatting used everywhere else in this project for euros.
    print(f"  Total price: EUR {booking['total_price_eur']:.2f}")
    print(f"  Booked on: {booking['booked_on_date']}")


def main():
    # setup_logging() is called once, here, before anything else - this
    # is the one place in the whole program where it is appropriate to
    # turn logging on, since main.py is the only file meant to actually
    # run as a program.
    setup_logging()

    arguments = parse_command_line_arguments()

    # Loading happens before any validation of the traveller's own input,
    # because a missing/corrupt data file is a more fundamental problem
    # than anything the traveller typed, and should fail first. Both
    # commands need the same loaded data, so this happens once here,
    # not separately inside each command's own function.
    destinations = load_destinations(DESTINATIONS_CSV_PATH)
    companies = load_companies(COMPANIES_CSV_PATH)
    offers = load_offers_file(
        OFFERS_CSV_PATH, set(destinations.keys()), set(companies.keys())
    )

    # arguments.command is either "search" or "book" - argparse itself
    # guarantees it cannot be anything else, since required=True on the
    # subparsers means the program refuses to start without one of them.
    if arguments.command == "search":
        run_search_command(arguments, destinations, companies, offers)
    elif arguments.command == "book":
        run_book_command(arguments, offers, companies)


# This guard means main() only runs when this file is executed directly
# (python3 -m busbidder.main ...), never when another file imports it.
if __name__ == "__main__":
    main()
