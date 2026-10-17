# Adapter: visual-terminal

The visual-terminal adapter fills the visual port for CLIs, libraries, and services that
have no screen. The adapter shows the change in a terminal.

- **script**: use `"kind": "terminal"`. Each step has `"run"`: a shell command that runs
  from the project root. The output of the command appears under the command, as in a
  real terminal. For a library, run a one-line script that calls the interface, for
  example
  `node -e "import('./src/greet.js').then(m => console.log(m.greet('Ana', 'es')))"`.
  Make every command print something, because the recorder fails a command that prints
  nothing. Set `"unchanged": true` only if the acceptance line says that the command
  prints nothing.
- **record**: run `node pdlc/bin/record_gif.mjs <visual.json> <change folder>`.
