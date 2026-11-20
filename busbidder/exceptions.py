# MEMO: This file is exceptions.py.
# Its only job is to define 2 custom exception types that loaders.py
# (built next) will raise when a row from offers.csv has something wrong
# with it. Having our own named exceptions, instead of just using plain
# ValueError everywhere, means the code that catches them later can tell
# exactly what kind of problem happened just from the exception's name.
# No real personal data is involved in this file at all - it only
# describes error shapes, not any actual data.


# Both exceptions below inherit from ValueError, not from the plain
# Exception class. This matches a convention already used in Python
# itself: ValueError means "the type was right, but the value inside it
# was wrong" (e.g. a price of -15.0 is still a float, just an impossible
# one) - which is exactly the kind of problem these two classes are for.
class InvalidIdentifierError(ValueError):
    """
    Raised when a text field that is supposed to follow a strict pattern
    (such as an offer_id like 'OFR-2026-0001') does not match that
    pattern. Used for regex checks in loaders.py.
    """

    # __init__ runs automatically whenever this exception is created,
    # e.g. raise InvalidIdentifierError("offer_id", "OFFER_ABC", pattern).
    def __init__(self, field_name, value, pattern):
        # field_name is a string - the name of the column that failed,
        # e.g. "offer_id". Stored as a string because it is only ever
        # used for printing/logging, never for any calculation.
        self.field_name = field_name
        # value is kept in whatever type it was given (usually a string
        # here, since identifiers are text) - not converted to anything
        # else, so the log can show exactly what was actually read.
        self.value = value
        # pattern is a string - the regular expression text itself, so
        # the error message can show the reader what was expected.
        self.pattern = pattern
        # super().__init__(...) hands the final message text up to the
        # built-in ValueError class, so that print(error) or str(error)
        # shows this exact sentence automatically.
        super().__init__(
            f"'{field_name}' = {value!r} does not match the required pattern {pattern}"
        )


# This second exception covers every other kind of bad value that is not
# about matching a text pattern - a negative price, a rating above 5.0,
# a destination_id that does not exist in destinations.csv, and so on.
class InvalidRecordError(ValueError):
    """
    Raised when a field's value is the wrong type of wrong - present,
    correctly formatted, but not actually valid (e.g. price_eur = -15.0,
    or customer_rating = 6.5 on a 1.0-5.0 scale).
    """

    def __init__(self, field_name, reason):
        # field_name is a string, same reasoning as above.
        self.field_name = field_name
        # reason is a string - a short, human-readable explanation of
        # exactly why the value was rejected, written by whichever check
        # in loaders.py raised this exception.
        self.reason = reason
        super().__init__(f"'{field_name}': {reason}")
