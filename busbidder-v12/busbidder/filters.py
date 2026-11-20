# MEMO: This file is filters.py.
# Its only job is to take a list of Offer objects (already loaded and
# validated by loaders.py) and remove the ones that fail a HARD
# constraint, for one specific destination/date search and one specific
# traveller profile. What is left after this file runs is the pool that
# scoring.py (built next) will actually rank - this file never ranks
# anything itself, only keeps or removes offers.
#
# There are two kinds of hard constraints checked here, kept as two
# separate functions on purpose, because they answer two different
# questions:
#   - universal constraints: the same for every profile, every time
#     (right destination, right date window, at least 1 seat free)
#   - profile constraints: specific to the one profile being used
#     (its own budget cap, baggage minimum, rating floor, etc, read
#     straight out of profiles.py)
#
# This file contains no real personal data - it only works on the
# fictional offers generated for this course project.

from busbidder.profiles import MIN_SEATS_REQUIRED


def passes_universal_constraints(offer, destination_id, date_from, date_to):
    """
    Checks the 3 rules that apply no matter which profile is being used.
    Returns True if the offer should still be considered, False if it
    should be thrown out.
    """
    # Compare destination_id as plain text - both sides are short string
    # codes like "D01", so a direct == comparison is all that is needed.
    if offer.get_destination_id() != destination_id:
        return False

    # travel_date, date_from and date_to are all strings in "YYYY-MM-DD"
    # format. That format happens to sort the same way alphabetically as
    # it does by actual date, so plain string comparison (<=) works
    # correctly here without needing to convert anything to a real date.
    travel_date = offer.get_travel_date()
    if travel_date < date_from or travel_date > date_to:
        return False

    # MIN_SEATS_REQUIRED is an int (1), imported from profiles.py so
    # there is exactly one place in the whole program that says what
    # "enough seats" means.
    if offer.get_seats_available() < MIN_SEATS_REQUIRED:
        return False

    return True


def passes_profile_hard_constraints(offer, profile):
    """
    Checks one profile's own hard_constraints dictionary (from
    profiles.py) against one offer. A value of None in that dictionary
    means "this profile has no rule for this field", so it is skipped.
    Returns True if the offer should still be considered, False if it
    should be thrown out.
    """
    hard_constraints = profile["hard_constraints"]

    max_price_eur = hard_constraints["max_price_eur"]
    if max_price_eur is not None and offer.get_price_eur() > max_price_eur:
        return False

    min_baggage_kg = hard_constraints["min_baggage_kg"]
    if min_baggage_kg is not None and offer.get_luggage_allowance_kg() < min_baggage_kg:
        return False

    min_rating = hard_constraints["min_rating"]
    if min_rating is not None and offer.get_customer_rating() < min_rating:
        return False

    must_be_refundable = hard_constraints["must_be_refundable"]
    if must_be_refundable is True and offer.get_refundable() is not True:
        return False

    must_be_changeable = hard_constraints["must_be_changeable"]
    if must_be_changeable is True and offer.get_changeable() is not True:
        return False

    return True


def filter_offers(offers, destination_id, date_from, date_to, profile):
    """
    Runs every offer in the given list through both hard-constraint
    checks above, for one destination/date search and one profile.
    Returns a new list containing only the offers that passed both -
    the original list passed in is never changed.
    """
    surviving_offers = []
    for offer in offers:
        if not passes_universal_constraints(offer, destination_id, date_from, date_to):
            continue
        if not passes_profile_hard_constraints(offer, profile):
            continue
        surviving_offers.append(offer)

    return surviving_offers
