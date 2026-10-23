"""Today's meetings from an .ics file, free focus blocks, and meetings worth declining."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path


@dataclass
class Meeting:
    title: str
    start: datetime
    end: datetime
    organizer: str = ""
    attendees: int = 0
    optional_for_me: bool = False
    has_agenda: bool = False
    recurring: bool = False
    declined: bool = False

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


@dataclass
class DayPlan:
    meetings: list[Meeting]
    focus_blocks: list[tuple[datetime, datetime]] = field(default_factory=list)
    skippable: list[tuple[Meeting, str]] = field(default_factory=list)


def _unfold(text: str) -> list[str]:
    """iCalendar folds long lines: a line starting with a space continues the previous one."""
    lines: list[str] = []
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _parse_dt(value: str) -> datetime:
    value = value.strip()
    if re.fullmatch(r"\d{8}", value):  # all-day
        return datetime.strptime(value, "%Y%m%d")
    return datetime.strptime(value.rstrip("Z")[:15], "%Y%m%dT%H%M%S")


def parse_ics(text: str, me: str = "") -> list[Meeting]:
    meetings: list[Meeting] = []
    current: dict | None = None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            current = {"attendees": 0, "optional": False, "declined": False, "agenda": False, "recurring": False}
        elif line == "END:VEVENT" and current is not None:
            if "start" in current:
                end = current.get("end") or current["start"] + timedelta(hours=1)
                meetings.append(Meeting(
                    title=current.get("title", "(no title)"),
                    start=current["start"], end=end,
                    organizer=current.get("organizer", ""),
                    attendees=current["attendees"],
                    optional_for_me=current["optional"],
                    has_agenda=current["agenda"],
                    recurring=current["recurring"],
                    declined=current["declined"],
                ))
            current = None
        elif current is not None and ":" in line:
            key, _, value = line.partition(":")
            name = key.split(";")[0].upper()
            if name == "SUMMARY":
                current["title"] = value.replace("\\,", ",")
            elif name == "DTSTART":
                current["start"] = _parse_dt(value)
            elif name == "DTEND":
                current["end"] = _parse_dt(value)
            elif name == "ORGANIZER":
                current["organizer"] = value.removeprefix("mailto:")
            elif name == "DESCRIPTION":
                current["agenda"] = len(value.strip()) >= 20
            elif name == "RRULE":
                current["recurring"] = True
            elif name == "ATTENDEE":
                current["attendees"] += 1
                if me and me.lower() in value.lower():
                    if "ROLE=OPT-PARTICIPANT" in key.upper():
                        current["optional"] = True
                    if "PARTSTAT=DECLINED" in key.upper():
                        current["declined"] = True
    return meetings


def plan_day(meetings: list[Meeting], day: date, work_start: time = time(9), work_end: time = time(17, 30),
             min_focus_minutes: int = 60) -> DayPlan:
    today = sorted((m for m in meetings if m.start.date() == day and not m.declined), key=lambda m: m.start)
    plan = DayPlan(meetings=today)

    cursor = datetime.combine(day, work_start)
    end_of_day = datetime.combine(day, work_end)
    for m in today:
        if m.minutes >= 24 * 60:  # all-day events don't block focus time
            continue
        if (m.start - cursor).total_seconds() >= min_focus_minutes * 60:
            plan.focus_blocks.append((cursor, min(m.start, end_of_day)))
        cursor = max(cursor, m.end)
    if (end_of_day - cursor).total_seconds() >= min_focus_minutes * 60:
        plan.focus_blocks.append((cursor, end_of_day))

    for m in today:
        reason = skip_reason(m)
        if reason:
            plan.skippable.append((m, reason))
    return plan


def skip_reason(m: Meeting) -> str:
    """Why a meeting might be worth declining. Empty string means keep it."""
    if m.optional_for_me and m.attendees >= 6:
        return f"you're optional and {m.attendees} people are invited"
    if m.recurring and not m.has_agenda and m.attendees >= 8:
        return f"recurring, no agenda, {m.attendees} people"
    return ""


def decline_draft(m: Meeting) -> str:
    return (f"Hi, I'll skip \"{m.title}\" today to keep a focus block clear. "
            f"Could you send me the notes or anything you need from me? Thanks.")


def load(path: str | Path, me: str = "") -> list[Meeting]:
    return parse_ics(Path(path).read_text(encoding="utf-8"), me=me)
