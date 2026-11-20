# MEMO: This file is profiles.py.
# Its only job is to store the 5 traveller profiles as plain data.
# A "profile" is just a named bundle of two things:
#   1) hard_constraints  - pass/fail rules. An offer that breaks even one
#                          of these is thrown away before any scoring.
#   2) soft_weights      - percentages (as decimals) used AFTER the hard
#                          constraints, to rank whatever offers survived.
# No classes, no decorators, no fancy logic in this file on purpose -
# it is meant to be nothing but numbers and short text, so it is easy to
# read and easy to change a single value later without touching any
# other file.
# This file contains no real personal data - every name, number and
# preference below is fictional, written for this course project only.


# Every profile applies these 3 rules too, in addition to its own rules
# below. They are kept here, separately, because they are the same for
# every profile and are not something any profile can turn off.
#   - the offer must go to the destination the traveller asked for
#   - the offer must be on a date inside the traveller's travel window
#   - the offer must have at least this many free seats
# MIN_SEATS_REQUIRED is an int because seats are always counted in whole
# numbers - you cannot book "2.5 seats".
MIN_SEATS_REQUIRED = 1


# This tuple lists the 8 criteria that can be soft-ranked. It is a tuple
# (not a list) because this set of names should never change while the
# program is running - a tuple just makes that "do not edit while running"
# intention visible in the code itself.
SOFT_CRITERIA = (
    "price",        # how cheap the ticket is
    "transfers",    # how few bus changes the journey has
    "duration",     # how short the total journey time is
    "eco",          # how low the estimated CO2 for the trip is
    "rating",       # how high the company's customer rating is
    "departure",    # how close the departure time is to what this profile prefers
    "seat",         # whether the seat type matches what this profile prefers
    "scenic",       # whether the route is a scenic one, if this profile cares
)

# Weights are percentages written as decimals (20% is written as 0.20)
# because that is the format the scoring formula needs later: a weight
# gets multiplied directly against a normalised 0-100 score, so it has
# to be a plain fraction of 1.0, not a whole number like 20.
# Every profile's weights must add up to 1.0 (checked by the function
# near the bottom of this file).


# ---------------------------------------------------------------------
# Profile 1: Practical
# This is the student's own real travel-booking preferences.
# ---------------------------------------------------------------------
PRACTICAL = {
    # display_name is a string because it is only ever shown as text on
    # the report/HTML page, never used in a calculation.
    "display_name": "Practical",

    "hard_constraints": {
        # max_price_eur is a float (not an int) because prices in our
        # offers.csv file have cents, e.g. 42.91, not just whole euros.
        "max_price_eur": 150.0,
        # min_baggage_kg is an int because our dataset only ever stores
        # baggage allowance as a whole number of kilograms.
        "min_baggage_kg": 20,
        # min_rating is None because this profile does not care about
        # customer rating at all - None means "no rule here".
        "min_rating": None,
        # must_be_refundable is None because this profile does not care
        # about refundability - it only cares about changeability below.
        "must_be_refundable": None,
        # must_be_changeable is a bool (True/False) because the offers
        # data stores changeable as True or False, so this rule needs to
        # match that same True/False type exactly.
        "must_be_changeable": True,
    },

    "soft_weights": {
        "price": 0.20,       # price still matters, just less than transfers/duration
        "transfers": 0.35,   # fewer transfers matters the most to this profile
        "duration": 0.30,    # a shorter trip matters almost as much
        "eco": 0.0,           # does not matter at all - weight is zero
        "rating": 0.0,        # does not matter at all - weight is zero
        "departure": 0.0,     # does not matter at all - weight is zero
        "seat": 0.15,         # a window seat is a real, smaller preference
        "scenic": 0.0,         # does not matter at all - weight is zero
    },

    # preferred_seat is a string, because the offers data will store the
    # seat type as text ("window", "aisle", "other"), so the preference
    # has to be the same text type to compare against it later.
    "preferred_seat": "window",
    # preferred_departure is None because this profile said timing is
    # "never the matter" - so there is no target time to compare against.
    "preferred_departure": None,
    # wants_scenic_route is None because the "scenic" weight above is
    # zero, so there is nothing to compare for this profile.
    "wants_scenic_route": None,
}


