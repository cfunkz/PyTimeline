"""
engine.py - An in-memory timeline that tracks changes over time with branching.

    timeline = Timeline()
    timeline.set("name", "Alice", timestamp=1)
    timeline.set("name", "Bob",   timestamp=5)

    timeline.get("name", timestamp=3)   # "Alice"  (time travel)
    timeline.get("name", timestamp=7)   # "Bob"

    timeline.branch("alt", from_timestamp=3)
    timeline.set("name", "Charlie", timestamp=5, branch="alt")
    # "main" has Bob at t=5, "alt" has Charlie at t=5


WHAT IS bisect_right? (used in the get() method)

    bisect_right answers: "If I inserted this value into a sorted list,
    WHICH POSITION would it go into?"

    Example:
        values =    [1,  3,  5,  7]
        positions:   0   1   2   3

        position = bisect_right(values, 4)

        print(position)  → 2
        print(values)    → [1, 3, 5, 7]   ← unchanged! nothing inserted!

        The 2 means: "4 WOULD go at position 2 (between 3 and 5)":

        [1,  3,  4,  5,  7]    ← if we DID insert (but we don't)
         0   1   2   3   4
               ↑
         position 2 — bisect_right just tells us this number

    WHY WE USE IT:
        We want to find the most recent event AT or BEFORE a certain time.

        bisect_right tells us where our target time WOULD go.
        The item ONE STEP BACK (position - 1) is the answer.

        events:     [t=1: 100,  t=3: 120,  t=5: 95]
        positions:      0           1           2

        bisect_right(events, t=4)  → position 2
        position 2 - 1 = position 1  → t=3: 120 ✓ (most recent before 4)

    WHY NOT JUST LOOP?
        We could loop through every event and check, but bisect_right
        is much faster on large lists (it uses binary search because it cuts
        the list in half each step instead of checking one by one).


WHAT IS A "DUMMY" EVENT? (used in the get() method)

    bisect_right compares items using <  (which calls __lt__).
    Our events are compared by timestamp (see models.py).

    To search "what happened at time 4?", we need something with
    timestamp=4 to compare against. But we don't have a real event
    at time 4 — that's what we're trying to find!

    So we create a FAKE event (a "dummy") with just the timestamp
    we're looking for. The key and value don't matter as they're only
    there because Event.__init__ requires them.

        dummy = Event(timestamp=4, key="x", value=None)
        #                    ↑ this is all we care about
        #                              ↑ these don't matter

    bisect_right then compares this dummy against real events
    using their timestamps, and tells us where time 4 would fit
    in the sorted list.


WHAT IS copy.deepcopy? (used in the branch() method)

    When you copy a list in Python, you get a SHALLOW copy:
        original = [{"a": 1}]
        shallow = original.copy()
        shallow[0]["a"] = 999
        print(original)  → [{"a": 999}]  ← BOTH changed!

    That's because both lists point to the SAME dictionary in memory.

    deepcopy creates a completely independent clone:
        deep = copy.deepcopy(original)
        deep[0]["a"] = 999
        print(original)  → [{"a": 1}]  ← original is safe!

    We need deepcopy when branching so that changes in a sub-branch
    don't accidentally change events in the main-branch.
"""

from bisect import bisect_right, insort
import copy
import json
from .models import Event


