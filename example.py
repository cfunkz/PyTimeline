"""
example.py - A blog with drafts, publishing, and version history.

Every edit is saved. You can view any old version,
create drafts without affecting published posts,
and publish drafts when they're ready.

Uses every Timeline feature:
    set       → write a post
    get       → read a post (at any version)
    delete    → remove a post
    keys      → list all posts
    diff      → compare two versions
    history   → see version list
    changelog → see every edit including corrections
    branch    → create a draft
    merge     → publish a draft
    save/load → persist to disk

    python example.py
"""

from timeline import Timeline

blog = Timeline()
version = {"main": 0}


def write_post(page, content, branch="main"):
    """Write or update a post. Each edit increments the version."""
    v = version.get(branch, 0) + 1
    version[branch] = v
    blog.set(page, content, timestamp=v, branch=branch)
    print(f"  [{branch} v{v}] Saved '{page}'")


def read_post(page, v=None, branch="main"):
    """Read a post. Optionally at a specific version."""
    if v is None:
        v = version.get(branch, 0)
    result = blog.get(page, v, branch=branch)
    if result is None:
        print(f"  [{branch} v{v}] '{page}' does not exist")
    else:
        print(f"  [{branch} v{v}] {page}: {result}")


def remove_post(page, branch="main"):
    """Remove a post (old versions are still readable)."""
    v = version.get(branch, 0) + 1
    version[branch] = v
    blog.delete(page, timestamp=v, branch=branch)
    print(f"  [{branch} v{v}] Removed '{page}'")


def list_posts(branch="main"):
    """List all posts that currently exist."""
    v = version.get(branch, 0)
    posts = blog.keys(v, branch=branch)
    if not posts:
        print(f"  [{branch}] No posts")
    else:
        print(f"  [{branch}] Posts: {', '.join(posts)}")


def create_draft(name, source="main"):
    """Create a draft branch from the current version."""
    v = version.get(source, 0)
    blog.branch(name, from_timestamp=v, source=source)
    version[name] = v
    print(f"  Created draft '{name}' from '{source}' at v{v}")


def publish_draft(name, into="main"):
    """Merge a draft branch into the target (publish it)."""
    v = version.get(into, 0) + 1
    version[into] = v
    blog.merge(name, into=into, timestamp=v)
    print(f"  Published '{name}' into '{into}' at v{v}")


# ─────────────────────────────────────────────────────────────

print("=== Writing posts ===\n")

write_post("home", "Welcome to my blog")
write_post("about", "I write about Python")
write_post("home", "Welcome to my blog! Now with more posts.")
read_post("home")


print("\n=== Reading old versions (time travel) ===\n")

read_post("home", v=1)    # first version
read_post("home", v=3)    # updated version


print("\n=== Listing all posts ===\n")

list_posts()


print("\n=== Deleting a post ===\n")

remove_post("about")
list_posts()                     # about is gone
read_post("about", v=2)         # but old version is still readable
write_post("about", "About page is back!")
list_posts()                     # about is back


print("\n=== Comparing versions (diff) ===\n")

old, new = blog.diff("home", t1=1, t2=3)
print(f"  home v1: {old}")
print(f"  home v3: {new}")


print("\n=== Version history ===\n")

print(f"  home history:  {blog.history('home')}")
print(f"  about history: {blog.history('about')}")


print("\n=== Changelog (shows every edit, even corrections) ===\n")

# Simulate a quick correction at the same version
v = version["main"]
blog.set("home", "TYPO version", timestamp=v, branch="main")
blog.set("home", "Fixed version", timestamp=v, branch="main")
print(f"  Two edits at same version (v{v}):")
print(f"  history:   {blog.history('home')}")
print(f"  changelog: {blog.changelog('home')}")
print("  (history shows latest per version, changelog shows everything)")


print("\n=== Creating a draft ===\n")

create_draft("redesign")
write_post("home", "Redesigned homepage!", branch="redesign")

print()
read_post("home")                          # main is unchanged
read_post("home", branch="redesign")       # draft has new content


print("\n=== Publishing the draft ===\n")

publish_draft("redesign")
read_post("home")                          # main now has the redesigned content


print("\n=== Multiple drafts ===\n")

create_draft("dark-theme")
create_draft("new-footer")
write_post("home", "Dark theme homepage!", branch="dark-theme")
write_post("home", "New footer homepage!", branch="new-footer")

print()
read_post("home")                              # main (published)
read_post("home", branch="dark-theme")         # draft 1
read_post("home", branch="new-footer")         # draft 2


print("\n=== Sub-draft (branch from a draft) ===\n")

create_draft("dark-theme-v2", source="dark-theme")
write_post("home", "Dark theme v2 — even better!", branch="dark-theme-v2")

print()
read_post("home", branch="dark-theme")        # original draft
read_post("home", branch="dark-theme-v2")     # forked draft

print()
print(f"  branch tree: {blog.branch_tree}")


print("\n=== Diff across branches ===\n")

main_v = version["main"]
draft_v = version["dark-theme-v2"]
old, new = blog.diff("home", main_v, draft_v, branch1="main", branch2="dark-theme-v2")
print(f"  main:           {old}")
print(f"  dark-theme-v2:  {new}")


print("\n=== Save and Load ===\n")

blog.save("blog_data.json")
print("  Saved to blog_data.json")

loaded = Timeline.from_file("blog_data.json")
print("  Loaded from blog_data.json")
print()
print(f"  main: {loaded.get('home', version['main'])}")
print(f"  dark-theme-v2: {loaded.get('home', version['dark-theme-v2'], branch='dark-theme-v2')}")
print(f"  branches: {list(loaded.branches.keys())}")

import os
os.remove("blog_data.json")
