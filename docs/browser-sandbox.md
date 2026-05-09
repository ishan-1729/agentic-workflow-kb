# Browser Sandbox

This project may use a browser only when explicitly approved for a bounded task.

## Installed Browser

Playwright-managed Chromium has been installed through:

```powershell
uv run --no-cache python -B -m playwright install chromium
```

This installs Playwright's own browser binaries. It does not use the user's personal Chrome, Edge, Brave, Firefox, or their profiles.

## Required Rules

- Use `uv` for all Python/Playwright commands.
- Use Playwright-managed Chromium only.
- Create a fresh project-local profile for each run, for example `data/browser_sandbox/goal-003-20260509T120000Z/`.
- Do not import cookies, storage state, session files, browser profiles, or account credentials.
- For persistent contexts, isolation comes from a brand-new `user_data_dir`; do not pass or load any storage-state file.
- Do not use `real_chrome`.
- Do not connect to an existing browser through CDP.
- Do not log in.
- Do not bypass CAPTCHA, anti-bot, or login walls.
- Store only bounded evidence needed for the task, such as screenshots, HTML snapshots, parsed text, URL, status, and error reason.

## X/Twitter Use

For X/Twitter, oEmbed remains the primary extraction method. The sandboxed browser is only a fallback for oEmbed failures or verification of public page visibility. Browser-visible public content may count as parsed content only when the post text or equivalent factual content is actually visible and captured. Login walls, empty pages, JavaScript shells, and screenshots without visible post content do not count.
