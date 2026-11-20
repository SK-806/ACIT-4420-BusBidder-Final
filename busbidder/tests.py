# MEMO: This file is tests.py.
# Its only job is to automatically check that every other file in this
# project behaves correctly - normal cases, invalid-input cases,
# missing-data cases, and boundary cases (the exact edge where a rule
# switches from "allowed" to "rejected", e.g. 6 seats vs 7 seats).
# Every module up to now has only been verified BY HAND, one command at
# a time, during the build - this file turns those same checks into
# something that re-runs itself automatically, every time, with one
# command, so a future change that breaks something old gets caught
# immediately instead of silently.
#
# Built using Python's own built-in `unittest` module, not a third-
# party testing library - this whole project only uses the Python
# standard library, and unittest is already part of it, so no extra
# installation is ever needed to run these tests.
#
# Run with:  python3 -m busbidder.tests
# (or, for more detail on each individual test:
#  python3 -m unittest busbidder.tests -v)
#
# This file contains no real personal data - every destination,
# company, offer and booking used below is fictional, either read from
# this project's own generated CSV files or built directly in this
# file for one specific test.

import unittest
from datetime import date, timedelta

from busbidder.booking import (
    MAX_SEATS_PER_BOOKING,
    MIN_SEATS_PER_BOOKING,
    BOOKING_REFERENCE_PATTERN,
    create_booking,
    validate_seats_selected,
)
from busbidder.exceptions import InvalidIdentifierError, InvalidRecordError
from busbidder.explain import explain_top_offer
from busbidder.filters import (
    filter_offers,
    passes_profile_hard_constraints,
    passes_universal_constraints,
)
from busbidder.loaders import (
    OFFER_ID_PATTERN,
    load_companies,
    load_destinations,
    load_offers_file,
    parse_offer_row,
)
from busbidder.main import resolve_destination_id, validate_date_not_in_past
from busbidder.models import Company, Destination, Offer
from busbidder.profiles import PROFILES, SOFT_CRITERIA, all_profile_keys, validate_profile_weights
from busbidder.scoring import CRITERION_FUNCTIONS, min_max_normalise, rank_offers, score_offers

# These 4 paths point at the real, committed CSV files this project
# ships with - the same files main.py itself reads from. Testing
# against the real files (rather than fake copies) means these tests
# are checking the actual deliverable, not a separate pretend version
# of it.
DESTINATIONS_CSV_PATH = "data/destinations.csv"
COMPANIES_CSV_PATH = "data/companies.csv"
OFFERS_CSV_PATH = "data/offers.csv"
OFFERS_INVALID_CSV_PATH = "data/offers_invalid.csv"


