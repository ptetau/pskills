# Adapter: visual-web

Fills the visual port for web apps, in a real browser.

- **script**: `"kind": "web"`. Set `"start"` and `"base_url"` from "Visual" in
  `pdlc/config.md`, so the recorder starts the app and waits for it. Steps use `goto`,
  `click`, `type` (selector and text), `press` (a key) and `wait` (milliseconds). Take
  selectors from the change spec's "Interface". Add a short `wait` after actions that
  change the page.
- **record**: `node pdlc/bin/record_gif.mjs <visual.json> <change folder>`. The recorder
  stops the app when it is done.
