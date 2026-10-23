# Build log

- Start: 2026-10-23 20:00 (Europe/London)
- Agent: Claude Code (Opus 5.5)
- Grok Bot plan: none, so the skill and routine are written but not yet tested on Grok Bot.
- Parts checked 2026-10-23: Miniflux (miniflux/v2, Apache-2.0, last commit 21 Oct, not archived), RSSHub (DIYgod/RSSHub, AGPL-3.0, last commit 23 Oct, not archived). Both allow commercial use.
- Build PC had no Docker and no Go, so Miniflux itself was not run. Its API client is tested against a stand-in server that follows the GET /v1/entries request and response in https://miniflux.app/docs/api.html.
- RSSHub run locally from its npm package (1.0.0-master.3c11932). Every route failed with "No headers based on this input can be generated" until a fixed user agent was set; then /hackernews/best returned 30 items, /github/repos/miniflux 7 and /bbc/technology 21.
- `dawnbrief preview` done: 13 tests pass. Sample Monday (6 meetings, 38 overnight emails) builds a 973-character brief.
- Real run: 5 live feeds (3 through local RSSHub, 2 public) plus the sample calendar and inbox, 8.1 s, 1,156 characters, no failed feeds.
- Code done: 2026-10-23 20:08
- Guide, cover and brief images, glass-look 16:9 and 9:16 videos (voice transcribes back, -14.0 LUFS), 6 Instagram slides and posts done: 2026-10-23 20:32
- Total build time: 20:00 to 20:32
- Repo: local only, waiting for the owner's OK to publish as Obiwayne/dawnbrief.
