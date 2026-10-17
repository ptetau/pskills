# Adapter: visual-web

The visual-web adapter fills the visual port for web apps, in a real browser.

- **script**: use `"kind": "web"`. Set `"start"` and `"base_url"` from the "Visual"
  section of `pdlc/config.md`. Then the recorder starts the app and waits for the app.
  The steps use `goto`, `click`, `type` (selector and text), `press` (a key), and `wait`
  (milliseconds). Get the selectors from the "Interface" section of the change spec.
  After each action that changes the page, add a short `wait`.
- **record**: run `node pdlc/bin/record_gif.mjs <visual.json> <change folder>`. At the
  end, the recorder stops the app.