def make_test_offer(
    offer_id="OFR-2026-0001",
    company_id="C1",
    destination_id="D01",
    travel_date="2026-12-01",
    departure_time="08:00",
    arrival_time="10:00",
    arrival_day_offset=0,
    duration_minutes=120,
    price_eur=50.0,
    transfers=0,
    luggage_allowance_kg=20,
    changeable=True,
    refundable=True,
    seats_available=5,
    customer_rating=4.0,
    co2_estimate_kg=10.0,
    seat_type="window",
    scenic_route=False,
):
    """
    Builds one complete, valid Offer object with sensible default
    values for every field. Every test below that needs an Offer calls
    this instead of writing out all 19 constructor arguments itself -
    a test only passes in the 1 or 2 fields it actually cares about
    (e.g. make_test_offer(price_eur=5.0)) and gets realistic, valid
    values for everything else for free.
    """
    return Offer(
        offer_id=offer_id,
        company_id=company_id,
        destination_id=destination_id,
        origin="Madrid",
        travel_date=travel_date,
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


class TestExceptions(unittest.TestCase):
    """Normal case: the 2 custom exceptions store and display the right information."""

    def test_invalid_identifier_error_message(self):
        error = InvalidIdentifierError("offer_id", "BAD_ID", OFFER_ID_PATTERN.pattern)
        self.assertEqual(error.field_name, "offer_id")
        self.assertEqual(error.value, "BAD_ID")
        self.assertIn("BAD_ID", str(error))

    def test_invalid_record_error_message(self):
        error = InvalidRecordError("price_eur", "-15.0 is negative")
        self.assertEqual(error.field_name, "price_eur")
        self.assertIn("price_eur", str(error))
        self.assertIn("negative", str(error))


class TestModels(unittest.TestCase):
    """Normal case: every get_ method returns exactly what was passed into __init__."""

    def test_destination_getters(self):
        destination = Destination("D01", "Alicante", 420)
        self.assertEqual(destination.get_destination_id(), "D01")
        self.assertEqual(destination.get_name(), "Alicante")
        self.assertEqual(destination.get_approx_distance_km(), 420)

    def test_company_getters(self):
        company = Company("C1", "SolRuta", "Budget option, frequent departures")
        self.assertEqual(company.get_company_id(), "C1")
        self.assertEqual(company.get_name(), "SolRuta")
        self.assertEqual(company.get_profile_description(), "Budget option, frequent departures")

    def test_offer_getters(self):
        offer = make_test_offer(price_eur=42.91, seats_available=3)
        self.assertEqual(offer.get_price_eur(), 42.91)
        self.assertEqual(offer.get_seats_available(), 3)


class TestLoaders(unittest.TestCase):
    """
    normal: the real, committed data files load cleanly, with at
      least the spec's own stated minimum of offers.
    invalid: the real, committed offers_invalid.csv is fully rejected,
      every single row.
    missing-data: a nonexistent file path raises instead of being
      silently swallowed - loaders.py deliberately lets this kind of
      error propagate, since a missing file is more fundamental than
      one bad row inside an existing file.
    boundary: seats_available = 0 is valid (sold out, not an error);
      seats_available = -1 is not. Also checks OFFER_ID_PATTERN itself
      directly against a few known-good and known-bad id strings.
    """

    def test_normal_destinations_and_companies_load(self):
        destinations = load_destinations(DESTINATIONS_CSV_PATH)
        companies = load_companies(COMPANIES_CSV_PATH)
        self.assertEqual(len(destinations), 15)
        self.assertEqual(len(companies), 5)

    def test_normal_offers_load_with_at_least_the_spec_minimum(self):
        destinations = load_destinations(DESTINATIONS_CSV_PATH)
        companies = load_companies(COMPANIES_CSV_PATH)
        offers = load_offers_file(
            OFFERS_CSV_PATH, set(destinations.keys()), set(companies.keys())
        )
        # >=75 is the spec's own stated minimum (15 destinations x 5
        # companies). Checked as "at least" rather than one exact
        # number, since the real count can grow if the dataset is ever
        # regenerated and happens to draw more random "second offer"
        # routes - the floor of 75 is the only thing truly guaranteed.
        self.assertGreaterEqual(len(offers), 75)

    def test_invalid_file_rejects_every_single_row(self):
        destinations = load_destinations(DESTINATIONS_CSV_PATH)
        companies = load_companies(COMPANIES_CSV_PATH)
        offers = load_offers_file(
            OFFERS_INVALID_CSV_PATH, set(destinations.keys()), set(companies.keys())
        )
        # Every row in this file is deliberately broken in its own
        # different way (see validation-rules.md Layer 1), so none of
        # them should ever come back as a valid Offer.
        self.assertEqual(len(offers), 0)

    def test_missing_file_raises_instead_of_being_swallowed(self):
        # FileNotFoundError is a built-in Python exception, raised
        # automatically the moment open() itself fails. loaders.py does
        # not catch it anywhere, on purpose, so it is expected to reach
        # all the way up to this test.
        with self.assertRaises(FileNotFoundError):
            load_destinations("data/this_file_does_not_exist.csv")

    def test_boundary_zero_seats_is_valid_but_negative_is_not(self):
        known_destination_ids = {"D01"}
        known_company_ids = {"C1"}
        base_row = {
            "offer_id": "OFR-2026-0001", "destination_id": "D01", "company_id": "C1",
            "price_eur": "50.0", "customer_rating": "4.0", "duration_minutes": "120",
            "transfers": "0", "luggage_allowance_kg": "20", "co2_estimate_kg": "10.0",
            "changeable": "True", "refundable": "True", "scenic_route": "False",
            "seat_type": "window", "arrival_day_offset": "0",
            "departure_time": "08:00", "arrival_time": "10:00",
            "origin": "Madrid", "travel_date": "2026-12-01",
        }

        # dict(base_row, seats_available="0") copies base_row and
        # overrides just that one key - the rest of the row stays valid,
        # so only the seats_available boundary is actually being tested.
        zero_seats_row = dict(base_row, seats_available="0")
        offer = parse_offer_row(zero_seats_row, known_destination_ids, known_company_ids)
        self.assertEqual(offer.get_seats_available(), 0)

        negative_seats_row = dict(base_row, seats_available="-1")
        with self.assertRaises(InvalidRecordError):
            parse_offer_row(negative_seats_row, known_destination_ids, known_company_ids)

    def test_boundary_offer_id_pattern_matches_exactly(self):
        self.assertTrue(OFFER_ID_PATTERN.fullmatch("OFR-2026-0001"))
        self.assertFalse(OFFER_ID_PATTERN.fullmatch("OFFER_ABC"))
        # One digit short in the final group - must fail, not "mostly match".
        self.assertFalse(OFFER_ID_PATTERN.fullmatch("OFR-2026-001"))


class TestFilters(unittest.TestCase):
    """
    normal: an offer matching every rule passes.
    invalid/boundary: wrong destination, a date outside the search
      window, 0 seats, and a broken profile hard constraint are each
      individually rejected.
    """

    def test_normal_offer_passes_every_universal_constraint(self):
        offer = make_test_offer(destination_id="D01", travel_date="2026-12-05", seats_available=2)
        self.assertTrue(passes_universal_constraints(offer, "D01", "2026-12-01", "2026-12-10"))

    def test_wrong_destination_is_rejected(self):
        offer = make_test_offer(destination_id="D01")
        self.assertFalse(passes_universal_constraints(offer, "D02", "2026-12-01", "2026-12-10"))

    def test_date_outside_window_is_rejected(self):
        offer = make_test_offer(destination_id="D01", travel_date="2026-01-01")
        self.assertFalse(passes_universal_constraints(offer, "D01", "2026-12-01", "2026-12-10"))

    def test_boundary_zero_seats_fails_universal_constraint(self):
        offer = make_test_offer(seats_available=0)
        self.assertFalse(
            passes_universal_constraints(offer, offer.get_destination_id(), "2026-12-01", "2026-12-10")
        )

    def test_profile_hard_constraint_price_cap_boundary(self):
        # Practical's max_price_eur is locked at 150.0 in profiles.py.
        profile = PROFILES["practical"]
        just_under_cap = make_test_offer(price_eur=149.99, changeable=True)
        just_over_cap = make_test_offer(price_eur=150.01, changeable=True)
        self.assertTrue(passes_profile_hard_constraints(just_under_cap, profile))
        self.assertFalse(passes_profile_hard_constraints(just_over_cap, profile))

    def test_filter_offers_combines_both_kinds_of_constraint(self):
        profile = PROFILES["practical"]  # requires changeable=True, max EUR 150
        matching_offer = make_test_offer(
            offer_id="OFR-2026-0001", destination_id="D01", travel_date="2026-12-05",
            price_eur=100.0, changeable=True,
        )
        wrong_destination_offer = make_test_offer(
            offer_id="OFR-2026-0002", destination_id="D02", travel_date="2026-12-05",
            price_eur=100.0, changeable=True,
        )
        too_expensive_offer = make_test_offer(
            offer_id="OFR-2026-0003", destination_id="D01", travel_date="2026-12-05",
            price_eur=200.0, changeable=True,
        )
        offers = [matching_offer, wrong_destination_offer, too_expensive_offer]
        surviving_offers = filter_offers(offers, "D01", "2026-12-01", "2026-12-10", profile)
        self.assertEqual([o.get_offer_id() for o in surviving_offers], ["OFR-2026-0001"])


class TestScoring(unittest.TestCase):
    """
    normal: min-max normalisation matches the hand-worked formula.
    boundary: every value tied (max == min) gives everyone 100.0
      instead of crashing on a divide-by-zero.
    missing-data: scoring an empty offer list returns {} instead of
      crashing when min()/max() have nothing at all to compare.
    """

    def test_normal_min_max_normalisation_cost_type(self):
        raw_values = {"A": 10.0, "B": 20.0, "C": 30.0}
        scores = min_max_normalise(raw_values, invert=True)
        self.assertAlmostEqual(scores["A"], 100.0)
        self.assertAlmostEqual(scores["B"], 50.0)
        self.assertAlmostEqual(scores["C"], 0.0)

    def test_boundary_all_tied_values_score_100(self):
        raw_values = {"A": 5.0, "B": 5.0, "C": 5.0}
        scores = min_max_normalise(raw_values, invert=False)
        self.assertEqual(scores, {"A": 100.0, "B": 100.0, "C": 100.0})

    def test_missing_data_empty_offer_list_scores_to_empty_dict(self):
        self.assertEqual(score_offers([], PROFILES["practical"]), {})

    def test_all_8_criteria_are_registered(self):
        # Confirms the decorator/registry pattern actually registered
        # every one of the 8 criteria named in profiles.SOFT_CRITERIA -
        # a typo in a @criterion(...) name in scoring.py would show up
        # here as a missing key, not silently do nothing.
        for criterion_name in SOFT_CRITERIA:
            self.assertIn(criterion_name, CRITERION_FUNCTIONS)

    def test_rank_offers_sorts_highest_score_first(self):
        cheap_offer = make_test_offer(offer_id="OFR-2026-0001", price_eur=10.0)
        expensive_offer = make_test_offer(offer_id="OFR-2026-0002", price_eur=100.0)
        ranked_offers, scores = rank_offers([expensive_offer, cheap_offer], PROFILES["budget_friendly"])
        self.assertEqual(ranked_offers[0].get_offer_id(), "OFR-2026-0001")
        self.assertGreaterEqual(scores["OFR-2026-0001"], scores["OFR-2026-0002"])


class TestExplain(unittest.TestCase):
    """boundary: exactly 1 advantage/disadvantage uses singular wording; 2+ uses plural."""

    def test_singular_wording_for_exactly_one_advantage_and_one_disadvantage(self):
        profile = PROFILES["budget_friendly"]  # weights: price 0.70, scenic 0.30
        # Cheapest offer, but NOT scenic: price is the only advantage,
        # "not a scenic route" is the only disadvantage - exactly 1 of
        # each, so singular wording ("advantage is"/"disadvantage is")
        # is the grammatically correct choice here.
        cheap_non_scenic_offer = make_test_offer(
            offer_id="OFR-2026-0001", price_eur=1.0, scenic_route=False
        )
        other_offer = make_test_offer(
            offer_id="OFR-2026-0002", price_eur=999.0, scenic_route=True
        )
        sentence = explain_top_offer([cheap_non_scenic_offer, other_offer], profile, cheap_non_scenic_offer)
        self.assertIn("advantage is", sentence)
        self.assertNotIn("advantages are", sentence)
        self.assertIn("disadvantage is", sentence)

    def test_plural_wording_for_two_advantages(self):
        profile = PROFILES["budget_friendly"]
        # Cheapest AND scenic: both criteria score as advantages, so
        # "advantages are" (plural) is the grammatically correct choice.
        cheap_scenic_offer = make_test_offer(
            offer_id="OFR-2026-0001", price_eur=1.0, scenic_route=True
        )
        other_offer = make_test_offer(
            offer_id="OFR-2026-0002", price_eur=999.0, scenic_route=False
        )
        sentence = explain_top_offer([cheap_scenic_offer, other_offer], profile, cheap_scenic_offer)
        self.assertIn("advantages are", sentence)

    def test_caveat_sentence_always_present(self):
        profile = PROFILES["leisure"]
        offer = make_test_offer()
        sentence = explain_top_offer([offer], profile, offer)
        # The spec requires this exact caveat - the ranking must never
        # be described as objectively best, only best for one profile.
        self.assertIn("only the best choice under the", sentence)


class TestProfiles(unittest.TestCase):
    """
    normal: every one of the 5 locked profiles' weights sum to 1.0.
    invalid: a deliberately broken profile (weights that do not sum to
      1.0) is rejected.
    """

    def test_normal_all_locked_profiles_pass(self):
        # validate_profile_weights raises on failure, so simply not
        # raising, for every real profile, IS the pass condition here.
        for profile_key in all_profile_keys():
            validate_profile_weights(profile_key)

    def test_invalid_weights_not_summing_to_one_is_rejected(self):
        # A deliberately-broken profile is added to PROFILES just for
        # this one test, then removed again in the finally block - this
        # never changes or risks any of the 5 real, locked profiles.
        PROFILES["_test_broken_profile"] = {
            "display_name": "Broken",
            "soft_weights": {name: 0.0 for name in SOFT_CRITERIA},
        }
        try:
            with self.assertRaises(ValueError):
                validate_profile_weights("_test_broken_profile")
        finally:
            del PROFILES["_test_broken_profile"]


class TestBooking(unittest.TestCase):
    """
    boundary: seats_selected exactly at the allowed min/max succeeds;
      one step beyond either edge, plus a non-integer and a bool, are
      all rejected.
    normal: a booking within capacity succeeds, with a correctly
      formatted reference and correct total price.
    invalid: booking more seats than actually remain (accounting for
      earlier bookings) is rejected.
    boundary: booking exactly the last remaining seat succeeds.

    None of these tests call save_booking() - create_booking() alone
    is pure (it only returns a dict, no file is touched), so these
    tests never write to the real data/bookings.csv file.
    """

    def test_boundary_seats_selected_values(self):
        for valid_value in (MIN_SEATS_PER_BOOKING, MAX_SEATS_PER_BOOKING):
            validate_seats_selected(valid_value)  # should not raise

        invalid_values = (
            MIN_SEATS_PER_BOOKING - 1,
            MAX_SEATS_PER_BOOKING + 1,
            2.5,
            True,
        )
        for invalid_value in invalid_values:
            with self.assertRaises(InvalidRecordError):
                validate_seats_selected(invalid_value)

    def test_normal_booking_within_capacity_succeeds(self):
        offer = make_test_offer(offer_id="OFR-2026-0001", seats_available=3, price_eur=20.0)
        booking = create_booking(offer, 2, bookings=[], booking_number=1)
        self.assertTrue(BOOKING_REFERENCE_PATTERN.fullmatch(booking["booking_reference"]))
        self.assertEqual(booking["seats_selected"], 2)
        self.assertEqual(booking["total_price_eur"], 40.0)

    def test_invalid_booking_more_than_remaining_capacity(self):
        offer = make_test_offer(offer_id="OFR-2026-0002", seats_available=2)
        # A fake "already fully booked" history for this exact offer -
        # only offer_id and seats_selected are actually read by
        # seats_still_available(), so no other real CSV column is
        # needed to test this in isolation.
        existing_bookings = [{"offer_id": "OFR-2026-0002", "seats_selected": 2}]
        with self.assertRaises(InvalidRecordError):
            create_booking(offer, 1, existing_bookings, booking_number=1)

    def test_boundary_booking_exactly_the_last_remaining_seat_succeeds(self):
        offer = make_test_offer(offer_id="OFR-2026-0003", seats_available=2)
        existing_bookings = [{"offer_id": "OFR-2026-0003", "seats_selected": 1}]
        booking = create_booking(offer, 1, existing_bookings, booking_number=2)
        self.assertEqual(booking["seats_selected"], 1)


class TestMainHelpers(unittest.TestCase):
    """
    normal/boundary: resolve_destination_id resolves a real ID, a real
      name (any letter case, extra whitespace tolerated), and returns
      None for anything unknown.
    boundary: validate_date_not_in_past accepts today and any future
      date up to and including MAX_DAYS_AHEAD_ALLOWED days ahead, and
      rejects anything before today, anything more than
      MAX_DAYS_AHEAD_ALLOWED days ahead, and any text that is not a
      real calendar date at all (even if it looks date-shaped).
    """

    def setUp(self):
        # A tiny, self-contained destinations dict, built directly from
        # Destination objects rather than loading the real CSV file -
        # these tests should keep working no matter what
        # destinations.csv happens to contain at the time.
        self.destinations = {
            "D01": Destination("D01", "Alicante", 420),
            "D02": Destination("D02", "Barcelona", 620),
        }

    def test_resolve_by_id(self):
        self.assertEqual(resolve_destination_id("D02", self.destinations), "D02")

    def test_resolve_by_name_case_and_whitespace_insensitive(self):
        self.assertEqual(resolve_destination_id("  barcelona  ", self.destinations), "D02")

    def test_resolve_unknown_returns_none(self):
        self.assertIsNone(resolve_destination_id("Madrid", self.destinations))

    def test_boundary_today_and_future_dates_are_valid(self):
        today_text = str(date.today())
        future_text = str(date.today() + timedelta(days=1))
        validate_date_not_in_past("date_from", today_text)  # should not raise
        validate_date_not_in_past("date_from", future_text)  # should not raise

    def test_boundary_yesterday_is_invalid(self):
        yesterday_text = str(date.today() - timedelta(days=1))
        with self.assertRaises(InvalidRecordError):
            validate_date_not_in_past("date_from", yesterday_text)

    def test_malformed_date_text_is_rejected(self):
        # Each of these strings is date-shaped (digits and dashes in
        # the right positions) but is not a real calendar date, so
        # plain text comparison would have let all of them through -
        # date.fromisoformat() must reject every one of them.
        malformed_dates = [
            "2027-0-20",   # month 0 does not exist
            "2026-13-01",  # month 13 does not exist
            "2026-02-30",  # no 30th of February, even in a leap year
            "notadate",    # not date-shaped at all
        ]
        for malformed_date in malformed_dates:
            with self.assertRaises(InvalidRecordError):
                validate_date_not_in_past("date_from", malformed_date)

    def test_boundary_exactly_90_days_ahead_is_valid(self):
        boundary_text = str(date.today() + timedelta(days=90))
        validate_date_not_in_past("date_to", boundary_text)  # should not raise

    def test_boundary_91_days_ahead_is_invalid(self):
        too_far_text = str(date.today() + timedelta(days=91))
        with self.assertRaises(InvalidRecordError):
            validate_date_not_in_past("date_to", too_far_text)


class TestFullPipelineIntegration(unittest.TestCase):
    """
    One end-to-end smoke test against the real, committed data: load
    -> filter -> rank -> explain for one real profile, across every
    real destination until at least one has matching offers, then
    checks the results are internally consistent (sorted highest score
    first, and the explanation actually names the real top offer).
    """

    def test_full_pipeline_runs_and_is_internally_consistent(self):
        destinations = load_destinations(DESTINATIONS_CSV_PATH)
        companies = load_companies(COMPANIES_CSV_PATH)
        offers = load_offers_file(
            OFFERS_CSV_PATH, set(destinations.keys()), set(companies.keys())
        )

        profile = PROFILES["practical"]
        # A 30-day-wide window starting today is comfortably wider than
        # the dataset's own ~7-16-days-out travel window (see
        # scripts/generate_dataset.py), so this test keeps working
        # correctly no matter which day the dataset was last generated.
        date_from = str(date.today())
        date_to = str(date.today() + timedelta(days=30))

        any_matches_found = False
        for destination_id in destinations:
            surviving_offers = filter_offers(offers, destination_id, date_from, date_to, profile)
            if not surviving_offers:
                continue

            any_matches_found = True
            ranked_offers, scores = rank_offers(surviving_offers, profile)

            # The ranking must actually be sorted highest score first.
            ranked_scores = [scores[offer.get_offer_id()] for offer in ranked_offers]
            self.assertEqual(ranked_scores, sorted(ranked_scores, reverse=True))

            # explain_top_offer must not crash, and must name the real
            # top offer somewhere in its own sentence.
            explanation = explain_top_offer(surviving_offers, profile, ranked_offers[0])
            self.assertIn(ranked_offers[0].get_offer_id(), explanation)
            break  # one real destination with matches is enough to prove this works

        self.assertTrue(any_matches_found, "Expected at least one destination to have matching offers")


# This lets the whole file be run directly too (python3 busbidder/tests.py),
# not only via "python3 -m busbidder.tests".
if __name__ == "__main__":
    unittest.main()
