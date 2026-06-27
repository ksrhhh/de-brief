"""
send_email.py — sends the generated briefing via Resend.

Requires environment variables:
    RESEND_API_KEY
    BRIEFING_FROM_EMAIL   (must be on a domain verified in your Resend account)
    BRIEFING_TO_EMAIL     (your inbox)

Usage:
    python send_email.py --in briefings/_latest_daily.md --mode daily
"""

import argparse
import os
import sys

import markdown
import resend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", required=True)
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily")
    args = parser.parse_args()

    api_key = os.environ.get("RESEND_API_KEY")
    from_email = os.environ.get("BRIEFING_FROM_EMAIL")
    to_email = os.environ.get("BRIEFING_TO_EMAIL")

    missing = [name for name, val in [
        ("RESEND_API_KEY", api_key),
        ("BRIEFING_FROM_EMAIL", from_email),
        ("BRIEFING_TO_EMAIL", to_email),
    ] if not val]
    if missing:
        print(f"Missing required env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.infile):
        print(f"No briefing file found at {args.infile} — nothing to send.", file=sys.stderr)
        # Not a hard failure: if fetch found zero stories, synthesize.py exits
        # early and there's nothing to email. Don't fail the whole workflow.
        sys.exit(0)

    with open(args.infile, "r") as f:
        md_content = f.read()

    html_body = markdown.markdown(md_content, extensions=["extra"])

    resend.api_key = api_key

    label = "Daily" if args.mode == "daily" else "Weekly Deep Dive"
    subject = f"🗞️ Debate Briefing — {label}"

    params = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }

    result = resend.Emails.send(params)
    print(f"Email sent: {result}")


if __name__ == "__main__":
    main()
