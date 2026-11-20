# MEMO: This file is scoring.py.
# Its only job is to take the offers that survived filters.py and rank
# them for one specific traveller profile. Ranking happens in 2 steps
# for each of the 8 criteria in profiles.SOFT_CRITERIA: first every
# offer's raw value (a price in euros, a duration in minutes, etc) gets
# converted to a 0-100 score using min-max normalisation, then that
# score gets multiplied by the profile's weight for that criterion and
# added into a running total per offer.
#
# The 8 criterion functions below are registered in CRITERION_FUNCTIONS
# using the @criterion(...) decorator instead of being called directly
# by name. This is the course's "metaprogramming technique" requirement:
# adding a 9th criterion later means writing one new function with
# @criterion("new_name") above it - nothing else in this file, or in
# profiles.py, or anywhere else, needs to change.
#
# This file contains no real personal data - it only works on the
# fictional offers generated for this course project.

from busbidder.profiles import SOFT_CRITERIA

# CRITERION_FUNCTIONS is a dict mapping a criterion name (a string, e.g.
# "price") to the function that knows how to score every offer on that
# criterion. It starts empty and gets filled in automatically, one entry
# at a time, every time the @criterion(...) decorator is used below.
CRITERION_FUNCTIONS = {}


def criterion(name):
    """
    This is a decorator FACTORY - calling criterion("price") returns the
    actual decorator that gets applied to the function underneath it.
    That is why it is written as a function that returns a function.
    """

    def decorator(func):
        # This line is the entire "registry" part of the pattern: it
        # just stores the function in the dict under its name, then
        # hands the function back unchanged so it can still be called
        # normally too.
        CRITERION_FUNCTIONS[name] = func
        return func

    return decorator


def min_max_normalise(raw_values_by_offer_id, invert):
    """
    Converts a dict of {offer_id: raw_number} into a new dict of
    {offer_id: score_0_to_100}, using the min and max found in this
    exact dict (not any fixed constant) - this is the "Min-Max
    normalisation" method confirmed by the instructor's email.

    invert is a bool: True for a "lower raw value is better" criterion
    (e.g. price, duration), so the smallest raw value gets the highest
    score; False for a "higher raw value is better" criterion (e.g.
    customer rating), so the largest raw value gets the highest score.
    """
    values = list(raw_values_by_offer_id.values())
    minimum = min(values)
    maximum = max(values)

    # If every offer has the exact same raw value for this criterion,
    # (maximum - minimum) would be 0, and dividing by 0 is not allowed.
    # In that case there is nothing to actually differentiate between
    # the offers on this criterion, so every offer gets the same score.
    if maximum == minimum:
        return {offer_id: 100.0 for offer_id in raw_values_by_offer_id}

    scores = {}
    for offer_id, value in raw_values_by_offer_id.items():
        if invert:
            scores[offer_id] = (maximum - value) / (maximum - minimum) * 100
        else:
            scores[offer_id] = (value - minimum) / (maximum - minimum) * 100
    return scores


# The 4 numeric criteria below (price, transfers, duration, eco) are all
# "lower is better", so each one calls min_max_normalise with invert=True.


@criterion("price")
def score_price(offers, profile):
    # profile is not actually used by this function (price is scored the
    # same way for every profile), but every criterion function takes
    # the same 2 arguments, so the scoring engine below can call all of
    # them the exact same way without needing to know which ones care
    # about the profile and which ones don't.
    raw_values = {offer.get_offer_id(): offer.get_price_eur() for offer in offers}
    return min_max_normalise(raw_values, invert=True)


@criterion("transfers")
def score_transfers(offers, profile):
    raw_values = {offer.get_offer_id(): offer.get_transfers() for offer in offers}
    return min_max_normalise(raw_values, invert=True)


@criterion("duration")
def score_duration(offers, profile):
    raw_values = {offer.get_offer_id(): offer.get_duration_minutes() for offer in offers}
    return min_max_normalise(raw_values, invert=True)


@criterion("eco")
def score_eco(offers, profile):
    raw_values = {offer.get_offer_id(): offer.get_co2_estimate_kg() for offer in offers}
    return min_max_normalise(raw_values, invert=True)


# rating is "higher is better", so invert=False - the highest star
# rating in the batch gets the top score.
@criterion("rating")
def score_rating(offers, profile):
    raw_values = {offer.get_offer_id(): offer.get_customer_rating() for offer in offers}
    return min_max_normalise(raw_values, invert=False)


