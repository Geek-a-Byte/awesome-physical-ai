#!/usr/bin/env python3
"""
check_entry_counts.py — verify that every category in README.md
is within the 15–25 entry target band.

Usage:
    python scripts/check_entry_counts.py

It also verifies that the "Last updated / N entries" status line in
README.md reports the true total, so the hand-maintained figure cannot
drift away from the list it describes.

Exit codes:
    0 — all categories within [15, 25] and the status-line total is correct
    1 — a category is outside the band, or the status line is missing/stale
"""

import re
import sys
from pathlib import Path

# Matches the centred status line near the top of README.md.
STATUS_LINE_RE = re.compile(
    r"<strong>Last updated:</strong>\s*(\d{4}-\d{2}-\d{2})"
    r".*?<strong>(\d+) entries</strong>"
)

# The ⚠ glyph is not representable in the cp1252 console Windows uses by
# default, and printing it there raises UnicodeEncodeError. Force UTF-8 so
# the script reports a verdict instead of a traceback.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGET_LOW = 15
TARGET_HIGH = 25

KNOWN_CATEGORIES = {
    "Simulators",
    "Datasets",
    "Benchmarks",
    "Evaluation Methodology",
    "Robotics Foundation Models",
    "World Models",
    "Manipulation",
    "Locomotion",
    "Sim-to-Real",
    "Safety & Robustness",
    "Governance & Policy",
    "Production Patterns / Reference Architectures",
    "Courses",
    "Companies",
}

# Headings that are structural (not content categories)
SKIP_HEADINGS = {
    "Contents",
    "Contributing",
    "License",
    "Awesome Physical AI",
}


def parse_categories(readme_path: Path) -> dict[str, int]:
    """Return {category_name: entry_count} for all known categories."""
    text = readme_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    counts: dict[str, int] = {}
    current_category: str | None = None
    current_count = 0

    heading_re = re.compile(r"^#{1,3}\s+(.+)$")
    bullet_re = re.compile(r"^\s*[-*]\s+\[")  # lines like `- [Name](url)`

    for line in lines:
        m = heading_re.match(line)
        if m:
            # Save previous category
            if current_category and current_category in KNOWN_CATEGORIES:
                counts[current_category] = current_count
            heading_text = m.group(1).strip()
            if heading_text in KNOWN_CATEGORIES:
                current_category = heading_text
                current_count = 0
            else:
                current_category = None
                current_count = 0
        elif current_category and bullet_re.match(line):
            current_count += 1

    # Flush last category
    if current_category and current_category in KNOWN_CATEGORIES:
        counts[current_category] = current_count

    return counts


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    readme = repo_root / "README.md"

    if not readme.exists():
        print(f"ERROR: README.md not found at {readme}")
        return 1

    counts = parse_categories(readme)

    # Check for missing categories
    missing = KNOWN_CATEGORIES - counts.keys()
    if missing:
        print(f"WARNING: categories not found in README: {', '.join(sorted(missing))}")

    col_w = 32
    print(f"\n{'Category':<{col_w}} {'Count':>5}  Status")
    print("-" * (col_w + 15))

    any_fail = False
    for category in sorted(KNOWN_CATEGORIES):
        count = counts.get(category, 0)
        if count < TARGET_LOW:
            status = "LOW ⚠"
            any_fail = True
        elif count > TARGET_HIGH:
            status = "HIGH ⚠"
            any_fail = True
        else:
            status = "OK"
        print(f"{category:<{col_w}} {count:>5}  {status}")

    total = sum(counts.values())
    print(f"{'TOTAL':<{col_w}} {total:>5}")

    status = STATUS_LINE_RE.search(readme.read_text(encoding="utf-8"))
    print()
    if status is None:
        print("FAIL — no 'Last updated / N entries' status line found in README.md.")
        any_fail = True
    elif int(status.group(2)) != total:
        print(
            f"FAIL — README status line claims {status.group(2)} entries, "
            f"but the categories hold {total}."
        )
        any_fail = True
    else:
        print(f"Status line OK — {total} entries, last updated {status.group(1)}.")

    print()
    if any_fail:
        print("FAIL — see the errors above.")
        return 1

    print(f"PASS — all categories within [{TARGET_LOW}, {TARGET_HIGH}].")
    return 0


if __name__ == "__main__":
    sys.exit(main())
