# slice config

- stack: <language, framework, and test library, as ratified in the spec interview>
- test command: `<one command that runs all tests and prints one result for each test>`
- result format: <unittest | junit>
- tests folder: `tests`
- source folders: `src`
- source files: none

A `junit` command writes its report to `{junit}`, for example `pytest --junitxml={junit}`.
A `unittest` command prints verbose lines, for example `python3 -m unittest discover -s tests -v`.
Each test name holds the spec number, the ID of its slice, and the requirement: `test_NNN_Sn_Rn_<what>`, for example `test_002_S1_R2_counts_words`.
`source files` is optional: single paths and globs outside the source folders that a slice can write, for example `package.json`, `migrations/**`. A source file path is relative to the project root. `*` stays in one folder and `**` crosses folders. A path in the tests folder or in `slice/` is not a source file.
