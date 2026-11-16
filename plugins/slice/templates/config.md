# slice config

- stack: <language, framework, and test library, as ratified in the spec interview>
- test command: `<one command that runs all tests and prints one result for each test>`
- result format: <unittest | junit>
- tests folder: `tests`
- source folders: `src`

A `junit` command writes its report to `{junit}`, for example `pytest --junitxml={junit}`.
A `unittest` command prints verbose lines, for example `python3 -m unittest discover -s tests -v`.
Each test name holds the ID of its slice, for example `test_S1_counts_words`.
