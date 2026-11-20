# MEMO: This file is models.py.
# Its only job is to define the 3 data classes that match our 3 CSV
# files: Destination (destinations.csv), Company (companies.csv) and
# Offer (offers.csv). Each class only stores values and gives back
# (get_...) methods to read them - there is no decision-making logic in
# this file at all. Filtering and ranking logic belongs in filters.py
# and scoring.py instead, not here, so this file stays simple.
#
# Every attribute name starts with an underscore (e.g. self._name).
# That underscore is just a convention, not a real Python restriction -
# it is a signal to anyone reading the code that this value should be
# read through its get_ method, not changed directly from outside the
# class.
#
# This file contains no real personal data - it only describes the
# SHAPE that fictional course-project data will be stored in.


class Destination:
    """One row from destinations.csv - a city served from Madrid."""

    def __init__(self, destination_id, name, approx_distance_km):
        # destination_id is a string (e.g. "D01") because it is a short
        # code, not a number used in any maths.
        self._destination_id = destination_id
        # name is a string because it is only ever displayed as text
        # (e.g. "Barcelona"), never calculated with.
        self._name = name
        # approx_distance_km is an int because destinations.csv stores
        # this as a whole number of kilometres, with no decimal part.
        self._approx_distance_km = approx_distance_km

    def get_destination_id(self):
        return self._destination_id

    def get_name(self):
        return self._name

    def get_approx_distance_km(self):
        return self._approx_distance_km


class Company:
    """One row from companies.csv - one of the 5 fictional bus companies."""

    def __init__(self, company_id, name, profile_description):
        # company_id is a string (e.g. "C1") - a short code, not a number.
        self._company_id = company_id
        # name is a string, only ever shown as text (e.g. "SolRuta").
        self._name = name
        # profile_description is a string - a short sentence describing
        # the company's personality, only ever shown as text.
        self._profile_description = profile_description

    def get_company_id(self):
        return self._company_id

    def get_name(self):
        return self._name

    def get_profile_description(self):
        return self._profile_description


class Offer:
    """
    One row from offers.csv - one specific bus ticket a company is
    selling for one destination, on one date. This is the class that
    filters.py and scoring.py will actually read from the most.
    """

    def __init__(
        self,
        offer_id,
        company_id,
        destination_id,
        origin,
        travel_date,
        departure_time,
        arrival_time,
        arrival_day_offset,
        duration_minutes,
        price_eur,
        transfers,
        luggage_allowance_kg,
        changeable,
        refundable,
        seats_available,
        customer_rating,
        co2_estimate_kg,
        seat_type,
        scenic_route,
    ):
        # offer_id is a string (e.g. "OFR-2026-0001") - it follows a
        # strict pattern, but a pattern is still just text, not a number.
        self._offer_id = offer_id
        # company_id and destination_id are strings - short codes that
        # link this offer back to one row in companies.csv / destinations.csv.
        self._company_id = company_id
        self._destination_id = destination_id
        # origin is a string - always "Madrid" in this dataset, but kept
        # as a real field rather than hard-coded, in case that changes.
        self._origin = origin
        # travel_date is kept as a plain string in "YYYY-MM-DD" format,
        # not converted into a datetime object - that keeps date-range
        # checks in filters.py a simple text/string comparison instead
        # of needing extra datetime-handling code.
        self._travel_date = travel_date
        # departure_time and arrival_time are plain strings in "HH:MM"
        # format, for the same reason - simple text, no datetime needed.
        self._departure_time = departure_time
        self._arrival_time = arrival_time
        # arrival_day_offset is an int: 0 means the bus arrives the same
        # calendar day it leaves, 1 means it arrives the next day (a
        # genuine overnight trip). An int is enough since it is only
        # ever 0 or 1 in this dataset.
        self._arrival_day_offset = arrival_day_offset
        # duration_minutes is an int - offers.csv never uses a fraction
        # of a minute, so a whole number is all that is needed.
        self._duration_minutes = duration_minutes
        # price_eur is a float, not an int, because prices have cents
        # (e.g. 42.91).
        self._price_eur = price_eur
        # transfers is an int - you cannot have half a bus transfer.
        self._transfers = transfers
        # luggage_allowance_kg is an int - offers.csv only ever stores
        # a whole number of kilograms.
        self._luggage_allowance_kg = luggage_allowance_kg
        # changeable and refundable are bools (True/False) because they
        # are simple yes/no facts about the ticket.
        self._changeable = changeable
        self._refundable = refundable
        # seats_available is an int - you cannot sell half a seat.
        self._seats_available = seats_available
        # customer_rating is a float because ratings in this dataset are
        # decimals on a 1.0-5.0 scale (e.g. 4.1), not whole numbers.
        self._customer_rating = customer_rating
        # co2_estimate_kg is a float - an estimate like this will almost
        # always have a decimal part (e.g. 22.4).
        self._co2_estimate_kg = co2_estimate_kg
        # seat_type is a string - one of "window", "aisle" or "other",
        # a category, not a number.
        self._seat_type = seat_type
        # scenic_route is a bool (True/False) - another simple yes/no fact.
        self._scenic_route = scenic_route

    # One get_ method per attribute, in the same order as above, so this
    # class is simple to read top to bottom and simple to look something
    # up in - no @property, just plain methods, matching how models.py
    # was written in the earlier assignments for this course.

    def get_offer_id(self):
        return self._offer_id

    def get_company_id(self):
        return self._company_id

    def get_destination_id(self):
        return self._destination_id

    def get_origin(self):
        return self._origin

    def get_travel_date(self):
        return self._travel_date

    def get_departure_time(self):
        return self._departure_time

    def get_arrival_time(self):
        return self._arrival_time

    def get_arrival_day_offset(self):
        return self._arrival_day_offset

    def get_duration_minutes(self):
        return self._duration_minutes

    def get_price_eur(self):
        return self._price_eur

    def get_transfers(self):
        return self._transfers

    def get_luggage_allowance_kg(self):
        return self._luggage_allowance_kg

    def get_changeable(self):
        return self._changeable

    def get_refundable(self):
        return self._refundable

    def get_seats_available(self):
        return self._seats_available

    def get_customer_rating(self):
        return self._customer_rating

    def get_co2_estimate_kg(self):
        return self._co2_estimate_kg

    def get_seat_type(self):
        return self._seat_type

    def get_scenic_route(self):
        return self._scenic_route
