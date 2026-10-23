"""Overnight email from a Google Takeout .mbox: what needs you and what you can ignore."""
from __future__ import annotations

import mailbox
import re
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

ASK_WORDS = re.compile(
    r"\?|\b(can you|could you|please|by (today|tomorrow|monday|tuesday|wednesday|thursday|friday|eod|end of day)"
    r"|deadline|urgent|asap|sign|approve|confirm|invoice due|overdue)\b",
    re.IGNORECASE,
)
DUE_TODAY = re.compile(
    r"\b(today|tonight|this morning|asap|urgent|by \d{1,2}(:\d{2})?\s?(am|pm)|before (our|the) (call|meeting))\b",
    re.IGNORECASE,
)
NO_REPLY = re.compile(r"no-?reply|donotreply|notifications?@|mailer-daemon", re.IGNORECASE)


@dataclass
class Mail:
    sender: str
    name: str
    subject: str
    when: datetime
    labels: set[str]
    is_list: bool
    snippet: str

    @property
    def who(self) -> str:
        return self.name or self.sender


@dataclass
class Overnight:
    needs_you: list[tuple[Mail, int]]  # (mail, score), best first
    ignorable: int
    total: int


def _text(value) -> str:
    if value is None:
        return ""
    try:
        return str(make_header(decode_header(str(value))))
    except Exception:
        return str(value)


def _body(msg) -> str:
    part = msg
    if msg.is_multipart():
        part = next((p for p in msg.walk() if p.get_content_type() == "text/plain"), None)
        if part is None:
            return ""
    payload = part.get_payload(decode=True) or b""
    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")


def read_mbox(path: str | Path) -> list[Mail]:
    box = mailbox.mbox(str(path), create=False)
    out: list[Mail] = []
    for msg in box:
        name, addr = parseaddr(_text(msg.get("From")))
        try:
            when = parsedate_to_datetime(msg.get("Date")).replace(tzinfo=None)
        except Exception:
            continue
        labels = {l.strip().lower() for l in _text(msg.get("X-Gmail-Labels")).split(",") if l.strip()}
        out.append(Mail(
            sender=addr.lower(), name=name, subject=_text(msg.get("Subject")) or "(no subject)", when=when,
            labels=labels, is_list=bool(msg.get("List-Unsubscribe") or msg.get("List-Id")),
            snippet=" ".join(_body(msg).split())[:240],
        ))
    box.close()
    return out


def known_contacts(mails: list[Mail]) -> set[str]:
    """Senders Gmail marked Important, outside mailing lists: a stand-in for the people you actually deal with."""
    return {m.sender for m in mails if "sent" not in m.labels and not m.is_list and "important" in m.labels}


def triage(mails: list[Mail], since: datetime, until: datetime, me: str = "") -> Overnight:
    window = [m for m in mails if since <= m.when <= until and "sent" not in m.labels and m.sender != me.lower()]
    contacts = known_contacts(mails)
    scored: list[tuple[Mail, int]] = []
    ignorable = 0
    for m in window:
        if m.is_list or NO_REPLY.search(m.sender) or labels_say_bulk(m.labels):
            ignorable += 1
            continue
        score = 1
        if m.sender in contacts:
            score += 2
        if "important" in m.labels or "starred" in m.labels:
            score += 2
        if ASK_WORDS.search(m.subject) or ASK_WORDS.search(m.snippet):
            score += 3
        if DUE_TODAY.search(m.subject) or DUE_TODAY.search(m.snippet):
            score += 2
        scored.append((m, score))
    scored.sort(key=lambda pair: (-pair[1], pair[0].when))
    return Overnight(needs_you=scored, ignorable=ignorable, total=len(window))


def labels_say_bulk(labels: set[str]) -> bool:
    return bool(labels & {"category promotions", "category social", "category updates", "category forums", "spam"})
