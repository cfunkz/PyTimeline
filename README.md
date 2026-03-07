<p align="center">
  <h1 align="center">PyTimeline</h1>
  <p align="center">
    An in-memory timeline that tracks every change over time with branching.
    <br/>
    <code>set</code> · <code>get</code> · <code>delete</code> · <code>branch</code> · <code>history</code>
  </p>
</p>

<br/>

## Table of Contents

- [Install](#install)
- [How It Works](#how-it-works)
  - [Setting values](#-setting-values)
  - [Getting values](#-getting-values-time-travel)
  - [Deleting](#-deleting)
  - [Branching](#-branching)
  - [The branch tree](#-the-branch-tree)
- [CLI](#-cli)
- [Tests](#-tests)
- [Project Structure](#-project-structure)

---

## Install

```bash
git clone https://github.com/cfunkz/PyTimeline.git
cd PyTimeline
```

---

## How It Works

A normal dictionary forgets old values:

```python
data = {}
data["price"] = 100
data["price"] = 120    # 100 is gone forever
```

PyTimeline remembers **every** change as a list of events. Nothing is ever overwritten or removed.

---

### 📝 Setting values

```python
from timeline import Timeline

t = Timeline()
t.set("price", 100, timestamp=1)
t.set("price", 120, timestamp=3)
```

What is stored in memory after these two lines:

```
 branches
 └── "main"
      └── "price"
           ├── Event(t=1, value=100)     ← first set
           └── Event(t=3, value=120)     ← second set (first is NOT replaced)
```

> Both events exist. Nothing was overwritten.

---

### 🔍 Getting values (time travel)

`get()` does **not** look for an exact timestamp match.
It finds the **most recent event AT or BEFORE** your timestamp.

```python
t.get("price", timestamp=0)    # None, nothing exists yet
t.get("price", timestamp=1)    # 100  (set here)
t.get("price", timestamp=2)    # 100  (no t=2 event, so t=1 is closest
t.get("price", timestamp=3)    # 120  (set here)
t.get("price", timestamp=99)   # 120  (still t=3, nothing newer
```

**How does it find the right event?**

```
Event list:  [t=1: 100]   [t=3: 120]
              ────┬────    ────┬────
                  │            │
get(t=2):    ◄───┘            │        ← t=1 is most recent before t=2
get(t=4):         ◄───────────┘        ← t=3 is most recent before t=4
get(t=0):    nothing before t=0        ← returns None
```

---

### 🗑️ Deleting

`delete()` does **not** remove events. It **adds** a new event that says `deleted=True`.

```python
t.delete("price", timestamp=5)
```

Memory now has **three** events, nothing was removed:

```
 "price"
  ├── Event(t=1, value=100)         ← still here
  ├── Event(t=3, value=120)         ← still here
  └── Event(t=5, deleted=True)      ← NEW, marks deletion
```

Now `get()` checks the `deleted` flag:

```python
t.get("price", timestamp=4)    # 120   ← t=3 is closest, NOT deleted
t.get("price", timestamp=5)    # None  ← t=5 found, but marked deleted
t.get("price", timestamp=99)   # None  ← t=5 still most recent, still deleted
```

You can set a value again after deleting. It just adds another event:

```python
t.set("price", 200, timestamp=8)
```

```
 "price"
  ├── Event(t=1, value=100)
  ├── Event(t=3, value=120)
  ├── Event(t=5, deleted=True)
  └── Event(t=8, value=200)      ← price is back
```

Full audit log with `history()`:

```python
t.history("price")
# [(1, 100), (3, 120), (5, None), (8, 200)]
```

---

### 🌿 Branching

Branching copies events up to a timestamp into a new independent branch.

```python
t = Timeline()
t.set("price", 100, timestamp=1)
t.set("price", 120, timestamp=3)
t.set("price", 95,  timestamp=5)
```

Branch at timestamp 3:

```python
t.branch("alt", from_timestamp=3)
```

Events where `timestamp ≤ 3` are copied. Everything after is **not**:

```
 branches
 ├── "main"
 │    └── "price": [t=1: 100,  t=3: 120,  t=5: 95]     ← unchanged
 │
 └── "alt"
      └── "price": [t=1: 100,  t=3: 120]                ← copied up to t=3
```

Now set a different value in `"alt"`:

```python
t.set("price", 999, timestamp=5, branch="alt")
```

```
 branches
 ├── "main"
 │    └── "price": [t=1: 100,  t=3: 120,  t=5: 95 ]
 │
 └── "alt"
      └── "price": [t=1: 100,  t=3: 120,  t=5: 999]    ← different!
```

Same key, same timestamp, different values in each branch:

```python
t.get("price", timestamp=5)                    # main → 95
t.get("price", timestamp=5, branch="alt")      # alt  → 999
```

---

### 🌳 The branch tree

You can create **multiple branches from the same source**, and **branch from any branch**.

**Two sub-branches from main:**

```python
t.branch("alt", from_timestamp=3)
t.branch("alt2", from_timestamp=1)
```

```
 branch_tree
 │
 main ─────────────────────────────────
 ├── alt    (copied events up to t=3)
 └── alt2   (copied events up to t=1)
```

```
 branches
 ├── "main":  "price": [t=1: 100,  t=3: 120,  t=5: 95]     ← unchanged
 ├── "alt":   "price": [t=1: 100,  t=3: 120]                ← up to t=3
 └── "alt2":  "price": [t=1: 100]                            ← up to t=1
```

Each branch goes its own way:

```python
t.set("price", 999, timestamp=5, branch="alt")
t.set("price", 444, timestamp=2, branch="alt2")

t.get("price", timestamp=5)                     # main → 95
t.get("price", timestamp=5, branch="alt")       # alt  → 999
t.get("price", timestamp=5, branch="alt2")      # alt2 → 444  (no t=5, uses t=2)
```

**Branching from a sub-branch:**

```python
t.branch("alt3", from_timestamp=3, source="alt")
```

```
 branch_tree
 │
 main ─────────────────────
 ├── alt ──────────────
 │    └── alt3              ← branched from alt, NOT main
 └── alt2
```

```python
branch_tree = {
    "alt":  "main",     # alt came from main
    "alt2": "main",     # alt2 came from main
    "alt3": "alt",      # alt3 came from alt
}
```

> `"main"` is never in `branch_tree`. It's the root.
> Only sub-branches appear here.

---

### 💻 CLI

```
$ python cli.py
```

```
> set price 100 1
  [main] price = '100' at t=1

> set price 120 3
  [main] price = '120' at t=3

> get price 2
  [main] price at t=2 = '100'

> branch alt 2
  created 'alt' from 'main' at t=2

> set price 999 3 alt
  [alt] price = '999' at t=3

> get price 3 alt
  [alt] price at t=3 = '999'

> branches
  main (main-branch, from: -)
  alt (sub-branch, from: main)

> history price
  t=1: '100'
  t=3: '120'

> exit
```

---

### 🧪 Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

### 📁 Project Structure

```
PyTimeline/
│
├── timeline/
│   ├── __init__.py
│   ├── models.py          # Event class
│   └── timeline.py        # Timeline class
│
├── tests/
│   └── pytest_test.py     # tests
│
├── cli.py                 # interactive CLI
├── example.py             # quick demo
└── README.md
```

---

<p align="center">MIT License</p>