class Timeline:

    # ── __init__: set up empty storage ───────────────────────
    #
    # Creates two things:
    #   self.branches      → where all the data lives
    #   self.branch_tree → remembers which branch came from which
    #
    # self.branches is a nested dictionary:
    #   {
    #       "main": {
    #           "price": [Event(t=1, 100), Event(t=3, 120)],
    #           "name":  [Event(t=2, "Alice")],
    #       },
    #       "alt": {
    #           "price": [Event(t=1, 100), Event(t=3, 999)],
    #       },
    #       "alt2": {
    #           "price": [Event(t=1, 100)],
    #       }
    #   }
    #
    # self.branch_tree tracks where each sub-branch came from:
    #   {
    #       "alt":  "main",     ← "alt" was branched from "main"
    #       "alt2": "alt",      ← "alt2" was branched from "alt"
    #   }
    #
    # Notice "main" is NOT in branch_tree — it has no parent,
    # it's the root. Only sub-branches appear here.

    def __init__(self):
        self.branches = {"main": {}}
        self.branch_tree = {}

    # ── set: record a change ─────────────────────────────────
    #
    # Example:
    #   timeline.set("price", 100, timestamp=1)
    #
    # What happens inside:
    #   1. Get (or create) the event list for "price"
    #   2. Append a new Event (never replaces — full changelog)
    #   3. Sort the list so events stay in time order
    #
    # If you set the same key at the same timestamp twice,
    # BOTH events are recorded. get() returns the latest one,
    # but history() shows every change ever made.
    #
    # .sort() uses Event.__lt__ to compare by timestamp.

    def set(self, key, value, timestamp, branch="main"):
        events = self._events_for(key, branch, create=True)
        insort(events, Event(timestamp, key, value))

    # ── delete: mark a key as removed at a point in time ─────
    #
    # Doesn't actually delete anything — it adds an Event with
    # deleted=True. This way the history is preserved.
    #
    # Example:
    #   timeline.set("price", 100, timestamp=1)
    #   timeline.delete("price", timestamp=5)
    #   timeline.get("price", timestamp=3)   → 100  (before delete)
    #   timeline.get("price", timestamp=6)   → None (after delete)

    def delete(self, key, timestamp, branch="main"):
        events = self._events_for(key, branch, create=True)
        # Prevent duplicate delete at the same timestamp.
        # We check ALL events at this timestamp (not just the very last one)
        # because insort may have placed earlier events after it.
        for e in reversed(events):
            if e.timestamp < timestamp:
                break
            if e.timestamp == timestamp and e.deleted:
                return
        insort(events, Event(timestamp, key, None, deleted=True))
        
    # ── get: look up a value at a specific time ──────────────
    #
    # This is the core "time travel" method.
    #
    # Example: events for "price" are [t=1: 100, t=3: 120, t=5: 95]
    #
    #   get("price", timestamp=4) should return 120
    #   because t=3 is the most recent event at or before t=4
    #
    # Step by step:
    #   1. Create a dummy Event with the timestamp we're searching for
    #   2. Use bisect_right to find where it would fit in the sorted list
    #   3. Go one step back (index - 1) to get the most recent event
    #   4. If that event is a deletion, return None
    #   5. If nothing found, check the main-branch (for sub-branches)
    #
    # Visual example:
    #
    #   events:      [t=1: 100]  [t=3: 120]  [t=5: 95]
    #   indexes:         0            1            2
    #
    #   dummy = Event(timestamp=4)
    #   bisect_right → 2  (dummy would go between index 1 and 2)
    #   2 - 1 = 1 → events[1] → t=3: 120 ✓

    def get(self, key, timestamp, branch="main"):
        events = self._events_for(key, branch, create=False)

        if events:
            # Create a fake event just for searching (see explanation above)
            dummy = Event(timestamp, key, value=None)

            # Find where the dummy would be inserted in the sorted list
            insert_position = bisect_right(events, dummy)

            # One step back = most recent event at or before our timestamp
            index = insert_position - 1

            if index >= 0:
                event = events[index]
                # If this event was a delete, the key didn't exist at this time
                return None if event.deleted else event.value

        # Not found in this branch.
        # If this is a sub-branch, check the main-branch it came from.
        # Example: "alt" was branched from "main", so check "main" next.
        main_branch = self.branch_tree.get(branch)
        if main_branch:
            return self.get(key, timestamp, main_branch)

        return None

    # ── branch: create a sub-branch (alternate timeline) ─────
    #
    # Copies all events up to a certain timestamp into a new branch.
    # Changes in the sub-branch don't affect the main-branch.
    #
    # Example:
    #   timeline.set("price", 100, timestamp=1)
    #   timeline.set("price", 120, timestamp=5)
    #
    #   timeline.branch("alt", from_timestamp=3)
    #   # "alt" now has: [t=1: 100]  (copied from main)
    #   # "alt" does NOT have t=5: 120 (happened after the branch point)
    #
    #   timeline.set("price", 999, timestamp=5, branch="alt")
    #   # main at t=5: 120
    #   # alt  at t=5: 999  (different timeline!)
    #
    # Uses deepcopy so the sub-branch gets its own independent
    # copies of the events (see explanation at top of file).

    def branch(self, new_name, from_timestamp, source="main"):
        if new_name in self.branches:
            raise ValueError(f"Branch '{new_name}' already exists.")
        if source not in self.branches:
            raise ValueError(f"Branch '{source}' does not exist.")

        # Remember: "new_name" is a sub-branch of "source"
        self.branch_tree[new_name] = source

        # Create empty storage for the new branch
        self.branches[new_name] = {}

        # Copy events from the source branch, but only up to from_timestamp
        for key, events in self.branches[source].items():
            copied = [copy.deepcopy(e) for e in events if e.timestamp <= from_timestamp]
            if copied:
                self.branches[new_name][key] = copied

    # ── history: see all changes for a key ───────────────────
    #
    # Returns a list of (timestamp, value) pairs.
    # Deleted entries show None as the value.
    #
    # Example:
    #   timeline.set("price", 100, timestamp=1)
    #   timeline.set("price", 120, timestamp=3)
    #   timeline.delete("price", timestamp=5)
    #
    #   timeline.history("price")
    #   → [(1, 100), (3, 120), (5, None)]

    def history(self, key, branch="main"):
        events = self._events_for(key, branch, create=False)
        # Only keep the LAST event per timestamp
        # If you set the same timestamp twice, only the latest shows
        latest = {}
        for e in events:
            latest[e.timestamp] = None if e.deleted else e.value
        return sorted(latest.items())

    # ── changelog: every single change ever made ─────────────
    #
    # Unlike history(), this shows ALL events including duplicates
    # at the same timestamp. This is the full audit log.
    #
    # Example:
    #   timeline.set("price", 100, timestamp=1)
    #   timeline.set("price", 999, timestamp=1)   ← changed mind
    #   timeline.set("price", 120, timestamp=3)
    #
    #   timeline.history("price")
    #   → [(1, 999), (3, 120)]                    ← clean, latest per timestamp
    #
    #   timeline.changelog("price")
    #   → [(1, 100), (1, 999), (3, 120)]          ← every change ever made

    def changelog(self, key, branch="main"):
        events = self._events_for(key, branch, create=False)
        return [(e.timestamp, None if e.deleted else e.value) for e in events]

    # ── keys: list all pages/posts that exist at a point in time ──
    #
    # Loops through every key in the branch and checks if it
    # has a non-deleted value at the given timestamp.
    #
    # Example:
    #   timeline.set("home", "Welcome", timestamp=1)
    #   timeline.set("about", "About us", timestamp=2)
    #   timeline.delete("about", timestamp=5)
    #
    #   timeline.keys(timestamp=3)   → ["home", "about"]
    #   timeline.keys(timestamp=6)   → ["home"]   (about was deleted)
    #
    # This is how you'd build a "list all blog posts" page.

    def keys(self, timestamp, branch="main"):
        if branch not in self.branches:
            raise ValueError(f"Branch '{branch}' does not exist.")

        result = []
        for key in self.branches[branch]:
            # Reuse get() — it already handles time-travel and deletions
            if self.get(key, timestamp, branch) is not None:
                result.append(key)
        return sorted(result)

    # ── diff: compare a key at two different timestamps ────────
    #
    # Returns a tuple (old_value, new_value) showing what changed.
    #
    # Example:
    #   timeline.set("home", "Welcome", timestamp=1)
    #   timeline.set("home", "Updated!", timestamp=5)
    #
    #   timeline.diff("home", t1=1, t2=5)
    #   → ("Welcome", "Updated!")
    #
    # If the key didn't exist at t1, old_value is None.
    # If the key was deleted at t2, new_value is None.
    #
    # You can also diff across branches:
    #   timeline.diff("home", t1=5, t2=5, branch1="main", branch2="draft")
    #   → ("Welcome", "Draft version")

    def diff(self, key, t1, t2, branch1="main", branch2=None):
        if branch2 is None:
            branch2 = branch1
        old = self.get(key, t1, branch1)
        new = self.get(key, t2, branch2)
        return (old, new)

    # ── merge: publish a draft back into the main branch ───────
    #
    # Takes the current state of the source branch and applies it
    # to the target branch at the given timestamp.
    #
    # This is a "squash merge" — all draft edits become one change
    # in the target branch. Simple and clean.
    #
    # Example:
    #   timeline.set("home", "Welcome", timestamp=1)
    #   timeline.branch("draft", from_timestamp=1)
    #   timeline.set("home", "Draft v1", timestamp=2, branch="draft")
    #   timeline.set("home", "Draft v2", timestamp=3, branch="draft")
    #
    #   timeline.merge("draft", into="main", timestamp=4)
    #   timeline.get("home", timestamp=4)   → "Draft v2"
    #
    # After merging, the draft branch still exists. You can delete it
    # or keep editing it — it's up to you.
    #
    # HOW IT WORKS:
    #   1. Look at every key in the source branch
    #   2. Get the latest value for each key (at merge time)
    #   3. Set that value in the target branch at the merge timestamp
    #   4. If a key was deleted in the source, delete it in target too

    def merge(self, source, into="main", timestamp=None):
        if source not in self.branches:
            raise ValueError(f"Branch '{source}' does not exist.")
        if into not in self.branches:
            raise ValueError(f"Branch '{into}' does not exist.")
        if source == into:
            raise ValueError("Cannot merge a branch into itself.")

        # Find the latest timestamp across all events in the source branch
        # so we know what "current state" means
        latest_ts = 0
        for key, events in self.branches[source].items():
            if events:
                latest_ts = max(latest_ts, events[-1].timestamp)

        # If no merge timestamp given, use the latest from source
        if timestamp is None:
            timestamp = latest_ts

        # For each key in the source branch, apply its current state to target
        for key in self.branches[source]:
            events = self._events_for(key, source, create=False)
            if not events:
                continue

            # Find the most recent event for this key
            # (events are sorted by timestamp, so walk backwards)
            last_event = events[-1]

            if last_event.deleted:
                self.delete(key, timestamp, into)
            else:
                self.set(key, last_event.value, timestamp, into)

    # ── _events_for: helper to get/create an event list ──────
    #
    # The underscore _ at the start is a Python convention meaning
    # "this is a private/internal method — not meant to be called
    # from outside the class."
    #
    # It does two things:
    #   1. Checks the branch exists (raises error if not)
    #   2. Returns the event list for a key, creating an empty
    #      list [] if that key hasn't been used yet

    def _events_for(self, key, branch, create=False):
        if branch not in self.branches:
            raise ValueError(f"Branch '{branch}' does not exist.")
        if create:
            if key not in self.branches[branch]:
                self.branches[branch][key] = []
        return self.branches[branch].get(key, [])

    # ── save: write timeline to a JSON file ──────────────────
    #
    # Saves everything (all branches, all events, the branch tree)
    # to a .json file so you can load it later.
    #
    # Example:
    #   timeline.save("my_data.json")
    #
    # The file looks like:
    #   {
    #     "branch_tree": {"alt": "main"},
    #     "branches": {
    #       "main": {
    #         "home": [
    #           {"timestamp": 1, "key": "home", "value": "Welcome", "deleted": false}
    #         ]
    #       }
    #     }
    #   }
    #
    # NOTE: Values must be JSON-compatible types
    # (strings, numbers, bools, None, lists, dicts).

    def save(self, filepath):
        data = {
            "branch_tree": self.branch_tree,
            "branches": {}
        }
        for branch_name, keys in self.branches.items():
            data["branches"][branch_name] = {}
            for key, events in keys.items():
                for e in events:
                    if not isinstance(e.value, (str, int, float, bool, list, dict, type(None))):
                        raise TypeError(
                            f"Cannot save to JSON: key '{e.key}' at timestamp {e.timestamp} "
                            f"in branch '{branch_name}' has value of type {type(e.value).__name__}. "
                            f"JSON only supports: str, int, float, bool, None, list, dict."
                        )
                data["branches"][branch_name][key] = [
                    {
                        "timestamp": e.timestamp,
                        "key": e.key,
                        "value": e.value,
                        "deleted": e.deleted
                    }
                    for e in events
                ]

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    # ── load: restore timeline from a JSON file ──────────────
    #
    # Loads a previously saved timeline. Replaces everything
    # currently in memory.
    #
    # Example:
    #   timeline.load("my_data.json")
    #
    # Can also be used as a class method to create a new timeline:
    #   timeline = Timeline.from_file("my_data.json")

    def load(self, filepath):
        with open(filepath, "r") as f:
            data = json.load(f)

        self.branch_tree = data["branch_tree"]
        self.branches = {}

        for branch_name, keys in data["branches"].items():
            self.branches[branch_name] = {}
            for key, events in keys.items():
                self.branches[branch_name][key] = [
                    Event(
                        timestamp=e["timestamp"],
                        key=e["key"],
                        value=e["value"],
                        deleted=e["deleted"]
                    )
                    for e in events
                ]

    @classmethod
    def from_file(cls, filepath):
        """Create a new Timeline loaded from a JSON file."""
        t = cls()
        t.load(filepath)
        return t