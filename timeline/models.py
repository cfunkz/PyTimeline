"""
models.py - A single event on a timeline.

    Python has special method names wrapped in double underscores.
    Python calls them when certain syntax is used:

        __init__   → called when you create an object:   Event(1, "x", 10)
        __lt__     → called when you use <:               event_a < event_b
        __eq__     → called when you use ==:              event_a == event_b
        __repr__   → called when you use print():         print(event_a)

    They let custom class work with Python's built-in features
    like sorting, comparing, and printing — just like strings and numbers do.
"""


class Event:
    """One recorded change: what key changed, to what value, and when."""

    # __init__: the constructor ────────────────────────────
    #
    # Called automatically when you create a new Event:
    #   e = Event(1, "name", "Alice")
    #
    # "self" is the new object being created.
    # The other parameters are what you pass in.

    def __init__(self, timestamp, key, value, deleted=False):
        self.timestamp = timestamp    # when it happened
        self.key = key                # which key changed
        self.value = value            # what the new value is
        self.deleted = deleted        # was the key deleted?

    # __lt__: less than (<) ────────────────────────────────
    #
    # Tells Python how to compare two Events with <
    #
    # WITHOUT this, Python would crash:
    #   Event(1, "x", 10) < Event(2, "x", 20)
    #   → TypeError: '<' not supported
    #
    # WITH this, Python knows to compare timestamps:
    #   Event(1, "x", 10) < Event(2, "x", 20)
    #   → True (because 1 < 2)
    #
    # WHY WE NEED IT:
    #   .sort() uses < to decide the order.
    #   We sort events by timestamp, so we need to tell Python
    #   "earlier timestamp = comes first".
    #
    # "self" is the left side of <, "other" is the right side.

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    # __eq__: equals (==) ──────────────────────────────────
    #
    # Tells Python how to compare two Events with ==
    #
    # WITHOUT this, Python compares memory addresses:
    #   Event(1, "x", 10) == Event(1, "x", 10)
    #   → False (different objects in memory, even if identical)
    #
    # WITH this, Python compares timestamps:
    #   Event(1, "x", 10) == Event(1, "x", 10)
    #   → True (same timestamp)
    #
    # isinstance() check: if someone accidentally compares an Event
    # to a string or number, return False instead of crashing.

    def __eq__(self, other):
        if not isinstance(other, Event):
            return False
        return self.timestamp == other.timestamp

    # __repr__: printable string ───────────────────────────
    #
    # WITHOUT this:
    #   print(Event(1, "name", "Alice"))
    #   → <models.Event object at 0x7f3b2c1a5e80>   (useless!)
    #
    # WITH this:
    #   print(Event(1, "name", "Alice"))
    #   → Event(t=1, name='Alice')                   (helpful!)

    def __repr__(self):
        status = "DELETED" if self.deleted else repr(self.value)
        return f"Event(t={self.timestamp}, {self.key}={status})"