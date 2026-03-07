<p align="center">
  <h1 align="center">PyTimeline</h1>
  <p align="center">
    An in-memory timeline that tracks every change over time with branching.
    <br/>
    <code>set</code> · <code>get</code> · <code>delete</code> · <code>branch</code> · <code>history</code> · <code>changelog</code>
  </p>
</p>

<br/>

## Table of Contents

- [Install](#install)
- [How It Works](#how-it-works)
  - [Setting values](#-setting-values)
  - [Getting values](#-getting-values-time-travel)
  - [Deleting](#-deleting)
  - [History vs Changelog](#-history-vs-changelog)
  - [Branching](#-branching)
  - [The branch tree](#-the-branch-tree)
- [CLI](#-cli)
- [Tests](#-tests)
- [Project Structure](#-project-structure)

## Install

```bash
git clone https://github.com/cfunkz/PyTimeline.git
cd PyTimeline
```

## How It Works

Think of it like a wiki. A normal dictionary only keeps the latest edit:

```python
page = {}
page["home"] = "Welcome"
page["home"] = "Welcome! Updated."    # "Welcome" is gone forever
```

PyTimeline remembers **every** edit as a list of events. Nothing is ever overwritten or removed.

### 📝 Setting values

```python
from timeline import Timeline

wiki = Timeline()
wiki.set("home", "Welcome", timestamp=1)
wiki.set("home", "Welcome! Updated.", timestamp=2)
```

What is stored in memory:

```
 branches
 └── "main"
      └── "home"
           ├── Event(t=1, value="Welcome")             ← first edit
           └── Event(t=2, value="Welcome! Updated.")   ← second edit (first is NOT replaced)
```

> Both edits exist. Nothing was overwritten.

### 🔍 Getting values (time travel)

`get()` does **not** look for an exact timestamp match.
It finds the **most recent event AT or BEFORE** your timestamp.

```python
wiki.get("home", timestamp=0)    # None, page doesn't exist yet
wiki.get("home", timestamp=1)    # "Welcome" (created here)
wiki.get("home", timestamp=2)    # "Welcome! Updated." (edited here)
wiki.get("home", timestamp=99)   # "Welcome! Updated." (no newer edit)
```

**How does it find the right version?**

```
Event list:  [t=1: "Welcome"]   [t=2: "Welcome! Updated."]
              ──────┬──────     ──────────┬──────────
                    │                     │
get(t=1):    ◄─────┘                     │        ← t=1 is most recent at t=1
get(t=2):              ◄─────────────────┘        ← t=2 is most recent at t=2
get(t=0):    nothing before t=0                   ← returns None
```

### 🗑️ Deleting

`delete()` does **not** remove events. It **adds** a new event that says `deleted=True`. 
This is like marking a wiki page as removed, while old versions are still readable.

```python
wiki.set("about", "About this wiki", timestamp=1)
wiki.delete("about", timestamp=3)
```

Memory now has **two** events, nothing was removed:

```
 "about"
  ├── Event(t=1, value="About this wiki")    ← still here
  └── Event(t=3, deleted=True)               ← NEW, marks page as removed
```

Now `get()` checks the `deleted` flag:

```python
wiki.get("about", timestamp=2)    # "About this wiki" (before delete)
wiki.get("about", timestamp=3)    # None (page removed)
wiki.get("about", timestamp=1)    # "About this wiki" (old version still readable!)
```

You can recreate a deleted page. It just adds another event:

```python
wiki.set("about", "About page is back", timestamp=5)
```

```
 "about"
  ├── Event(t=1, value="About this wiki")
  ├── Event(t=3, deleted=True)
  └── Event(t=5, value="About page is back")    ← page is back
```

### 📋 History vs Changelog

Two ways to see past edits:

```python
wiki = Timeline()
wiki.set("home", "Draft 1", timestamp=1)
wiki.set("home", "Draft 2", timestamp=1)    # quick correction at same timestamp
wiki.set("home", "Final",   timestamp=2)
```

```python
wiki.history("home")      # [(1, 'Draft 2'), (2, 'Final')]
wiki.changelog("home")    # [(1, 'Draft 1'), (1, 'Draft 2'), (2, 'Final')]
```

- **`history()`** shows the latest value per timestamp. Clean version list.
- **`changelog()`** shows every single edit, including corrections. Full audit log.

### 🌿 Branching (drafts)

Branching is like creating a draft of your wiki. You can edit the draft
without affecting the published pages.

```python
wiki = Timeline()
wiki.set("home", "Welcome", timestamp=1)
wiki.set("home", "Welcome! Updated.", timestamp=2)
```

Create a draft branch at timestamp 2:

```python
wiki.branch("draft", from_timestamp=2)
```

Events where `timestamp ≤ 2` are copied. The draft is independent:

```
 branches
 ├── "main"
 │    └── "home": [t=1: "Welcome",  t=2: "Welcome! Updated."]   ← unchanged
 │
 └── "draft"
      └── "home": [t=1: "Welcome",  t=2: "Welcome! Updated."]   ← copied
```

Edit the draft without touching main:

```python
wiki.set("home", "Redesigned homepage!", timestamp=3, branch="draft")
```

```
 branches
 ├── "main"
 │    └── "home": [t=1: "Welcome",  t=2: "Welcome! Updated."]
 │
 └── "draft"
      └── "home": [t=1: "Welcome",  t=2: "Welcome! Updated.",  t=3: "Redesigned!"]
```

Published page vs draft:

```python
wiki.get("home", timestamp=3)                    # "Welcome! Updated." (main, unchanged)
wiki.get("home", timestamp=3, branch="draft")    # "Redesigned homepage!"
```

### 🌳 The branch tree

You can create **multiple drafts**, and **branch from any branch**.

**Two drafts from main:**

```python
wiki.branch("draft-A", from_timestamp=2)
wiki.branch("draft-B", from_timestamp=2)

wiki.set("home", "Version A", timestamp=3, branch="draft-A")
wiki.set("home", "Version B", timestamp=3, branch="draft-B")
```

```
 branch_tree
 │
 main ─────────────────────────
 ├── draft-A    (Version A)
 └── draft-B    (Version B)
```

```python
wiki.get("home", timestamp=3)                       # "Welcome! Updated." (main)
wiki.get("home", timestamp=3, branch="draft-A")     # "Version A"
wiki.get("home", timestamp=3, branch="draft-B")     # "Version B"
```

**Sub-draft (branching from a draft):**

```python
wiki.branch("draft-A2", from_timestamp=3, source="draft-A")
wiki.set("home", "Version A2", timestamp=4, branch="draft-A2")
```

```
 branch_tree
 │
 main ─────────────────────
 ├── draft-A ──────────
 │    └── draft-A2          ← branched from draft-A, NOT main
 └── draft-B
```

```python
branch_tree = {
    "draft-A":  "main",       # draft-A came from main
    "draft-B":  "main",       # draft-B came from main
    "draft-A2": "draft-A",    # draft-A2 came from draft-A
}
```

> `"main"` is never in `branch_tree`. It's the root.
> Only sub-branches appear here.

### 💻 CLI

```
$ python cli.py
```

```
> set home "Welcome" 1
  [main] home = 'Welcome' at t=1

> set home "Updated" 2
  [main] home = 'Updated' at t=2

> get home 1
  [main] home at t=1 = 'Welcome'

> branch draft 2
  created 'draft' from 'main' at t=2

> set home "Redesigned" 3 draft
  [draft] home = 'Redesigned' at t=3

> get home 3 draft
  [draft] home at t=3 = 'Redesigned'

> branches
  main (main-branch, from: -)
  draft (sub-branch, from: main)

> history home
  t=1: 'Welcome'
  t=2: 'Updated'

> changelog home
  t=1: 'Welcome'
  t=2: 'Updated'

> exit
```

### 🧪 Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

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
├── wiki.py                # wiki example app
├── example.py             # quick feature demo
└── README.md
```