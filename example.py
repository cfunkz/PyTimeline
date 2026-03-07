"""
example.py - Quick demo of all Timeline features.

    python example.py
"""

from timeline import Timeline

t = Timeline()

# ── set and get ──────────────────────────────────────────────

t.set("price", 100, timestamp=1)
t.set("price", 120, timestamp=3)
t.set("price", 95,  timestamp=5)

print("Time travel:")
print(f"  t=0: {t.get('price', 0)}")  # None  (not set yet)
print(f"  t=1: {t.get('price', 1)}")  # 100
print(f"  t=2: {t.get('price', 2)}")  # 100   (unchanged)
print(f"  t=4: {t.get('price', 4)}")  # 120
print(f"  t=5: {t.get('price', 5)}")  # 95

# ── delete ───────────────────────────────────────────────────

t.delete("price", timestamp=7)

print("\nDelete:")
print(f"  t=6: {t.get('price', 6)}")  # 95   (before delete)
print(f"  t=8: {t.get('price', 8)}")  # None (after delete)

# ── history ──────────────────────────────────────────────────

print(f"\nHistory: {t.history('price')}")
# [(1, 100), (3, 120), (5, 95), (7, None)]

# ── branch ───────────────────────────────────────────────────

t.branch("alt", from_timestamp=3)
t.set("price", 200, timestamp=5, branch="alt")

print("\nBranch:")
print(f"  main at t=5: {t.get('price', 5)}")                    # 95
print(f"  alt  at t=5: {t.get('price', 5, branch='alt')}")      # 200
print(f"  alt  at t=2: {t.get('price', 2, branch='alt')}")      # 100 (inherited)