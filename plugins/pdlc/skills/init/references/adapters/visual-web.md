# Adapter: visual-web

The visual-web adapter fills the visual port for web apps, in a real browser.

- **script**: use `"kind": "web"`. Set `"start"` and `"base_url"` from "Visual"
  in `pdlc/config.md`, so that the recorder starts the app and waits for the app.
  The steps use `goto`, `click`, `type` (selector and text), `press` (a key), and `wait`
  (milliseconds). Get the selectors from the "Interface" section of the change spec.
  - After a `click`, `type`, or `press` step, the recorder waits for the page to change
    and settle. The recorder fails the step if the page does not change.
  - Set `"unchanged": true` only if the acceptance line says that nothing changes.
  - A `run` step shows a command and its output in a terminal, in a second tab. Use it for
    what a page cannot show, for example a status code, a header, or a redirect.
    For example, `curl -si {base_url}/items -d text=milk` shows the 303 and its `Location`.
    In a command, `{base_url}` stands for `base_url`. The page keeps its state for the next
    web step.
- **record**: run `node pdlc/bin/record_gif.mjs <visual.json> <change folder>`. At the
  end, the recorder stops the app.
