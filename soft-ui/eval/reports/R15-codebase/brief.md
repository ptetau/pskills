# R15 · Structure of the "atlas" codebase

`files.csv` holds each source file of the "atlas" monorepo: its path, language, lines
of code, and the number of commits that touched it in the last 90 days. `imports.csv`
holds the import edges between top-level modules, with the count of import statements.

Reader: the tech lead who plans a refactor. They need to see where the code is (which
modules are big), how the modules depend on each other (and any cycles), and which big
files also change often.
