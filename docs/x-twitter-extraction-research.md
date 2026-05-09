# X/Twitter Extraction Research

Date: 2026-05-09

## Findings

Plain HTTP fetching of `x.com` post pages is not a sufficient extraction strategy. The first pass produced HTTP 200 pages, but those pages were JavaScript shells without post text. Scrapling supports browser-backed dynamic fetchers for JavaScript-rendered sites, but X's own developer guidance says non-API scraping and browser automation are not an approved route.

The best unauthenticated, official option for individual public post URLs is X's oEmbed endpoint:

- Endpoint: `https://publish.x.com/oembed`
- Authentication: none
- Rate limited: no, according to X's oEmbed documentation
- Output: JSON containing an HTML fallback snippet that can include post text, author, author URL, post link, and date
- Limitations: intended for embedding, not full analytics; may not expose full thread/quote/media/card detail; deleted, protected, age-restricted, or otherwise unavailable posts can fail

The most robust and policy-aligned option is the official X API Post Lookup:

- Endpoint family: `/2/tweets/:id` and `/2/tweets`
- Requires an approved developer account, project/app, and bearer token
- Multiple-post lookup accepts up to 100 post IDs in one request
- Supports fields and expansions for author, created date, public metrics, entities/URLs, media, referenced posts, and more
- It introduces credentials, billing/usage tracking, and policy obligations, so it needs explicit user approval before use

Sandboxed browser rendering is now approved only as a fallback after oEmbed. It must use Playwright-managed Chromium with a fresh project-local profile and no credentials, cookies, storage state, account context, `real_chrome`, or CDP connection to an existing browser. Its purpose is to view public URLs without touching the user's personal browser data. It may still hit login walls or JavaScript shell pages, and those outcomes must be logged honestly.

Undocumented internal GraphQL endpoints, public front ends, session cookies, browser profiles, proxy rotation, and paid third-party scrapers should not be used by default. They are either credentialed, policy-sensitive, brittle, or need separate safety/legal review.

## Recommended Next Goal

Run a new CLI `/goal` that implements an oEmbed-based X parser and stops only when either:

- at least 50% of X/Twitter link rows have real parsed content, or
- the goal writes a blocker explaining why the official unauthenticated oEmbed route cannot reach that threshold.

Use oEmbed first, then sandboxed Playwright-managed Chromium only for URLs that remain unparsed or where browser-visible evidence is needed. Recorded attempts, HTTP 200 shell pages, browser login walls, screenshots without visible post content, and empty parsed text must not count toward the 50% threshold.

## Sources

- X oEmbed API: `https://docs.x.com/x-for-websites/oembed-api`
- X API introduction/pricing model: `https://docs.x.com/x-api/introduction`
- X Post Lookup overview: `https://docs.x.com/x-api/posts/lookup/introduction`
- X Get Posts by IDs: `https://docs.x.com/x-api/posts/get-posts-by-ids`
- X Post Lookup integration guide: `https://docs.x.com/x-api/posts/lookup/integrate`
- X Developer Guidelines: `https://docs.x.com/developer-guidelines`
- Scrapling fetcher selection: `https://scrapling.readthedocs.io/en/latest/fetching/choosing.html`
- Scrapling dynamic fetching: `https://scrapling.readthedocs.io/en/latest/fetching/dynamic.html`
