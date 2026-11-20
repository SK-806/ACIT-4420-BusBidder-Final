# MEMO: This file is render.py.
# Its only job is to take the exact same results main.py already
# computed and printed to the terminal, and also write them out as one
# static HTML file - a side-by-side visual comparison of all 5 profiles
# for the same destination/date search. This is the bonus presentation
# layer mentioned in final-project-plan.md: the CLI output on its own
# already satisfies the spec's interface requirement, this file is
# purely an extra, nicer way to look at the same numbers.
#
# This file never recomputes anything itself - it only turns numbers
# and text that were already calculated by filters.py/scoring.py/
# explain.py into HTML tags. That rule matters: it means the HTML page
# and the terminal output can never disagree with each other, because
# they are built from the exact same values, not two separate runs of
# the ranking logic.
#
# This file contains no real personal data - every offer, price and
# explanation it writes into the HTML page is fictional, generated for
# this course project only.

import html
from pathlib import Path

from busbidder.explain import explain_top_offer

# MAX_OFFERS_IN_HTML is an int - same idea as main.py's
# MAX_OFFERS_TO_PRINT, just for the HTML page instead of the terminal,
# so a destination with many offers does not produce an endlessly long
# table for any one profile.
MAX_OFFERS_IN_HTML = 5

# PAGE_CSS is one plain string of CSS, written once here and reused by
# every page this file builds. Keeping it as a string (not a separate
# .css file) matches the "single combined page" idea - opening just
# this one HTML file is enough to see everything, no other file needed.
PAGE_CSS = """
body { font-family: Arial, Helvetica, sans-serif; margin: 24px; color: #222; }
h1 { font-size: 20px; }
h2 { font-size: 16px; margin-bottom: 4px; }
.search-info { color: #555; margin-bottom: 20px; }
.profile-grid { display: flex; flex-wrap: wrap; gap: 16px; }
.profile-card {
    border: 1px solid #ccc;
    border-radius: 6px;
    padding: 12px;
    width: 380px;
    box-sizing: border-box;
}
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th, td { border: 1px solid #ddd; padding: 4px 6px; text-align: left; font-size: 13px; }
.explanation { font-size: 13px; color: #333; }
.no-match { color: #a00; font-size: 13px; }
"""


def _offer_row_html(rank_number, offer, score, companies):
    """
    Builds one <tr> table row for one ranked offer, including which
    company actually offers it. html.escape(...) is used on every piece
    of text that came from the data files, not because our fictional
    data is actually dangerous, but because it is the correct habit any
    time text ends up inside an HTML page - it stops a stray "<" or "&"
    in a value from accidentally being read as part of the page's own
    markup instead of as plain text.

    companies is the dict returned by load_companies() - used to turn
    this offer's company_id (e.g. "C3") into a real company name (e.g.
    "CostaLink") for display, the same lookup main.py's own terminal
    output now does too.
    """
    offer_id_text = html.escape(offer.get_offer_id())
    company_name_text = html.escape(companies[offer.get_company_id()].get_name())
    # :.2f and :.1f format the price and score to a fixed number of
    # decimal places, the same formatting already used in main.py's own
    # terminal output, so the two views always show matching numbers.
    return (
        f"<tr><td>{rank_number}</td><td>{offer_id_text}</td>"
        f"<td>{company_name_text}</td>"
        f"<td>EUR {offer.get_price_eur():.2f}</td><td>{score:.1f}</td></tr>"
    )


def _profile_card_html(profile, surviving_offers, ranked_offers, scores, companies):
    """
    Builds one full <section> block for one profile: its name, how many
    offers matched, a small table of the top few (now including each
    one's company), and the plain-language explanation of the single
    best one. Returns a "no offers matched" message instead, if
    ranked_offers is empty.
    """
    display_name = html.escape(profile["display_name"])

    if not ranked_offers:
        return (
            f'<section class="profile-card"><h2>{display_name}</h2>'
            f'<p class="no-match">No offers matched this profile\'s own '
            f"constraints for this search.</p></section>"
        )

    # ranked_offers[:MAX_OFFERS_IN_HTML] takes only the first few offers
    # from the already-sorted list - the same slicing idea main.py uses
    # for its own terminal output.
    top_offers = ranked_offers[:MAX_OFFERS_IN_HTML]
    # enumerate(..., start=1) numbers the rows 1, 2, 3, ... for a human
    # reader, the same as main.py's terminal output does.
    table_rows = "".join(
        _offer_row_html(rank_number, offer, scores[offer.get_offer_id()], companies)
        for rank_number, offer in enumerate(top_offers, start=1)
    )

    explanation_text = html.escape(
        explain_top_offer(surviving_offers, profile, ranked_offers[0])
    )

    return (
        f'<section class="profile-card">'
        f"<h2>{display_name}</h2>"
        f"<p>{len(ranked_offers)} offer(s) matched.</p>"
        f"<table><tr><th>Rank</th><th>Offer ID</th><th>Company</th>"
        f"<th>Price</th><th>Score</th></tr>"
        f"{table_rows}</table>"
        f'<p class="explanation">{explanation_text}</p>'
        f"</section>"
    )


def render_results_to_html(
    destination_id, destination_name, date_from, date_to, profile_results, companies,
    output_path="output/results.html",
):
    """
    Builds the full combined HTML page and writes it to output_path.

    profile_results must be a list of dicts, one per profile, each
    shaped exactly like:
      {"profile": <profile dict from profiles.py>,
       "surviving_offers": <list from filters.py>,
       "ranked_offers": <list from scoring.py>,
       "scores": <dict from scoring.py>}
    This is exactly what main.py already builds for its own terminal
    output - nothing here is computed again from scratch. companies is
    the dict from load_companies(), used only to show each offer's
    company name.

    Returns the output_path it wrote to (as a string), so the caller
    can print or log where the file ended up.
    """
    destination_name_text = html.escape(destination_name)
    destination_id_text = html.escape(destination_id)

    # "".join(...) builds one <section> block per profile and glues
    # them all together into one string, in the same order
    # profile_results was given (the order the profiles were searched).
    profile_cards_html = "".join(
        _profile_card_html(
            result["profile"],
            result["surviving_offers"],
            result["ranked_offers"],
            result["scores"],
            companies,
        )
        for result in profile_results
    )

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>BusBidder Spain - {destination_name_text}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<h1>BusBidder Spain - ranked offers to {destination_name_text} ({destination_id_text})</h1>
<p class="search-info">Travel window: {html.escape(date_from)} to {html.escape(date_to)}</p>
<div class="profile-grid">
{profile_cards_html}
</div>
</body>
</html>
"""

    # Path(...).parent.mkdir(...) creates the "output" folder if it does
    # not already exist, the same pattern setup_logging() in loaders.py
    # uses for the "logs" folder.
    output_file_path = Path(output_path)
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    output_file_path.write_text(page_html, encoding="utf-8")

    return str(output_file_path)
