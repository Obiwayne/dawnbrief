"""News on your topics: unread entries from Miniflux, or straight from RSS/Atom feeds (including RSSHub routes)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

USER_AGENT = "Dawnbrief/0.1 (+https://github.com/Obiwayne/dawnbrief)"
ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass
class Item:
    title: str
    url: str
    source: str
    published: datetime


def _get(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _naive_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def _iso(value: str) -> datetime:
    return _naive_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def from_miniflux(base_url: str, token: str, since: datetime, limit: int = 50) -> list[Item]:
    """Unread entries published after `since` (UTC), newest first, via GET /v1/entries."""
    query = urllib.parse.urlencode({
        "status": "unread", "order": "published_at", "direction": "desc", "limit": limit,
        "published_after": int(since.replace(tzinfo=timezone.utc).timestamp()),
    })
    data = json.loads(_get(f"{base_url.rstrip('/')}/v1/entries?{query}", {"X-Auth-Token": token}))
    items = []
    for e in data.get("entries") or []:
        feed = e.get("feed") or {}
        category = (feed.get("category") or {}).get("title", "")
        source = feed.get("title", "") + (f" ({category})" if category else "")
        items.append(Item(e.get("title", ""), e.get("url", ""), source, _iso(e["published_at"])))
    return items


def parse_feed(xml_bytes: bytes, fallback_source: str = "") -> list[Item]:
    root = ET.fromstring(xml_bytes)
    items: list[Item] = []
    if root.tag == f"{ATOM}feed":
        source = (root.findtext(f"{ATOM}title") or fallback_source).strip()
        for entry in root.findall(f"{ATOM}entry"):
            link = entry.find(f"{ATOM}link[@rel='alternate']")
            if link is None:  # Elements without children are falsy, so no `or` here
                link = entry.find(f"{ATOM}link")
            when = entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated")
            if when:
                items.append(Item((entry.findtext(f"{ATOM}title") or "").strip(),
                                  link.get("href", "") if link is not None else "", source, _iso(when)))
        return items
    channel = root.find("channel")
    if channel is None:
        return items
    source = (channel.findtext("title") or fallback_source).strip()
    for item in channel.findall("item"):
        when = item.findtext("pubDate")
        if not when:
            continue
        try:
            published = _naive_utc(parsedate_to_datetime(when))
        except (TypeError, ValueError):
            continue
        items.append(Item((item.findtext("title") or "").strip(), (item.findtext("link") or "").strip(), source, published))
    return items


def from_feeds(urls: list[str], since: datetime) -> tuple[list[Item], list[str]]:
    """Items newer than `since` from each feed, plus a list of feeds that failed (never fatal)."""
    items: list[Item] = []
    failed: list[str] = []
    for url in urls:
        try:
            items += [i for i in parse_feed(_get(url), url) if i.published >= since]
        except Exception as exc:  # one broken feed must not stop the brief
            failed.append(f"{url}: {exc.__class__.__name__}")
    items.sort(key=lambda i: i.published, reverse=True)
    return items, failed


def pick(items: list[Item], topics: list[str], limit: int = 2) -> list[Item]:
    """Prefer items that mention one of your topics, one per source, then fill with the newest."""
    chosen: list[Item] = []
    seen_sources: set[str] = set()
    lowered = [t.lower() for t in topics]
    for item in items:
        if len(chosen) >= limit:
            break
        if any(t in item.title.lower() for t in lowered) and item.source not in seen_sources:
            chosen.append(item)
            seen_sources.add(item.source)
    for item in items:
        if len(chosen) >= limit:
            break
        if item not in chosen and item.source not in seen_sources:
            chosen.append(item)
            seen_sources.add(item.source)
    return chosen
