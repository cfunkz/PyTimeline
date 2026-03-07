"""
pytest_test.py - Tests for Timeline.

    pip install pytest
    pytest pytest_test.py -v
"""

import pytest
from timeline import Timeline, Event


# ── Event model ──────────────────────────────────────────────

class TestEvent:
    def test_sorting(self):
        events = [Event(5, "k", "b"), Event(1, "k", "a"), Event(3, "k", "c")]
        events.sort()
        assert [e.timestamp for e in events] == [1, 3, 5]

    def test_equality(self):
        a = Event(1, "k", "x")
        b = Event(1, "k", "y")
        assert a == b  # same timestamp = equal

    def test_inequality(self):
        a = Event(1, "k", "x")
        b = Event(2, "k", "x")
        assert a < b
        assert not b < a

    def test_eq_wrong_type(self):
        assert Event(1, "k", "x") != "not an event"

    def test_repr(self):
        e = Event(1, "k", "hello")
        assert "t=1" in repr(e)
        assert "hello" in repr(e)

    def test_repr_deleted(self):
        e = Event(1, "k", None, deleted=True)
        assert "DELETED" in repr(e)


# ── Set and Get ──────────────────────────────────────────────

class TestSetGet:
    def test_basic(self):
        t = Timeline()
        t.set("x", 10, timestamp=1)
        assert t.get("x", 1) == 10

    def test_before_set(self):
        t = Timeline()
        t.set("x", 10, timestamp=5)
        assert t.get("x", 3) is None

    def test_after_set(self):
        t = Timeline()
        t.set("x", 10, timestamp=5)
        assert t.get("x", 99) == 10

    def test_overwrite(self):
        t = Timeline()
        t.set("x", "a", timestamp=1)
        t.set("x", "b", timestamp=3)
        assert t.get("x", 2) == "a"
        assert t.get("x", 4) == "b"

    def test_multiple_keys(self):
        t = Timeline()
        t.set("a", 1, timestamp=1)
        t.set("b", 2, timestamp=1)
        assert t.get("a", 1) == 1
        assert t.get("b", 1) == 2

    def test_nonexistent_key(self):
        t = Timeline()
        assert t.get("nope", 1) is None

    def test_insert_out_of_order(self):
        t = Timeline()
        t.set("x", "late", timestamp=10)
        t.set("x", "early", timestamp=1)
        assert t.get("x", 5) == "early"
        assert t.get("x", 10) == "late"

    def test_any_value_type(self):
        t = Timeline()
        t.set("list", [1, 2, 3], timestamp=1)
        t.set("dict", {"a": 1}, timestamp=2)
        t.set("float", 3.14, timestamp=3)
        assert t.get("list", 1) == [1, 2, 3]
        assert t.get("dict", 2) == {"a": 1}
        assert t.get("float", 3) == 3.14


# ── Delete ───────────────────────────────────────────────────

class TestDelete:
    def test_basic_delete(self):
        t = Timeline()
        t.set("x", 10, timestamp=1)
        t.delete("x", timestamp=5)
        assert t.get("x", 3) == 10
        assert t.get("x", 5) is None
        assert t.get("x", 99) is None

    def test_set_after_delete(self):
        t = Timeline()
        t.set("x", "a", timestamp=1)
        t.delete("x", timestamp=3)
        t.set("x", "b", timestamp=5)
        assert t.get("x", 2) == "a"
        assert t.get("x", 4) is None
        assert t.get("x", 6) == "b"

    def test_delete_nonexistent(self):
        t = Timeline()
        t.delete("x", timestamp=1)
        assert t.get("x", 1) is None


# ── History ──────────────────────────────────────────────────

class TestHistory:
    def test_full_history(self):
        t = Timeline()
        t.set("x", 1, timestamp=1)
        t.set("x", 2, timestamp=3)
        t.delete("x", timestamp=5)
        assert t.history("x") == [(1, 1), (3, 2), (5, None)]

    def test_empty_history(self):
        t = Timeline()
        assert t.history("x") == []

    def test_single_entry(self):
        t = Timeline()
        t.set("x", "only", timestamp=1)
        assert t.history("x") == [(1, "only")]


# ── Branching ────────────────────────────────────────────────

class TestBranch:
    def test_branch_inherits(self):
        t = Timeline()
        t.set("x", 10, timestamp=1)
        t.set("x", 20, timestamp=5)
        t.branch("alt", from_timestamp=3)
        # alt should have x=10 (from t=1) but NOT x=20 (from t=5)
        assert t.get("x", 2, branch="alt") == 10
        assert t.get("x", 6, branch="alt") == 10  # still 10, no t=5 event

    def test_branch_diverges(self):
        t = Timeline()
        t.set("x", "a", timestamp=1)
        t.branch("alt", from_timestamp=1)
        t.set("x", "main_b", timestamp=3, branch="main")
        t.set("x", "alt_b", timestamp=3, branch="alt")
        assert t.get("x", 3) == "main_b"
        assert t.get("x", 3, branch="alt") == "alt_b"

    def test_branch_does_not_affect_source(self):
        t = Timeline()
        t.set("x", 1, timestamp=1)
        t.branch("alt", from_timestamp=1)
        t.set("x", 999, timestamp=2, branch="alt")
        assert t.get("x", 2) is None or t.get("x", 2) == 1  # main unaffected

    def test_branch_from_branch(self):
        t = Timeline()
        t.set("x", "root", timestamp=1)
        t.branch("b1", from_timestamp=1)
        t.set("x", "b1_val", timestamp=2, branch="b1")
        t.branch("b2", from_timestamp=2, source="b1")
        assert t.get("x", 2, branch="b2") == "b1_val"

    def test_duplicate_branch_raises(self):
        t = Timeline()
        t.branch("alt", from_timestamp=0)
        with pytest.raises(ValueError):
            t.branch("alt", from_timestamp=0)

    def test_main_branch_lookup(self):
        """If a key doesn't exist in the sub-branch, it checks the main-branch."""
        t = Timeline()
        t.set("x", "from_main", timestamp=1)
        t.branch("alt", from_timestamp=0)  # branch before x was set
        # alt has no events, but parent (main) has x at t=1
        assert t.get("x", 1, branch="alt") == "from_main"

    def test_branch_history_is_independent(self):
        t = Timeline()
        t.set("x", 1, timestamp=1)
        t.set("x", 2, timestamp=3)
        t.branch("alt", from_timestamp=2)
        t.set("x", 99, timestamp=4, branch="alt")
        assert t.history("x") == [(1, 1), (3, 2)]
        assert t.history("x", branch="alt") == [(1, 1), (4, 99)]


# ── Edge cases ───────────────────────────────────────────────

class TestEdgeCases:
    def test_timestamp_zero(self):
        t = Timeline()
        t.set("x", "zero", timestamp=0)
        assert t.get("x", 0) == "zero"

    def test_same_timestamp_keeps_all(self):
        t = Timeline()
        t.set("x", "first", timestamp=1)
        t.set("x", "second", timestamp=1)
        # Full changelog: both events are kept in the list
        # get() returns the latest one, history() shows both
        assert t.get("x", 1) == "second"
        assert len(t.history("x")) == 2  # both recorded
        assert t.history("x") == [(1, "first"), (1, "second")]

    def test_bad_branch_name(self):
        t = Timeline()
        with pytest.raises(ValueError):
            t.get("x", 1, branch="nonexistent")

    def test_large_timeline(self):
        t = Timeline()
        for i in range(1000):
            t.set("counter", i, timestamp=i)
        assert t.get("counter", 0) == 0
        assert t.get("counter", 500) == 500
        assert t.get("counter", 999) == 999