# DEPARTURE_WINDOWS maps a profile's plain-text target (e.g. "morning")
# to an actual (start, end) clock-time range, both as "HH:MM" strings.
# A dict is used because more named windows (e.g. "evening") could be
# added later just by adding one more entry, with no other code change.
DEPARTURE_WINDOWS = {
    "morning": ("06:00", "12:00"),
}


@criterion("departure")
def score_departure(offers, profile):
    """
    A simple yes/no match, not a sliding scale: 100 if the offer departs
    inside the profile's preferred window, 0 if it does not. Kept
    deliberately binary rather than measuring "how close" to the window,
    to keep this criterion easy to explain and verify.
    """
    preferred_departure = profile["preferred_departure"]
    scores = {}
    if preferred_departure not in DEPARTURE_WINDOWS:
        # No target window for this profile (preferred_departure is
        # None) - this criterion's weight will be 0 for this profile
        # anyway, so the actual number here never affects the total.
        for offer in offers:
            scores[offer.get_offer_id()] = 0.0
        return scores

    window_start, window_end = DEPARTURE_WINDOWS[preferred_departure]
    for offer in offers:
        departure_time = offer.get_departure_time()
        in_window = window_start <= departure_time <= window_end
        scores[offer.get_offer_id()] = 100.0 if in_window else 0.0
    return scores


@criterion("seat")
def score_seat(offers, profile):
    """Another simple yes/no match: does the offer's seat_type match this profile's preferred_seat?"""
    preferred_seat = profile["preferred_seat"]
    scores = {}
    for offer in offers:
        is_match = preferred_seat is not None and offer.get_seat_type() == preferred_seat
        scores[offer.get_offer_id()] = 100.0 if is_match else 0.0
    return scores


@criterion("scenic")
def score_scenic(offers, profile):
    """Another simple yes/no match: is the offer scenic, for a profile that wants that?"""
    wants_scenic_route = profile["wants_scenic_route"]
    scores = {}
    for offer in offers:
        is_match = wants_scenic_route is True and offer.get_scenic_route() is True
        scores[offer.get_offer_id()] = 100.0 if is_match else 0.0
    return scores


def score_offers(offers, profile):
    """
    Runs every registered criterion function, multiplies each one's
    0-100 scores by the profile's weight for that criterion, and adds
    them all up. Returns a dict {offer_id: total_score}.
    """
    # If nothing survived filters.py for this profile/destination, there
    # is nothing to score - returning early here avoids calling any
    # criterion function on an empty list, where min()/max() would
    # otherwise crash with no values to compare.
    if not offers:
        return {}

    total_scores = {offer.get_offer_id(): 0.0 for offer in offers}

    for criterion_name in SOFT_CRITERIA:
        weight = profile["soft_weights"][criterion_name]
        # A weight of exactly 0 contributes nothing no matter what the
        # criterion function returns, so skipping it saves work and also
        # avoids calling a criterion function on an empty offers list
        # later, where min() / max() would otherwise fail.
        if weight == 0:
            continue

        score_function = CRITERION_FUNCTIONS[criterion_name]
        criterion_scores = score_function(offers, profile)

        for offer_id, score in criterion_scores.items():
            total_scores[offer_id] += score * weight

    return total_scores


def score_breakdown_for_offer(offers, profile, offer_id):
    """
    Returns {criterion_name: score_0_to_100} for just ONE offer, only
    for the criteria that actually have a nonzero weight in this
    profile. Used by explain.py to say WHY one offer scored the way it
    did, not just what its final total was. offers must be the same
    list that was scored originally, since min-max normalisation needs
    the same min/max context to give the same numbers back.
    """
    breakdown = {}
    for criterion_name in SOFT_CRITERIA:
        weight = profile["soft_weights"][criterion_name]
        if weight == 0:
            continue
        score_function = CRITERION_FUNCTIONS[criterion_name]
        criterion_scores = score_function(offers, profile)
        breakdown[criterion_name] = criterion_scores[offer_id]
    return breakdown


def rank_offers(offers, profile):
    """
    Returns (ranked_offers, scores): ranked_offers is the same list of
    Offer objects sorted from best to worst for this profile, and scores
    is the {offer_id: total_score} dict used to sort them, so the exact
    numbers behind the ranking are still available afterwards (for
    explain.py and render.py, built later).
    """
    scores = score_offers(offers, profile)
    # sorted(..., key=..., reverse=True) sorts from highest score to
    # lowest, i.e. the best offer for this profile ends up first.
    ranked_offers = sorted(offers, key=lambda offer: scores[offer.get_offer_id()], reverse=True)
    return ranked_offers, scores
