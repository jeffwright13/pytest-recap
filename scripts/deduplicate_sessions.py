#!/usr/bin/env python3
"""
Utility script to deduplicate an existing all_test_sessions.json file by session_id.
Keeps the last occurrence of each session_id.
Usage:
    python deduplicate_sessions.py [input.json] [output.json]
If no arguments are given, defaults to 'all_test_sessions.json' in the current directory.
"""
import sys
import json

INPUT = sys.argv[1] if len(sys.argv) > 1 else "all_test_sessions.json"
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else "all_test_sessions.deduped.json"

def main():
    with open(INPUT, "r") as f:
        sessions = json.load(f)
    session_map = {}
    for s in sessions:
        sid = s.get("session_id")
        if sid is not None:
            session_map[sid] = s
        else:
            session_map[id(s)] = s  # fallback for missing session_id
    deduped = list(session_map.values())
    with open(OUTPUT, "w") as f:
        json.dump(deduped, f, indent=2)
    print(f"Deduplicated {len(sessions)} sessions to {len(deduped)} unique session_ids. Output: {OUTPUT}")

if __name__ == "__main__":
    main()
