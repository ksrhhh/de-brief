"""
synthesize.py — takes raw_stories.json (from fetch.py) and produces a debate
briefing markdown file using the Claude API.

This encodes the exact template the user approved in chat:
  - background/context per story ("why this happened")
  - core clash framed as both an empirical AND a values question
  - 3-4 motion angles (BP/Parli style: THW / THBT)
  - "Underlying principle in play" — argues BOTH sides of the relevant
    principle, says what tips it in THIS case, and gives a cross-domain
    comparison.

Usage:
    python synthesize.py --in raw_stories.json --out briefing.md --mode daily
    python synthesize.py --in raw_stories.json --out briefing.md --mode weekly

Requires ANTHROPIC_API_KEY in environment.
"""

import argparse
import json
import os
from datetime import date

import anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are building a debate briefing for a competitive Parli/BP \
(British Parliamentary) debater. You will be given a batch of raw news items \
(title, summary/teaser, source, link) pulled from RSS feeds across international \
relations, finance/economics, tech/AI policy, law/courts, environment, social \
movements, and history-adjacent sources.

Your job: select the genuinely significant, debate-relevant stories (skip routine \
or low-stakes items) and write them up following this EXACT structure for each \
story, in markdown:

## [emoji] [Category]

### [Story headline, written as a clear claim not a vague label]

**What happened:** [2-4 sentences, concrete, factual]

**Why this happened (background):** [3-5 sentences of context — incentives, \
history, structural factors that explain why this is happening now. This is the \
single most important section to get right; it's what separates a debater who \
can build a model/mechanism from one who can only describe a headline.]

**The core clash:** [Separate the EMPIRICAL question (what actually causes what / \
what would actually happen) from the VALUES question (which principle should \
win) where relevant. Get specific to this story, not generic.]

**Motion angles:**
- *THW/THBT [motion]* — [what it tests]
(3-4 motions, varied in angle — some pro, some testing the unusual side, at \
least one perspective-flip if natural)

**Underlying principle in play:** [Name the generalizable tension this story is \
an instance of (e.g. deterrence-vs-escalation, neutrality-vs-capture, \
separation-of-powers-vs-efficiency, innovation-vs-precaution). Then: argue the \
FIRST side properly. Then argue the RESPONSE/second side properly — not a token \
sentence, an actual rebuttal that would survive being said out loud in a round. \
Then say what specific fact about THIS case tips the balance one way or the \
other. End with one sentence naming 1-2 OTHER domains where the same structural \
tension recurs, since judges reward debaters who show an argument generalizes.]

---

After all stories, add a final section:

## 🧠 Cross-Story Connections
[1-3 sentences max, only if there's a genuine, non-forced link between two or \
more of today's stories — e.g. the same underlying principle, or one story's \
infrastructure feeding another's controversy. Skip this section entirely if \
there's no real connection; don't manufacture one.]

RULES:
- Never invent facts. If the source material is thin on background, say so \
honestly rather than fabricating specifics.
- Paraphrase everything; never quote more than a short phrase from any source.
- Pick at most 5-7 stories total for a daily briefing — quality and depth over \
breadth. If there are more good stories than that, pick the ones with the \
richest debate angles, not just the most "important" ones by news-cycle standards.
- Vary which categories appear based on what's actually newsworthy that day — \
don't force a story into a weak category just for coverage.
- Write in a direct, sharp register — this is for someone who will use it to \
argue in front of judges in under an hour, not light reading.
"""


def build_user_prompt(stories, mode):
    window_label = "the last 24 hours" if mode == "daily" else "the last 7 days"
    lines = [f"Here are {len(stories)} raw stories from {window_label}. Build the briefing.\n"]
    for s in stories:
        lines.append(
            f"- [{s['source']}] {s['title']}\n  {s['summary'][:500]}\n  ({s['link']})"
        )
    return "\n".join(lines)


def call_claude(stories, mode):
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    user_prompt = build_user_prompt(stories, mode)

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return "".join(block.text for block in response.content if block.type == "text")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", default="raw_stories.json")
    parser.add_argument("--out", default=None)
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily")
    args = parser.parse_args()

    with open(args.infile, "r") as f:
        data = json.load(f)

    stories = data["stories"]
    if not stories:
        print("No stories fetched — skipping synthesis, nothing to send.")
        return

    print(f"Synthesizing {len(stories)} stories ({args.mode} mode)...")
    briefing_body = call_claude(stories, args.mode)

    today = date.today().isoformat()
    label = "Daily" if args.mode == "daily" else "Weekly Deep Dive"
    header = f"# Debate Briefing — {label} — {today}\n\n"

    full_doc = header + briefing_body

    outfile = args.out or f"briefings/{today}-{args.mode}.md"
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    with open(outfile, "w") as f:
        f.write(full_doc)

    print(f"Wrote {outfile}")

    # Also write a fixed-name copy for send_email.py to pick up without
    # needing to know today's date.
    latest_path = f"briefings/_latest_{args.mode}.md"
    with open(latest_path, "w") as f:
        f.write(full_doc)


if __name__ == "__main__":
    main()
