"""Made-up calendar and overnight inbox for trying Dawnbrief without your own data."""
from __future__ import annotations

import mailbox
import random
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path

ME = "alex@example.com"

MEETINGS = [
    # (start, minutes, title, attendees, optional, agenda, recurring)
    ("09:00", 15, "Team stand-up", 6, False, "", True),
    ("10:00", 60, "Quarterly pricing review with Priya", 3, False, "Go through the three pricing options and pick one.", False),
    ("12:30", 30, "Lunch with Sam", 2, False, "", False),
    ("14:00", 60, "Company all-hands", 42, True, "Updates from each team.", True),
    ("15:30", 45, "Weekly status sync", 11, False, "", True),
    ("16:30", 30, "Interview: product designer", 3, False, "Portfolio review, then questions about the onboarding project.", False),
]

NEEDS_YOU = [
    ("Priya Shah", "priya@acme-client.com", "Can you approve the revised quote by 10am?",
     "Hi Alex, the client wants the revised quote approved before our call. Could you confirm the 12% discount?"),
    ("Jordan Lee", "jordan@example.com", "Contract for the Leeds office: please sign",
     "The landlord needs the signed copy by Friday. I've attached the final version."),
    ("Mum", "mum@example.net", "Sunday lunch?", "Are you free on Sunday? Dad's doing a roast."),
    ("Sam Patel", "sam@example.com", "Notes from yesterday", "Here are my notes from the workshop, no action needed."),
]

BULK_SENDERS = [
    ("The Morning Edit", "news@morningedit.example", "category promotions"),
    ("ShopRight", "deals@shopright.example", "category promotions"),
    ("LinkedIn", "notifications@linkedin.example", "category social"),
    ("GitHub", "noreply@github.example", "category updates"),
    ("Product Hunt Daily", "hello@producthunt.example", "category promotions"),
]


def write_ics(path: Path, day: date) -> None:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Dawnbrief sample//EN"]
    for i, (start, minutes, title, attendees, optional, agenda, recurring) in enumerate(MEETINGS):
        begin = datetime.combine(day, datetime.strptime(start, "%H:%M").time())
        end = begin + timedelta(minutes=minutes)
        lines += ["BEGIN:VEVENT", f"UID:sample-{i}@dawnbrief", f"SUMMARY:{title}",
                  f"DTSTART:{begin:%Y%m%dT%H%M%S}", f"DTEND:{end:%Y%m%dT%H%M%S}",
                  "ORGANIZER:mailto:organiser@example.com"]
        if agenda:
            lines.append(f"DESCRIPTION:{agenda}")
        if recurring:
            lines.append("RRULE:FREQ=WEEKLY")
        role = "OPT-PARTICIPANT" if optional else "REQ-PARTICIPANT"
        lines.append(f"ATTENDEE;ROLE={role};PARTSTAT=NEEDS-ACTION:mailto:{ME}")
        lines += [f"ATTENDEE;ROLE=REQ-PARTICIPANT:mailto:person{n}@example.com" for n in range(attendees - 1)]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


def _msg(name: str, addr: str, subject: str, body: str, when: datetime, labels: str, bulk: bool) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"{name} <{addr}>"
    msg["To"] = ME
    msg["Subject"] = subject
    msg["Date"] = format_datetime(when)
    msg["X-Gmail-Labels"] = labels
    if bulk:
        msg["List-Unsubscribe"] = f"<mailto:unsubscribe@{addr.split('@')[1]}>"
    msg.set_content(body)
    return msg


def write_mbox(path: Path, day: date, seed: int = 7) -> None:
    rng = random.Random(seed)
    if path.exists():
        path.unlink()
    box = mailbox.mbox(str(path))
    evening = datetime.combine(day - timedelta(days=1), datetime.min.time()) + timedelta(hours=18)
    # Two messages you'd already seen yesterday afternoon (outside the overnight window).
    box.add(_msg("Priya Shah", "priya@acme-client.com", "Kick-off notes", "Thanks for today.",
                 evening - timedelta(hours=3), "Inbox,Important,Opened", False))
    box.add(_msg("Jordan Lee", "jordan@example.com", "Leeds office", "Viewing went well.",
                 evening - timedelta(hours=2), "Inbox,Important,Opened", False))
    for name, addr, subject, body in NEEDS_YOU:
        when = evening + timedelta(minutes=rng.randint(60, 12 * 60))
        labels = "Inbox,Important,Unread" if name != "Sam Patel" else "Inbox,Unread"
        box.add(_msg(name, addr, subject, body, when, labels, False))
    for n in range(34):
        name, addr, label = BULK_SENDERS[n % len(BULK_SENDERS)]
        when = evening + timedelta(minutes=rng.randint(0, 13 * 60))
        box.add(_msg(name, addr, f"{name}: issue {n + 1}", "Read in your browser.", when, f"Inbox,Unread,{label}", True))
    box.flush()
    box.close()


def write_feeds(path: Path) -> None:
    path.write_text(
        "# One feed URL per line. RSSHub routes work too, e.g. http://localhost:1200/github/repos/miniflux\n"
        "https://feeds.bbci.co.uk/news/technology/rss.xml\n"
        "https://hnrss.org/frontpage\n",
        encoding="utf-8",
    )


def make(folder: Path, day: date) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    write_ics(folder / "today.ics", day)
    write_mbox(folder / "overnight.mbox", day)
    write_feeds(folder / "feeds.txt")
