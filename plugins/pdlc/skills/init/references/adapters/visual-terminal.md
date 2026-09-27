# Adapter: visual-terminal

Fills the visual port for CLIs, libraries and services without a screen, as a terminal.

- **script**: `"kind": "terminal"`. Each step has `"run"`: a shell command, run from the
  project root. Its output appears under the command, like a real terminal. For a library,
  run a one-line script that calls the interface, for example
  `node -e "import('./src/greet.js').then(m => console.log(m.greet('Ana', 'es')))"`.
- **record**: `node pdlc/bin/record_gif.mjs <visual.json> <change folder>`.
