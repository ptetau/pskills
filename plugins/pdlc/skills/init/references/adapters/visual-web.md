# Adapter: visual-web

Fills the visual port for web apps, in a real browser.

- **script**: `"kind": "web"`. Set `"start"` and `"base_url"` from "Visual" in
  `pdlc/config.md`, so the recorder starts the app and waits for it. Steps use `goto`,
  `click`, `type` (selector and text), `press` (a key) and `wait` (milliseconds). Take
  selectors from the change spec's "Interface". After a click, typing or a key press,
  the recorder waits for the page to change and settle. If the page doesn't change, the
  recorder fails the step. Set `"unchanged": true` only if the acceptance line says
  nothing changes.
- **record**: `node pdlc/bin/record_gif.mjs <visual.json> <change folder>`. When the
  recorder is done, it stops the app.
