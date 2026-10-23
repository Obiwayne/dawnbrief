"""Put calendar, email and news together into one short morning message."""
from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime

from .calendar import DayPlan, decline_draft
from .mail import Overnight
from .news import Item

MAX_CHARS = 1500  # one phone screen or so; the Bot is told the same limit


@dataclass
class Brief:
    text: str
    top3: list[str]
    declines: list[tuple[str, str]] = field(default_factory=list)  # (meeting title, draft)
    warnings: list[str] = field(default_factory=list)


def _hm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def top_three(plan: DayPlan, mail: Overnight) -> list[str]:
    """Replies that ask something of you first, then the first meeting, then the first focus block."""
    jobs = [f"Reply to {m.who}: {m.subject}" for m, score in mail.needs_you if score >= 4][:2]
    skippable = {id(m) for m, _ in plan.skippable}
    # The first meeting that needs real prep: one with an agenda, or 30+ minutes, and not one you could skip.
    prep = next((m for m in plan.meetings if id(m) not in skippable and (m.has_agenda or m.minutes >= 30)), None)
    if prep:
        jobs.append(f"Prep for {prep.title} at {_hm(prep.start)}")
    if plan.focus_blocks and len(jobs) < 3:
        start, end = plan.focus_blocks[0]
        jobs.append(f"Protect focus time {_hm(start)}-{_hm(end)}")
    for m, _ in mail.needs_you:
        if len(jobs) >= 3:
            break
        line = f"Reply to {m.who}: {m.subject}"
        if line not in jobs:
            jobs.append(line)
    return jobs[:3]


def compose(plan: DayPlan, mail: Overnight, news: list[Item], now: datetime, warnings: list[str] | None = None) -> Brief:
    lines = [f"Good morning. {now.strftime('%A %d %B')}."]

    lines.append("")
    if plan.meetings:
        lines.append(f"CALENDAR ({len(plan.meetings)})")
        for m in plan.meetings[:6]:
            lines.append(f"- {_hm(m.start)} {m.title} ({m.minutes} min)")
        if len(plan.meetings) > 6:
            lines.append(f"- and {len(plan.meetings) - 6} more")
    else:
        lines.append("CALENDAR: nothing booked.")

    if plan.focus_blocks:
        blocks = ", ".join(f"{_hm(s)}-{_hm(e)}" for s, e in plan.focus_blocks[:3])
        lines.append(f"Focus time: {blocks}")

    lines.append("")
    needs = mail.needs_you[:3]
    lines.append(f"NEEDS YOU ({len(mail.needs_you)} of {mail.total} overnight)")
    if needs:
        for m, _ in needs:
            lines.append(f"- {m.who}: {m.subject}")
    else:
        lines.append("- Nothing overnight needs a reply.")
    if mail.ignorable:
        lines.append(f"Can ignore: {mail.ignorable} newsletters, notifications and promotions.")

    if news:
        lines.append("")
        lines.append("NEWS")
        for item in news:
            lines.append(f"- {item.title} ({item.source})")

    top3 = top_three(plan, mail)
    lines.append("")
    lines.append("TOP 3")
    for i, job in enumerate(top3, 1):
        lines.append(f"{i}. {job}")

    declines = [(m.title, decline_draft(m)) for m, _ in plan.skippable]
    if declines:
        lines.append("")
        lines.append("COULD SKIP (I'll only decline if you reply OK)")
        for (m, reason) in plan.skippable:
            lines.append(f"- {_hm(m.start)} {m.title}: {reason}")
        freed = sum(m.minutes for m, _ in plan.skippable)
        lines.append(f"Skipping {'both' if len(plan.skippable) == 2 else 'these'} frees {freed // 60} h {freed % 60:02d} min."
                     if freed >= 60 else f"Skipping frees {freed} min.")

    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[: MAX_CHARS - 1].rsplit("\n", 1)[0] + "\n…"
    return Brief(text=text, top3=top3, declines=declines, warnings=list(warnings or []))


def to_html(brief: Brief) -> str:
    body = html.escape(brief.text)
    drafts = "".join(
        f"<details><summary>Decline draft: {html.escape(t)}</summary><p>{html.escape(d)}</p></details>"
        for t, d in brief.declines
    )
    warn = "".join(f"<li>{html.escape(w)}</li>" for w in brief.warnings)
    return (
        "<!doctype html><meta charset='utf-8'><title>Dawnbrief preview</title>"
        "<style>body{font:16px/1.5 system-ui;max-width:420px;margin:32px auto;padding:0 16px;color:#15131f}"
        "pre{white-space:pre-wrap;background:#f5f4fb;border-radius:16px;padding:16px;font:15px/1.5 system-ui}"
        "details{margin:8px 0}small{color:#8c89a6}</style>"
        f"<h1>Your 7am brief</h1><pre>{body}</pre>{drafts}"
        + (f"<h2>Warnings</h2><ul>{warn}</ul>" if warn else "")
        + f"<p><small>{len(brief.text)} characters. Preview made on your computer; nothing was sent.</small></p>"
    )
