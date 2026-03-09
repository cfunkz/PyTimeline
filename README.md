<p align="center">
  <h1 align="center">PyTimeline</h1>
  <p align="center">
    Git-like version control for blogs, wikis, and web apps.
    <br/>
    <code>set</code> · <code>get</code> · <code>delete</code> · <code>keys</code> · <code>diff</code> · <code>branch</code> · <code>merge</code> · <code>history</code> · <code>changelog</code> · <code>save</code> · <code>load</code>
  </p>
</p>

<br/>

## Table of Contents

- [Install](#install)
- [How It Works](#how-it-works)
  - [Setting values](#-setting-values)
  - [Getting values](#-getting-values-time-travel)
  - [Deleting](#-deleting)
  - [Listing keys](#-listing-keys)
  - [Comparing versions](#-comparing-versions-diff)
  - [History vs Changelog](#-history-vs-changelog)
  - [Branching](#-branching-drafts)
  - [Merging](#-merging-publishing-drafts)
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

Think of it like a blog. A normal dictionary only keeps the latest edit:

```python
page = {}
page["home"] = "Welcome"
page["home"] = "Welcome! Updated."    # "Welcome" is gone forever
```

PyTimeline remembers **every** edit as a list of events. Nothing is ever overwritten or removed.

### 📝 Setting values

```python
from timeline import Timeline

blog = Timeline()
blog.set("home", "Welcome", timestamp=1)
blog.set("home", "Welcome! Updated.", timestamp=2)
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
blog.get("home", timestamp=0)    # None, page doesn't exist yet
blog.get("home", timestamp=1)    # "Welcome" (created here)
blog.get("home", timestamp=2)    # "Welcome! Updated." (edited here)
blog.get("home", timestamp=99)   # "Welcome! Updated." (no newer edit)
```

### 🗑️ Deleting

`delete()` does **not** remove events. It **adds** a new event that says `deleted=True`.
Old versions are still readable.

```python
blog.set("about", "About this blog", timestamp=1)
blog.delete("about", timestamp=3)

blog.get("about", timestamp=2)    # "About this blog" (before delete)
blog.get("about", timestamp=3)    # None (deleted)
blog.get("about", timestamp=1)    # "About this blog" (old version still works!)
```

You can bring a page back by setting it again:

```python
blog.set("about", "About page is back", timestamp=5)
```

### 📋 Listing keys

`keys()` lists all pages that exist (not deleted) at a given timestamp.

```python
blog.set("home", "Welcome", timestamp=1)
blog.set("about", "About us", timestamp=2)
blog.delete("about", timestamp=5)

blog.keys(timestamp=3)    # ["about", "home"]
blog.keys(timestamp=6)    # ["home"]   (about was deleted)
```

### 🔀 Comparing versions (diff)

`diff()` compares a key at two timestamps. Returns `(old_value, new_value)`.

```python
blog.set("home", "Welcome", timestamp=1)
blog.set("home", "Redesigned!", timestamp=5)

blog.diff("home", t1=1, t2=5)
# ("Welcome", "Redesigned!")
```

You can also diff across branches:

```python
blog.diff("home", t1=5, t2=5, branch1="main", branch2="draft")
# ("Welcome", "Draft version")
```

### 📋 History vs Changelog

Two ways to see past edits:

```python
blog = Timeline()
blog.set("home", "Draft 1", timestamp=1)
blog.set("home", "Draft 2", timestamp=1)    # quick correction at same timestamp
blog.set("home", "Final",   timestamp=2)
```

```python
blog.history("home")      # [(1, 'Draft 2'), (2, 'Final')]
blog.changelog("home")    # [(1, 'Draft 1'), (1, 'Draft 2'), (2, 'Final')]
```

- **`history()`** shows the latest value per timestamp. Clean version list.
- **`changelog()`** shows every single edit, including corrections. Full audit log.

### 🌿 Branching (drafts)

Branching is like creating a draft. You can edit the draft
without affecting the published pages.

```python
blog = Timeline()
blog.set("home", "Welcome", timestamp=1)
blog.set("home", "Welcome! Updated.", timestamp=2)

blog.branch("draft", from_timestamp=2)
blog.set("home", "Redesigned homepage!", timestamp=3, branch="draft")

blog.get("home", timestamp=3)                    # "Welcome! Updated." (main, unchanged)
blog.get("home", timestamp=3, branch="draft")    # "Redesigned homepage!"
```

### 🚀 Merging (publishing drafts)

When a draft is ready, merge it back into main. This is how you "publish".

```python
blog.merge("draft", into="main", timestamp=4)

blog.get("home", timestamp=4)    # "Redesigned homepage!" (published!)
blog.get("home", timestamp=2)    # "Welcome! Updated." (old version still works)
```

Merge takes the current state of the source branch and applies it to the target.
The draft branch still exists after merging — you can keep editing it or ignore it.

### 🌳 The branch tree

You can create **multiple drafts**, and **branch from any branch**.

**Two drafts from main:**

```python
blog.branch("draft-A", from_timestamp=2)
blog.branch("draft-B", from_timestamp=2)

blog.set("home", "Version A", timestamp=3, branch="draft-A")
blog.set("home", "Version B", timestamp=3, branch="draft-B")
```

```
 branch_tree
 │
 main ─────────────────────────
 ├── draft-A    (Version A)
 └── draft-B    (Version B)
```

**Sub-draft (branching from a draft):**

```python
blog.branch("draft-A2", from_timestamp=3, source="draft-A")
blog.set("home", "Version A2", timestamp=4, branch="draft-A2")
```

```
 branch_tree
 │
 main ─────────────────────
 ├── draft-A ──────────
 │    └── draft-A2          ← branched from draft-A, NOT main
 └── draft-B
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

> keys 2
  home

> branch draft 2
  created 'draft' from 'main' at t=2

> set home "Redesigned" 3 draft
  [draft] home = 'Redesigned' at t=3

> diff home 2 3 draft
  t=2: 'Updated'
  t=3: 'Redesigned'

> merge draft
  merged 'draft' into 'main'

> branches
  main (main-branch, from: -)
  draft (sub-branch, from: main)

> history home
  t=1: 'Welcome'
  t=2: 'Updated'

> save blog.json
  saved to blog.json

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
│   └── engine.py          # Timeline class
│
├── tests/
│   └── pytest_test.py     # tests
│
├── cli.py                 # interactive CLI
├── example.py             # blog example app
└── README.md
```
