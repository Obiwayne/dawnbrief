"""dawnbrief preview: build tomorrow's 7am brief on your own computer, from files you exported. Sends nothing."""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from . import calendar, mail, news, sample
from .brief import compose, to_html


def _feeds(path: str | None) -> list[str]:
    if not path:
        return []
    return [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


def cmd_preview(args: argparse.Namespace) -> int:
    now = datetime.fromisoformat(args.now) if args.now else datetime.now().replace(second=0, microsecond=0)
    since = datetime.combine(now.date() - timedelta(days=1), datetime.min.time()) + timedelta(hours=args.overnight_from)
    warnings: list[str] = []

    meetings = calendar.load(args.ics, me=args.me) if args.ics else []
    plan = calendar.plan_day(meetings, now.date())

    mails = mail.read_mbox(args.mbox) if args.mbox else []
    overnight = mail.triage(mails, since, now, me=args.me)

    items: list[news.Item] = []
    if args.miniflux:
        token = os.environ.get(args.token_env, "")
        if not token:
            warnings.append(f"Miniflux URL given but ${args.token_env} is empty, so news was skipped.")
        else:
            try:
                items = news.from_miniflux(args.miniflux, token, since)
            except Exception as exc:
                warnings.append(f"Miniflux: {exc.__class__.__name__}: {exc}")
    if args.feeds:
        feed_items, failed = news.from_feeds(_feeds(args.feeds), since)
        items += feed_items
        warnings += [f"Feed skipped: {f}" for f in failed]
    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    chosen = news.pick(sorted(items, key=lambda i: i.published, reverse=True), topics, limit=args.news)

    brief = compose(plan, overnight, chosen, now, warnings)
    sys.stdout.reconfigure(encoding="utf-8")
    print(brief.text)
    for w in brief.warnings:
        print(f"! {w}", file=sys.stderr)
    if args.html:
        Path(args.html).write_text(to_html(brief), encoding="utf-8")
        print(f"\nHTML preview: {args.html}", file=sys.stderr)
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    day = date.fromisoformat(args.date)
    sample.make(Path(args.folder), day)
    print(f"Sample calendar, inbox and feed list for {day:%A %d %B %Y} written to {args.folder}/")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dawnbrief", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("preview", help="build the brief from your exported calendar, mail and feeds")
    pv.add_argument("--ics", help="calendar export (.ics)")
    pv.add_argument("--mbox", help="Google Takeout mail export (.mbox)")
    pv.add_argument("--feeds", help="text file with one RSS/Atom/RSSHub feed URL per line")
    pv.add_argument("--miniflux", help="your Miniflux URL, e.g. http://localhost:8080")
    pv.add_argument("--token-env", default="MINIFLUX_TOKEN", help="environment variable holding the Miniflux API key")
    pv.add_argument("--topics", default="", help="comma-separated words to prefer in news headlines")
    pv.add_argument("--news", type=int, default=2, help="how many news items (default 2)")
    pv.add_argument("--me", default="", help="your email address, to spot meetings where you're optional")
    pv.add_argument("--now", help="pretend it's this time (ISO, e.g. 2026-10-26T07:00)")
    pv.add_argument("--overnight-from", type=int, default=18, help="overnight starts at this hour yesterday (default 18)")
    pv.add_argument("--html", help="also write an HTML preview here")
    pv.set_defaults(func=cmd_preview)

    sm = sub.add_parser("sample", help="write a made-up calendar, inbox and feed list to try it")
    sm.add_argument("folder", nargs="?", default="demo")
    sm.add_argument("--date", default="2026-10-26", help="the morning to simulate (default Monday 26 Oct 2026)")
    sm.set_defaults(func=cmd_sample)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
