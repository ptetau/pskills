# slice config

- stack: <language, framework, and test library, as ratified in the spec interview>
- test command: `<one command that runs all acceptance tests and prints one result for each test>`
- result format: <unittest | junit>
- tests folder: `tests`
- unit tests folder: none
- unit test command: none
- source folders: `src`
- source files: none
- boundary files: none
- security scan: none

A `junit` command writes its report to `{junit}`, for example `pytest --junitxml={junit}`.
A `unittest` command prints verbose lines, for example `python3 -m unittest discover -s tests -v`.
Each acceptance test name holds the spec number, the ID of its slice, and the requirement: `test_NNN_Sn_Rn_<what>`, for example `test_002_S1_R2_counts_words`.
`unit tests folder` is optional: a separate folder where the implementer can write and run unit tests (outside `tests folder`). `unit test command` is optional: one command for the unit tests; when `none`, the implementer can still run a runner scoped to `unit tests folder`.
`boundary files` is optional: single paths and globs of public interface files that `test-writer` may read (read-only) while internal app code stays hidden.
`security scan` is optional: one command that scans the code and exits non-zero on a finding, for example `bandit -q -r src`, `semgrep --error --config auto src`, or `npm audit --audit-level=high`. `none` means no scan. `slice.py scan` runs it, and `slice.py commit Sn` refuses when it fails.
`source files` is optional: single paths and globs outside the source folders that a slice can write, for example `package.json`, `migrations/**`. A source file path is relative to the project root. `*` stays in one folder and `**` crosses folders. A path in the tests folder, unit tests folder, or in `slice/` is not a source file.
