# Adapter: visual-terminal

Fills the visual port for CLIs, libraries and services without a screen, as a terminal.

- **script**: `"kind": "terminal"`. Each step has `"run"`: a shell command, run from the
  project root. The command's output appears under it, as in a real terminal. For a
  library, run a one-line script that calls the interface, for example
  `node -e "import('./src/greet.js').then(m => console.log(m.greet('Ana', 'es')))"`.
  Make every command print something. The recorder fails a command that prints nothing.
  Set `"unchanged": true` only if the acceptance line says the command prints nothing.
- **record**: `node pdlc/bin/record_gif.mjs <visual.json> <change folder>`.
