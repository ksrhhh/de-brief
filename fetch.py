"""
fetch.py — pulls every source in sources.yaml, normalizes into a flat list of
story dicts, and writes the result to a JSON file for synthesize.py to consume.

Usage:
    python fetch.py --since-hours 24 --out raw_stories.json     # daily mode
    python fetch.py --since-hours 168 --out raw_stories.json    # weekly mode

Design notes:
- Network failures on individual feeds are caught and logged, not fatal —
  one dead feed shouldn't kill the whole run.
- We keep raw fields (title, summary, link, source name, published date) and
  do NOT do any debate framing here. That's synthesize.py's job, which calls
  the Claude API. Keeping fetch dumb and synthesis smart makes both easier
  to debug independently.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

import feedparser
import yaml


def load_sources(path="sources.yaml"):
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config["sources"]


def parse_entry_date(entry):
    """feedparser gives us a few possible date fields depending on feed format."""
    for field in ("published_parsed", "updated_parsed"):
        val = entry.get(field)
        if val:
            return datetime(*val[:6], tzinfo=timezone.utc)
    return None


def fetch_one_source(source, cutoff):
    """Fetch a single feed, return list of normalized story dicts within cutoff."""
    name = source["name"]
    url = source["feed_url"]
    access = source.get("access", "teaser")

    stories = []
    try:
        parsed = feedparser.parse(url)

        if parsed.bozo and not parsed.entries:
            print(f"  [WARN] {name}: feed failed to parse, 0 entries ({url})", file=sys.stderr)
            return stories

        for entry in parsed.entries:
            pub_date = parse_entry_date(entry)
            # If a feed doesn't supply dates at all, include it anyway rather than
            # silently dropping it — better to over-include than miss real news.
            if pub_date and pub_date < cutoff:
                continue

            summary = entry.get("summary", "") or entry.get("description", "")

            stories.append({
                "source": name,
                "access_level": access,
                "title": entry.get("title", "").strip(),
                "summary": summary.strip(),
                "link": entry.get("link", ""),
                "published": pub_date.isoformat() if pub_date else None,
            })

    except Exception as e:
        print(f"  [ERROR] {name}: {e} ({url})", file=sys.stderr)

    return stories


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since-hours", type=int, default=24,
                         help="Only include stories published within this window")
    parser.add_argument("--out", default="raw_stories.json")
    parser.add_argument("--sources", default="sources.yaml")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.since_hours)
    sources = load_sources(args.sources)

    print(f"Fetching {len(sources)} sources, cutoff = {cutoff.isoformat()}")

    all_stories = []
    for source in sources:
        print(f"  fetching: {source['name']}")
        stories = fetch_one_source(source, cutoff)
        print(f"    -> {len(stories)} stories within window")
        all_stories.extend(stories)

    print(f"Total stories fetched: {len(all_stories)}")

    with open(args.out, "w") as f:
        json.dump({
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "since_hours": args.since_hours,
            "story_count": len(all_stories),
            "stories": all_stories,
        }, f, indent=2)

    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
