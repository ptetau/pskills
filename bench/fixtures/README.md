# The to-do web apps

Each folder here is the same small to-do list web app in a different language. pdlc runs on
each app with the same intent. The bench checks each result with the same HTTP probes.
Thus, the results of the languages compare directly.

| Folder | Language | Status |
|---|---|---|
| `todo-rust` | Rust, standard library only | Ready |
| `todo-clojure` | Clojure 1.11 (the Ubuntu package), with the Java standard library | Ready |
| `todo-lean` | Lean 4 | Not written yet: the session blocks the Lean installer, and Ubuntu has no package |

## The app

Each app has the same behaviour, and its README says so in the same words.

- `GET /` shows the page: a heading, the list, and a form that adds an item. With no items,
  the page says "Nothing to do."
- `POST /items` with the form field `text` adds an item, and answers 303 to `/`. Empty text
  answers 400 with `error: text is empty`.
- Any other request answers 404 with `error: not found`.
- `PORT` sets the port, and `DATA_FILE` sets the file of the items. The data file has one
  item on each line: the id, a tab, and the text.

The code has a part for the storage of the items, and a part for the page. Thus, init maps
a capability (the item storage) and a job (the page).

## The intent

`TODO_INTENT` in `bench/run_bench.py` asks for a "done" mark. The intent needs two changes:

1. The storage keeps a done flag that stays after a restart. An old data file still loads.
2. The page gets a Done button for each open item, hides done items, and links to
   `/?show=all`.

## The probes

`todo_probes` in `bench/run_bench.py` builds the app, and starts it on a free port with its
own data file. Then it sends 8 groups of requests, and reads the page as a user reads it,
with no tags. The base app passes only the probe of the old behaviour. The reference
solution of each app, in `solutions/`, passes all 8. `bench/test_bench.py` tests both.

## Run

```
python3 bench/run_bench.py init-fixture --fixture todo-rust
python3 bench/run_bench.py e2e --fixture todo-rust --label todo-rust --runs 1 --out <folder>
```

`init-fixture` runs `/pdlc:init defaults` on a copy of the app. Its `pdlc/` folder then goes
into the folder of the app, as for `bench/fixture-app`.

## Keep a fixture up to date

A fixture keeps only the specs, `config.md`, and `version.json` in its `pdlc/` folder. The
bench adds the other pdlc files at each run, with `upgrade.py` of the plugin under test.
`version.json` lists the hash of each file that pdlc wrote. Thus the upgrade sees each default
spec of the fixture as unedited, and refreshes it. To bring a fixture up to the current plugin:

1. Copy the fixture to a temporary folder, run `git init`, and commit it as "Set up pdlc".
2. Run `python3 plugins/pdlc/skills/upgrade/scripts/upgrade.py plan` in the copy. Read the diff
   of each file that it calls `edited`. If the diff shows only plugin text, run `apply
   --no-intent --no-commit --take pdlc/<path>` for that file. If it shows a rule of the fixture,
   keep the file.
3. Copy `pdlc/specs/design/*` and `pdlc/version.json` back into the fixture.

The fixtures keep no "Interface" section in their job and capability specs. The upgrade only
reports them. Intake adds each section that it needs.

`rebuild` tests rule 10 (the specs can rebuild the project). It takes the project that an `e2e`
run left, and keeps only the specs and the config. A builder with no plugin then writes the app
again from these files. The bench runs the original acceptance checks and the probes on the new
app. The verdict is `holds`, `broken`, or `invalid` (the builder read the original).

```
python3 bench/run_bench.py rebuild <folder>/todo-rust --budget 5
```

## Add a language

1. Write the app in a new folder `todo-<language>`, with the behaviour above and its own
   checks. Keep the storage and the page in separate files.
2. Add an entry to `FIXTURES` in `bench/run_bench.py`. It gives these items:
   - The commands that build the app, start the app, and run its checks.
   - A pattern for the count of checks.
   - The Bash commands that pdlc needs.
3. Write a reference solution, and check that it passes all 8 probes.
4. Run `init-fixture`, and keep its `pdlc/` folder.
