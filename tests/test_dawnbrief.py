import json
import tempfile
import threading
import unittest
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dawnbrief import calendar, mail, news, sample
from dawnbrief.brief import MAX_CHARS, compose

DAY = date(2026, 10, 26)
NOW = datetime(2026, 10, 26, 7, 0)
SINCE = datetime(2026, 10, 25, 18, 0)


class SampleData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.tmp.name)
        sample.make(cls.folder, DAY)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class CalendarTests(SampleData):
    def test_parses_every_meeting(self):
        meetings = calendar.load(self.folder / "today.ics", me=sample.ME)
        self.assertEqual(len(meetings), 6)
        allhands = next(m for m in meetings if m.title == "Company all-hands")
        self.assertTrue(allhands.optional_for_me)
        self.assertEqual(allhands.attendees, 42)

    def test_focus_blocks_skip_short_gaps(self):
        plan = calendar.plan_day(calendar.load(self.folder / "today.ics", me=sample.ME), DAY)
        blocks = [(s.strftime("%H:%M"), e.strftime("%H:%M")) for s, e in plan.focus_blocks]
        self.assertEqual(blocks, [("11:00", "12:30"), ("13:00", "14:00")])  # 09:15-10:00 is under an hour

    def test_flags_meetings_you_could_skip(self):
        plan = calendar.plan_day(calendar.load(self.folder / "today.ics", me=sample.ME), DAY)
        self.assertEqual({m.title for m, _ in plan.skippable}, {"Company all-hands", "Weekly status sync"})

    def test_declined_and_folded_lines(self):
        ics = ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:A very long title that\r\n  wraps\r\n"
               "DTSTART:20261026T090000\r\nDTEND:20261026T100000\r\n"
               "ATTENDEE;PARTSTAT=DECLINED:mailto:me@x.com\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
        [m] = calendar.parse_ics(ics, me="me@x.com")
        self.assertEqual(m.title, "A very long title that wraps")
        self.assertEqual(calendar.plan_day([m], DAY).meetings, [])


class MailTests(SampleData):
    def test_overnight_window_and_ranking(self):
        result = mail.triage(mail.read_mbox(self.folder / "overnight.mbox"), SINCE, NOW, me=sample.ME)
        self.assertEqual(result.total, 38)  # yesterday afternoon's two messages are outside the window
        self.assertEqual(result.ignorable, 34)
        self.assertEqual(result.needs_you[0][0].name, "Priya Shah")  # due "by 10am" today beats "by Friday"

    def test_no_reply_senders_are_ignorable(self):
        m = mail.Mail("noreply@bank.example", "Bank", "Statement ready", SINCE, {"inbox"}, False, "")
        self.assertEqual(mail.triage([m], SINCE, NOW).ignorable, 1)


RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Tech</title>
<item><title>Fresh story</title><link>https://example.com/a</link><pubDate>Mon, 26 Oct 2026 05:00:00 GMT</pubDate></item>
<item><title>Old story</title><link>https://example.com/b</link><pubDate>Sat, 24 Oct 2026 05:00:00 GMT</pubDate></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Releases</title>
<entry><title>v2.3.4</title><link href="https://example.com/r"/><updated>2026-10-26T01:00:00Z</updated></entry>
</feed>"""


class FeedTests(unittest.TestCase):
    def test_rss(self):
        items = news.parse_feed(RSS)
        self.assertEqual([i.title for i in items], ["Fresh story", "Old story"])
        self.assertEqual(items[0].source, "Tech")

    def test_atom_link_without_children(self):
        [item] = news.parse_feed(ATOM)
        self.assertEqual(item.url, "https://example.com/r")

    def test_pick_prefers_topics_one_per_source(self):
        items = [news.Item("Weather", "", "A", NOW), news.Item("AI agents news", "", "A", NOW),
                 news.Item("More AI", "", "A", NOW), news.Item("Football", "", "B", NOW)]
        self.assertEqual([i.title for i in news.pick(items, ["ai"], 2)], ["AI agents news", "Football"])


class FakeMiniflux(BaseHTTPRequestHandler):
    seen: list = []

    def do_GET(self):
        url = urlparse(self.path)
        FakeMiniflux.seen.append((url.path, parse_qs(url.query), self.headers.get("X-Auth-Token")))
        if self.headers.get("X-Auth-Token") != "test-token":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error_message": "Access Unauthorized"}')
            return
        body = {"total": 1, "entries": [{
            "id": 888, "title": "Miniflux 2.3.4 released", "url": "https://example.org/a",
            "published_at": "2026-10-26T06:15:19Z",
            "feed": {"id": 42, "title": "Miniflux releases", "category": {"id": 22, "title": "Tools"}},
        }]}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *args):
        pass


class MinifluxTests(unittest.TestCase):
    """Matches the GET /v1/entries request and response documented at https://miniflux.app/docs/api.html."""

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeMiniflux)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_unread_since_last_evening(self):
        [item] = news.from_miniflux(self.url, "test-token", SINCE)
        self.assertEqual(item.source, "Miniflux releases (Tools)")
        path, query, token = FakeMiniflux.seen[-1]
        self.assertEqual(path, "/v1/entries")
        self.assertEqual(query["status"], ["unread"])
        self.assertEqual(token, "test-token")
        expected = int(datetime(2026, 10, 25, 18, tzinfo=timezone.utc).timestamp())
        self.assertEqual(query["published_after"], [str(expected)])

    def test_bad_token_raises(self):
        with self.assertRaises(Exception):
            news.from_miniflux(self.url, "wrong", SINCE)


class BriefTests(SampleData):
    def test_whole_brief(self):
        plan = calendar.plan_day(calendar.load(self.folder / "today.ics", me=sample.ME), DAY)
        overnight = mail.triage(mail.read_mbox(self.folder / "overnight.mbox"), SINCE, NOW, me=sample.ME)
        brief = compose(plan, overnight, [news.Item("Story", "", "Tech", NOW)], NOW)
        self.assertLessEqual(len(brief.text), MAX_CHARS)
        self.assertEqual(brief.top3[0], "Reply to Priya Shah: Can you approve the revised quote by 10am?")
        self.assertIn("Prep for Quarterly pricing review with Priya at 10:00", brief.top3)
        self.assertIn("Skipping both frees 1 h 45 min.", brief.text)
        self.assertEqual(len(brief.declines), 2)
        self.assertIn("only decline if you reply OK", brief.text)

    def test_empty_day(self):
        brief = compose(calendar.plan_day([], DAY), mail.Overnight([], 0, 0), [], NOW)
        self.assertIn("nothing booked", brief.text)
        self.assertIn("Nothing overnight needs a reply.", brief.text)


if __name__ == "__main__":
    unittest.main()
