"""
example.py - A tiny wiki with version history and drafts.

Every edit is saved. You can view any old version,
see who changed what, and create drafts without
affecting the published page.

Uses every Timeline feature:
    set       → edit a page
    get       → read a page (at any version)
    delete    → remove a page
    history   → see version list
    changelog → see every edit including reverted ones
    branch    → create a draft
    sub-branch → fork a draft

    python example.py
"""

from timeline import Timeline

wiki = Timeline()
version = {"main": 0}


def edit(page, content, branch="main"):
    """Edit a page. Each edit increments the version."""
    v = version.get(branch, 0)
    v += 1
    version[branch] = v
    wiki.set(page, content, timestamp=v, branch=branch)
    print(f"  [{branch} v{v}] Saved '{page}'")


def read(page, v=None, branch="main"):
    """Read a page. Optionally at a specific version."""
    if v is None:
        v = version.get(branch, 0)
    result = wiki.get(page, v, branch=branch)
    if result is None:
        print(f"  [{branch} v{v}] '{page}' does not exist")
    else:
        print(f"  [{branch} v{v}] {page}: {result}")


def remove(page, branch="main"):
    """Remove a page."""
    v = version.get(branch, 0)
    v += 1
    version[branch] = v
    wiki.delete(page, timestamp=v, keep_value=True, branch=branch)
    print(f"  [{branch} v{v}] Removed '{page}'")


def draft(name, source="main"):
    """Create a draft branch from the current version."""
    v = version.get(source, 0)
    wiki.branch(name, from_timestamp=v, source=source)
    version[name] = v
    print(f"  Created draft '{name}' from '{source}' at v{v}")


# ─────────────────────────────────────────────────────────────

print("=== Editing pages ===\n")

edit("home", "Welcome to the wiki")
edit("about", "This wiki is built with PyTimeline")
edit("home", "Welcome to the wiki! Updated.")
read("home")

print("\n=== Reading old versions ===\n")

read("home", v=1)    # first version
read("home", v=2)    # about was edited at v2, home still v1 content
read("home", v=3)    # updated version

print("\n=== Deleting a page ===\n")

remove("about")
read("about")          # gone
read("about", v=2)     # still readable at old version

print("\n=== Version history ===\n")

print(f"  home history:  {wiki.history('home')}")
print(f"  about history: {wiki.history('about')}")

print("\n=== Changelog (shows reverted edits too) ===\n")

# Simulate a quick correction at the same version
v = version["main"]
wiki.set("home", "TYPO version", timestamp=v, branch="main")
wiki.set("home", "Fixed version", timestamp=v, branch="main")
print(f"  Two edits at same version (v{v}):")

print()
print(f"  history:   {wiki.history('home')}")
print(f"  changelog: {wiki.changelog('home')}")
print("  (history shows 'Fixed version', changelog shows both)")


print("\n=== Drafts (branches) ===\n")

draft("redesign")
edit("home", "Redesigned homepage!", branch="redesign")

print()
read("home")                         # main is unchanged
read("home", branch="redesign")      # draft has new content

print("\n=== Multiple drafts ===\n")

draft("experiment")
edit("home", "Experimental homepage!", branch="experiment")

print()
read("home")                           # main
read("home", branch="redesign")        # draft 1
read("home", branch="experiment")      # draft 2

print("\n=== Sub-draft (branch from a draft) ===\n")

draft("redesign-v2", source="redesign")
edit("home", "Redesign v2 - even better!", branch="redesign-v2")

print()
read("home", branch="redesign")        # original draft
read("home", branch="redesign-v2")     # forked draft

print()
print(f"  branch tree: {wiki.branch_tree}")


print("\n=== Save and Load ===\n")

wiki.save("wiki_data.json")
print("  Saved to wiki_data.json")

# Load into a fresh timeline
from timeline import Timeline
loaded = Timeline.from_file("wiki_data.json")

print("  Loaded from wiki_data.json")
print()
read_loaded = loaded.get("home", version["main"])
read_draft = loaded.get("home", version["redesign-v2"], branch="redesign-v2")
print(f"  main: {read_loaded}")
print(f"  redesign-v2: {read_draft}")
print(f"  branch tree: {loaded.branch_tree}")

# Clean up
import os
os.remove("wiki_data.json")