# ---------------------------------------------------------------------
# Profile 2: Budget-friendly
# ---------------------------------------------------------------------
BUDGET_FRIENDLY = {
    "display_name": "Budget-friendly",

    "hard_constraints": {
        # max_price_eur was originally 100.0, but real Spanish inter-city
        # bus fares for these routes (and our own generated dataset,
        # EUR 3.18-50.53) never actually come close to that - so a
        # 100.0 cap never rejected a single offer. Lowered to 30.0 EUR
        # (close to this dataset's own median price of EUR 25.73) so
        # this profile's whole identity - being the cost-sensitive one -
        # actually does something: it now rejects the pricier, usually
        # longer-distance routes, leaving only genuinely cheap offers
        # for the soft price/scenic weights below to rank.
        "max_price_eur": 30.0,   # float, same reason as above (prices have cents)
        "min_baggage_kg": None,   # no baggage rule for this profile
        "min_rating": None,       # no rating rule for this profile
        "must_be_refundable": True,  # bool, must match the offers data's True/False
        "must_be_changeable": None,  # no changeability rule for this profile
    },

    "soft_weights": {
        "price": 0.70,     # cheaper is strongly preferred, even below the price cap
        "transfers": 0.0,   # does not matter - weight is zero
        "duration": 0.0,     # does not matter - weight is zero
        "eco": 0.0,           # does not matter - weight is zero
        "rating": 0.0,         # does not matter - weight is zero
        "departure": 0.0,      # does not matter - weight is zero
        "seat": 0.0,            # does not matter - weight is zero
        "scenic": 0.30,           # a scenic route is a real bonus for this profile
    },

    "preferred_seat": None,        # no seat preference, weight above is zero
    "preferred_departure": None,   # no departure-time preference
    # wants_scenic_route is True (a real value, not None) because the
    # "scenic" weight above is NOT zero - this profile really does want
    # scenic routes, so there is something real to compare against here.
    "wants_scenic_route": True,
}


# ---------------------------------------------------------------------
# Profile 3: Business-rush
# ---------------------------------------------------------------------
BUSINESS_RUSH = {
    "display_name": "Business-rush",

    "hard_constraints": {
        "max_price_eur": 200.0,   # float, a looser budget cap than the other profiles
        "min_baggage_kg": 10,     # int, a smaller minimum than Practical's
        "min_rating": 3.5,        # float, because ratings in the data are decimals (e.g. 4.1)
        "must_be_refundable": None,   # no refundability rule for this profile
        "must_be_changeable": True,   # bool, must be changeable, no exceptions
    },

    "soft_weights": {
        "price": 0.0,        # price does not drive the ranking at all, only the cap above does
        "transfers": 0.20,    # fewer transfers matters
        "duration": 0.30,      # a shorter trip matters the most for this profile
        "eco": 0.15,            # a real but moderate ("medium") amount of weight
        "rating": 0.0,           # does not matter - weight is zero
        "departure": 0.20,        # departing close to the morning target matters
        "seat": 0.15,              # an aisle seat is a real, smaller preference
        "scenic": 0.0,               # does not matter - weight is zero
    },

    "preferred_seat": "aisle",       # string, matches the offers data's seat_type text
    # preferred_departure is a string ("morning") because the offers
    # data will store an actual clock time, and the scoring step (built
    # later) is what turns "morning" into a comparable target.
    "preferred_departure": "morning",
    "wants_scenic_route": None,      # no scenic preference, weight above is zero
}


# ---------------------------------------------------------------------
# Profile 4: Review-focused
# ---------------------------------------------------------------------
REVIEW_FOCUSED = {
    "display_name": "Review-focused",

    "hard_constraints": {
        "max_price_eur": 150.0,
        "min_baggage_kg": 20,
        "min_rating": 4.0,             # a stricter floor than Business-rush's 3.5
        "must_be_refundable": True,    # both flexibility flags are required here
        "must_be_changeable": True,
    },

    "soft_weights": {
        "price": 0.0,        # price does not drive the ranking, only the cap does
        "transfers": 0.0,     # does not matter - weight is zero
        "duration": 0.0,       # does not matter - weight is zero
        "eco": 0.15,             # a real but smaller amount of weight
        # rating keeps mattering ABOVE the 4.0-star floor too, not just
        # as a pass/fail cutoff - this is the main point of this
        # profile, so it gets the largest single weight of any profile.
        "rating": 0.65,
        "departure": 0.0,         # does not matter - weight is zero
        "seat": 0.20,               # a window seat is a real preference
        "scenic": 0.0,                # does not matter - weight is zero
    },

    "preferred_seat": "window",
    "preferred_departure": None,     # no departure-time preference
    "wants_scenic_route": None,      # no scenic preference, weight above is zero
}


