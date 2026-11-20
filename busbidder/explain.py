# MEMO: This file is explain.py.
# Its only job is to turn the top-ranked offer's numbers into one short,
# plain-language paragraph: why it came out on top for THIS profile,
# which parts of it are genuinely good, and which parts are a real
# downside even though it still won overall. The spec is explicit that
# this must never claim to be "objectively best" - only best under the
# one profile's own constraints, weights and scoring assumptions - so
# that caveat is always included in the sentence this file builds.
#

from busbidder.scoring import score_breakdown_for_offer

# A score of 70 or higher on a criterion counts as a real advantage
# worth mentioning; 30 or lower counts as a real disadvantage. Anything
# in between (30-70) is treated as unremarkable and left out, so the
# explanation only talks about things that actually stand out.
HIGH_SCORE_THRESHOLD = 70.0
LOW_SCORE_THRESHOLD = 30.0

# One short phrase per criterion for each case: scoring high on it, or
# scoring low on it. A dict of (high_phrase, low_phrase) tuples, so
# adding a 9th criterion later (see scoring.py's memo) just means adding
# one more line here too.
CRITERION_PHRASES = {
    "price": ("a low price", "a high price"),
    "transfers": ("few transfers", "several transfers"),
    "duration": ("a short journey time", "a long journey time"),
    "eco": ("a low estimated CO2 footprint", "a high estimated CO2 footprint"),
    "rating": ("a high customer rating", "a low customer rating"),
    "departure": ("a departure time close to what this profile prefers",
                   "a departure time that does not match what this profile prefers"),
    "seat": ("this profile's preferred seat type", "unfortunately, not this profile's preferred seat type"),
    "scenic": ("a scenic route", "not a scenic route"),
}


def explain_top_offer(offers, profile, top_offer):
    """
    offers must be the same surviving-offers list that produced the
    ranking (needed so the min-max numbers line up). profile is the
    profile dict from profiles.py. top_offer is the Offer object that
    came first in rank_offers()'s result.

    Returns one plain-text string explaining the pick.
    """
    breakdown = score_breakdown_for_offer(offers, profile, top_offer.get_offer_id())

    advantages = []
    disadvantages = []
    for criterion_name, score in breakdown.items():
        high_phrase, low_phrase = CRITERION_PHRASES[criterion_name]
        if score >= HIGH_SCORE_THRESHOLD:
            advantages.append(high_phrase)
        elif score <= LOW_SCORE_THRESHOLD:
            disadvantages.append(low_phrase)
        # A score strictly between the two thresholds is unremarkable
        # on purpose - it is left out of both lists.

    display_name = profile["display_name"]
    offer_id = top_offer.get_offer_id()

    sentence = f"For the {display_name} profile, {offer_id} is the top-ranked offer."

    if advantages:
        # "advantage is" reads correctly with exactly one item;
        # "advantages are" is needed once there is more than one -
        # len(...) == 1 picks the grammatically correct word each time.
        word = "advantage is" if len(advantages) == 1 else "advantages are"
        # ", ".join(...) turns a list like ["few transfers", "a low price"]
        # into the single string "few transfers, a low price".
        sentence += f" Its {word} {', '.join(advantages)}."
    if disadvantages:
        word = "disadvantage is" if len(disadvantages) == 1 else "disadvantages are"
        sentence += f" Its main {word} {', '.join(disadvantages)}."

    # This last sentence is required by the spec 
    sentence += (
        f" This is only the best choice under the {display_name} profile's own "
        f"constraints and weights - a different profile could rank this same "
        f"offer lower."
    )

    return sentence
