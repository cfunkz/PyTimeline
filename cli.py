"""
cli.py - Command-line interface for Timeline.

    python cli.py

Commands:
    set <key> <value> <timestamp> [branch]
    get <key> <timestamp> [branch]
    delete <key> <timestamp> [branch]
    branch <name> <from_timestamp> [source]
    merge <source> [into] [timestamp]
    keys <timestamp> [branch]
    diff <key> <t1> <t2> [branch]
    history <key> [branch]
    changelog <key> [branch]
    branches
    save <filepath>
    load <filepath>
    help
    exit
"""

import json
import shlex
from timeline import Timeline

cache = Timeline()


def print_help():
    print("Commands:")
    print("  set <key> <value> <timestamp> [branch]")
    print("  get <key> <timestamp> [branch]")
    print("  delete <key> <timestamp> [branch]")
    print("  branch <name> <from_timestamp> [source]")
    print("  merge <source> [into] [timestamp]  - publish a draft")
    print("  keys <timestamp> [branch]          - list all keys")
    print("  diff <key> <t1> <t2> [branch]      - compare two versions")
    print("  history <key> [branch]")
    print("  changelog <key> [branch]")
    print("  branches                           - list all branches")
    print("  save <filepath>                    - save to JSON file")
    print("  load <filepath>                    - load from JSON file")
    print("  help                               - show this message")
    print("  exit                               - quit")


def main():
    print("Timeline CLI (type 'help' for commands, 'exit' to quit)\n")

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        try:
            parts = shlex.split(raw)
        except ValueError:
            parts = raw.split()
        if not parts:
            continue

        cmd = parts[0]

        try:
            if cmd == "exit":
                break

            elif cmd == "help":
                print_help()

            elif cmd == "set":
                if len(parts) < 4 or len(parts) > 5:
                    print("Usage: set <key> <value> <timestamp> [branch]")
                    continue
                key, ts = parts[1], int(parts[3])
                try:
                    value = json.loads(parts[2])
                except (json.JSONDecodeError, ValueError):
                    value = parts[2]
                branch = parts[4] if len(parts) == 5 else "main"
                cache.set(key, value, ts, branch)
                print(f"  [{branch}] {key} = {value!r} at t={ts}")

            elif cmd == "get":
                if len(parts) < 3 or len(parts) > 4:
                    print("Usage: get <key> <timestamp> [branch]")
                    continue
                key, ts = parts[1], int(parts[2])
                branch = parts[3] if len(parts) == 4 else "main"
                result = cache.get(key, ts, branch)
                print(f"  [{branch}] {key} at t={ts} = {result!r}")

            elif cmd == "delete":
                if len(parts) < 3 or len(parts) > 4:
                    print("Usage: delete <key> <timestamp> [branch]")
                    continue
                key, ts = parts[1], int(parts[2])
                branch = parts[3] if len(parts) == 4 else "main"
                cache.delete(key, ts, branch)
                print(f"  [{branch}] deleted {key} at t={ts}")

            elif cmd == "branch":
                if len(parts) < 3 or len(parts) > 4:
                    print("Usage: branch <name> <from_timestamp> [source]")
                    continue
                name, from_ts = parts[1], int(parts[2])
                source = parts[3] if len(parts) == 4 else "main"
                cache.branch(name, from_ts, source)
                print(f"  created '{name}' from '{source}' at t={from_ts}")

            elif cmd == "merge":
                if len(parts) < 2 or len(parts) > 4:
                    print("Usage: merge <source> [into] [timestamp]")
                    continue
                source = parts[1]
                into = parts[2] if len(parts) >= 3 else "main"
                ts = int(parts[3]) if len(parts) == 4 else None
                cache.merge(source, into=into, timestamp=ts)
                label = f" at t={ts}" if ts else ""
                print(f"  merged '{source}' into '{into}'{label}")

            elif cmd == "keys":
                if len(parts) < 2 or len(parts) > 3:
                    print("Usage: keys <timestamp> [branch]")
                    continue
                ts = int(parts[1])
                branch = parts[2] if len(parts) == 3 else "main"
                result = cache.keys(ts, branch)
                if not result:
                    print(f"  [{branch}] no keys at t={ts}")
                else:
                    for k in result:
                        print(f"  {k}")

            elif cmd == "diff":
                if len(parts) < 4 or len(parts) > 5:
                    print("Usage: diff <key> <t1> <t2> [branch]")
                    continue
                key = parts[1]
                t1, t2 = int(parts[2]), int(parts[3])
                branch = parts[4] if len(parts) == 5 else "main"
                old, new = cache.diff(key, t1, t2, branch)
                print(f"  t={t1}: {old!r}")
                print(f"  t={t2}: {new!r}")

            elif cmd == "history":
                if len(parts) < 2 or len(parts) > 3:
                    print("Usage: history <key> [branch]")
                    continue
                key = parts[1]
                branch = parts[2] if len(parts) == 3 else "main"
                h = cache.history(key, branch)
                if not h:
                    print(f"  [{branch}] no history for '{key}'")
                else:
                    for ts, val in h:
                        print(f"  t={ts}: {val!r}")

            elif cmd == "changelog":
                if len(parts) < 2 or len(parts) > 3:
                    print("Usage: changelog <key> [branch]")
                    continue
                key = parts[1]
                branch = parts[2] if len(parts) == 3 else "main"
                h = cache.changelog(key, branch)
                if not h:
                    print(f"  [{branch}] no changelog for '{key}'")
                else:
                    for ts, val in h:
                        print(f"  t={ts}: {val!r}")

            elif cmd == "branches":
                for name in cache.branches:
                    main_branch = cache.branch_tree.get(name, "-")
                    label = "main-branch" if name not in cache.branch_tree else "sub-branch"
                    print(f"  {name} ({label}, from: {main_branch})")

            elif cmd == "save":
                if len(parts) != 2:
                    print("Usage: save <filepath>")
                    continue
                cache.save(parts[1])
                print(f"  saved to {parts[1]}")

            elif cmd == "load":
                if len(parts) != 2:
                    print("Usage: load <filepath>")
                    continue
                cache.load(parts[1])
                print(f"  loaded from {parts[1]}")

            else:
                print(f"  unknown command: {cmd} (type 'help')")

        except Exception as e:
            print(f"  error: {e}")


if __name__ == "__main__":
    main()