# ---------------------------------------------------------------------
# Profile 5: Leisure
# A relaxed, comfort- and experience-focused tourist profile - this one
# replaced the earlier "Balanced / Neutral" idea entirely.
# ---------------------------------------------------------------------
LEISURE = {
    "display_name": "Leisure",

    "hard_constraints": {
        "max_price_eur": 200.0,
        "min_baggage_kg": 20,
        "min_rating": 3.5,
        "must_be_refundable": True,
        "must_be_changeable": True,
    },

    "soft_weights": {
        "price": 0.0,        # price does not drive the ranking, only the cap does
        "transfers": 0.0,     # does not matter - weight is zero
        "duration": 0.0,       # does not matter - weight is zero
        "eco": 0.20,             # a real, moderate ("medium") amount of weight
        "rating": 0.0,            # does not matter beyond the hard floor above
        "departure": 0.25,          # departing close to the morning target matters
        "seat": 0.20,                 # a window seat is a real preference
        # scenic gets the single biggest weight of any criterion in this
        # profile, because "wants a nice view" is the main idea behind a
        # leisure/tourist traveller.
        "scenic": 0.35,
    },

    "preferred_seat": "window",
    "preferred_departure": "morning",
    "wants_scenic_route": True,
}


# This dictionary collects all 5 profiles under short, lowercase keys,
# so other files can look one up by name, e.g. PROFILES["practical"],
# instead of needing to import 5 separate variable names one by one.
PROFILES = {
    "practical": PRACTICAL,
    "budget_friendly": BUDGET_FRIENDLY,
    "business_rush": BUSINESS_RUSH,
    "review_focused": REVIEW_FOCUSED,
    "leisure": LEISURE,
}

# A small positive number used only for comparing a weight total to 1.0.
# It is needed because adding decimal fractions in Python (e.g. three
# lots of 1/3) does not always land on exactly 1.0 - it can come out as
# 0.9999999999999999 due to how computers store decimal numbers. This
# tolerance says "close enough to 1.0 counts as 1.0".
WEIGHT_TOTAL_TOLERANCE = 0.000001


def validate_profile_weights(profile_key):
    """
    Checks one profile's soft_weights dictionary. Raises ValueError if a
    weight is listed for a criterion that does not exist in SOFT_CRITERIA,
    or if the weights do not add up to 1.0. Used by tests.py later so a
    typo in a weight fails loudly instead of silently producing a wrong
    ranking.
    """
    # Look up the one profile dictionary we were asked to check.
    profile = PROFILES[profile_key]
    # Pull out just its soft_weights part.
    weights = profile["soft_weights"]

    # set(weights) gives the criterion names actually used by this
    # profile; set(SOFT_CRITERIA) gives the criterion names that are
    # allowed to exist at all. Subtracting one set from the other gives
    # anything used that should not exist (a typo, most likely).
    unknown_criteria = set(weights) - set(SOFT_CRITERIA)
    if unknown_criteria:
        raise ValueError(
            f"profile '{profile_key}' has unknown criteria: {unknown_criteria}"
        )

    # sum() adds up every weight value in the dictionary.
    weight_total = sum(weights.values())
    # abs() makes a negative difference positive, so we can compare the
    # size of the gap from 1.0 without worrying about which side it is on.
    if abs(weight_total - 1.0) > WEIGHT_TOTAL_TOLERANCE:
        raise ValueError(
            f"profile '{profile_key}' weights add up to {weight_total}, not 1.0"
        )


def all_profile_keys():
    """Returns a plain list of every profile's short key name."""
    # list() turns the dictionary's keys into an actual list, since
    # PROFILES.keys() on its own is a view, not a list.
    return list(PROFILES.keys())


# This block only runs when this file is run directly
# (python3 busbidder/profiles.py), not when another file imports it.
# It is a quick manual self-check, not an automated test.
if __name__ == "__main__":
    # Go through every profile key, one at a time.
    for key in all_profile_keys():
        # This will raise an error and stop the program if anything
        # is wrong with that profile's weights.
        validate_profile_weights(key)
        # Only reached if the check above passed without error.
        print(f"{key}: OK, weights add up to 1.0")
