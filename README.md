# Dawnbrief

A 7am message from Grok Bot that plans your day: today's calendar with free focus time, the overnight email that needs you, news on your topics, your top 3 jobs, and meetings you could skip (declined only if you reply OK).

Dawnbrief has three parts:

1. **A Grok Bot skill and daily routine** (`grok-bot/`). The Bot reads your calendar, email, Slack and news once a morning and sends one message under 1,500 characters. It only reads; it never sends, accepts or declines anything without your OK.
2. **News from two free, open-source tools**: [Miniflux](https://github.com/miniflux/v2) (a feed reader with an API) and [RSSHub](https://github.com/DIYgod/RSSHub) (feeds for sites that don't have one, such as GitHub, YouTube or Hacker News). `server/` has a Docker Compose file for both, and a way to run RSSHub on your own PC without Docker.
3. **`dawnbrief preview`**, which builds the same brief on your own computer from a calendar export, a Gmail Takeout export and your feeds. It changes nothing and sends nothing, so you can see what the Bot will tell you before you give it access.

> **Status:** `dawnbrief preview` is tested (13 tests, plus a real run against five live feeds, three of them through RSSHub running locally). The Grok Bot skill and routine are **not yet tested on Grok Bot**, because we don't have a plan to test on. The Docker Compose file is **not yet run** (the build PC had no Docker). If you run any of them, please open an issue with what happened.

Built for [RepoQuarry](https://repoquarry.dev), which lists open-source parts and step-by-step builds you can hand to an AI agent.

## What it costs

- Grok Bot comes with X Premium ($30/month) or higher, and shares one weekly allowance with Cursor and the Grok apps. Dawnbrief runs once a day and caps itself at a short brief; if the allowance passes 70%, it sends calendar and top 3 only.
- Miniflux and RSSHub are free. Self-hosting them for the Bot needs a small server with a public HTTPS address (Grok Bot runs on its own cloud computer and can't see your PC). For the preview on your PC, nothing extra is needed.
- `dawnbrief preview` needs Python 3.10 or later and no packages.

## Try the preview

```bash
python -m dawnbrief sample demo
python -m dawnbrief preview --ics demo/today.ics --mbox demo/overnight.mbox --me alex@example.com --now 2026-10-26T07:00 --html demo/brief.html
```

That's a made-up Monday: six meetings, 38 overnight emails (4 that need you, 34 you can ignore). The brief ranks the quote that's due "by 10am" first, finds focus time from 11:00 to 12:30 and 13:00 to 14:00, and suggests skipping a 42-person all-hands where you're optional and an 11-person status sync with no agenda, which frees 1 h 45 min.

On your own data:

1. **Calendar:** in Google Calendar, Settings > Import & export > Export, and unzip the `.ics` file.
2. **Email:** at [Google Takeout](https://takeout.google.com), choose only **Mail**. You get a file ending `.mbox`.
3. **News:** list feed URLs in a text file, one per line, or point at your Miniflux with `--miniflux http://localhost:8080` and the API key in the `MINIFLUX_TOKEN` environment variable (Miniflux: Settings > API Keys).
4. Run `python -m dawnbrief preview --ics calendar.ics --mbox "All mail Including Spam and Trash.mbox" --feeds feeds.txt --topics "ai,pricing" --me you@example.com --html brief.html`.

## RSSHub without Docker

```bash
cd server/rsshub-npm
npm install
npm start          # RSSHub routes on http://localhost:1200, e.g. /github/repos/miniflux or /bbc/technology
```

This uses RSSHub's official npm package. On Windows, every route failed with "No headers based on this input can be generated" until a fixed user agent was set; `serve.mjs` sets one for you.

## The rules

| Part | Rule |
|---|---|
| Overnight | Since 18:00 yesterday (change with `--overnight-from`). |
| Can ignore | Mailing lists (List-Unsubscribe or List-Id), no-reply senders, and Gmail's Promotions, Social, Updates and Forums tabs. |
| Needs you | Scored: +3 asks something or has a deadline, +2 due today, +2 marked Important or starred, +2 from someone you deal with. Top 3 shown. |
| Focus time | Gaps of 60 minutes or more between 09:00 and 17:30. |
| Could skip | You're optional and 6+ are invited, or recurring with no agenda and 8+ people. Decline drafts are written, never sent. |
| News | Newest items since last evening, preferring your topics and one per source. Two by default. |

## Credits

The morning brief is the most common Grok Bot use case in xAI's own gallery and community lists, and appears as "Custom Morning Brief" in [awesome-openclaw-usecases](https://github.com/hesamsheikh/awesome-openclaw-usecases). Miniflux (Apache-2.0) and RSSHub (AGPL-3.0) are separate projects, not involved with this one.

## Licence

MIT, except `server/rsshub-npm/`, which runs RSSHub and is offered under AGPL-3.0 to match it.
