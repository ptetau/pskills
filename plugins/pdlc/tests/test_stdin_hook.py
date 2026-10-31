"""Tests for pdlc's stdin check hook. Run: python3 -m unittest discover plugins/pdlc/tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).parent.parent
HOOK = PLUGIN / "hooks/stdin.py"


class StdinHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.root = Path(self.tmp.name)
        (r / "pdlc").mkdir()
        (r / "pdlc/config.md").write_text("# pdlc config\n")

    def tearDown(self):
        self.tmp.cleanup()

    def hook(self, command, tool="Bash", cwd=None):
        call = {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(cwd or self.root)}
        run = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(call),
                             capture_output=True, text=True, timeout=30)
        return run.returncode, run.stderr

    def blocked(self, command):
        code, err = self.hook(command)
        self.assertEqual(code, 2, "%r should be blocked" % command)
        self.assertIn("reads standard input", err)

    def allowed(self, command):
        self.assertEqual(self.hook(command), (0, ""), "%r should be allowed" % command)

    # Blocked: a command that reads standard input and gets none

    def test_cat_into_a_file_with_no_input_is_blocked(self):
        code, err = self.hook("cat > $TMPDIR/ed.sh")
        self.assertEqual(code, 2)
        self.assertIn("pdlc: `cat` reads standard input", err)
        self.assertIn("Write tool", err)
        self.assertIn("cat > FILE <<'EOF'", err)

    def test_cat_appending_with_no_input_is_blocked(self):
        self.blocked("cat >> notes.md")

    def test_the_saved_command_of_the_hung_run_is_blocked(self):
        self.blocked("cat > $TMPDIR/ed.sh 2>/dev/null || true")

    def test_a_bare_reader_is_blocked(self):
        for command in ("cat", "cat -n", "cat - > f", "cat -- > f", "tee out", "python3", "python3 -",
                        "python", "python3.12 -u -", "node", "node -", "X=$(cat)", "echo `cat`"):
            with self.subTest(command=command):
                self.blocked(command)

    def test_the_message_names_the_command(self):
        code, err = self.hook("tee -a out")
        self.assertEqual(code, 2)
        self.assertIn("`tee -a out` reads", err)

    def test_a_reader_after_other_commands_is_blocked(self):
        for command in ("cd a && cat > f", "echo x; cat > f", "echo x\ncat > f", "false || cat > f",
                        "sleep 1 & cat > f", "echo x | tee a | cat > f; cat > g"):
            with self.subTest(command=command):
                self.blocked(command)

    def test_a_reader_in_a_group_or_behind_a_wrapper_is_blocked(self):
        for command in ("for f in a b; do cat > $f; done", "if true; then tee f; fi", "( cat > f )",
                        "timeout 60 cat > f", "timeout -k 5 60 python3", "env A=1 cat > f",
                        "A=1 B=2 cat > f", "time python3", "{ cat > f; }"):
            with self.subTest(command=command):
                self.blocked(command)

    def test_a_reader_after_a_heredoc_ends_is_blocked(self):
        self.blocked("cat > a <<EOF\nx\nEOF\ncat > b")

    # Allowed: the command has input

    def test_a_heredoc_gives_input(self):
        for command in ("cat > f <<'EOF'\nit's a | b; c\nEOF",
                        "cat > f <<EOF\n$(date) \"quoted\n\nEOF",
                        "cat <<-EOF > f\n\tbody\n\tEOF",
                        "cat > f << 'EOF'\nline\nEOF",
                        "python3 - <<'EOF'\nprint(1)\nEOF",
                        "tee f <<\"END\"\nline\nEND",
                        'git commit -m "$(cat <<\'EOF\'\nTitle with "quotes"\n\nBody it\'s here.\nEOF\n)"',
                        "x=$(cat <<'EOF'\nit's\nEOF\n)",
                        "cat > f <<'EOF'\nline\nEOF\nls | wc -l"):
            with self.subTest(command=command):
                self.allowed(command)

    def test_a_heredoc_body_is_not_a_command(self):
        self.allowed("python3 - <<'EOF'\nimport os\nos.system('cat > f')\nEOF")
        self.allowed("cat > notes.md <<'EOF'\ncat > f\ntee out\npython3\nnode\nEOF")
        self.allowed("git commit -m \"$(cat <<'EOF'\nSay \"hi\nthere\ncat > x\" ok\nEOF\n)\"")

    def test_a_pipe_gives_input(self):
        for command in ("echo x | cat > f", "git log | tee l", "printf a | python3 -", "echo x |& cat",
                        "echo x | node -", "ls\necho x |\ncat > f"):
            with self.subTest(command=command):
                self.allowed(command)

    def test_a_redirect_gives_input(self):
        for command in ("cat < a > b", 'cat <<< "t" > f', "cat < <(echo hi)", "tee f < a", "python3 < s.py",
                        "cat > f < /dev/null", "cat 2>/dev/null <a"):
            with self.subTest(command=command):
                self.allowed(command)

    def test_a_group_that_gets_input_is_allowed(self):
        for command in ("while read l; do cat; done < list", "{ cat > f; } < a", "( cat > f ) < a",
                        "echo x | { echo y; cat > f; }", "echo x | (cat > f)",
                        "echo x | while read l; do cat > f; done"):
            with self.subTest(command=command):
                self.allowed(command)

    def test_a_redirect_after_a_substitution_does_not_cover_other_commands(self):
        self.blocked("d=$(pwd); cat > f; python3 - < s.py")

    # Allowed: the command is not a reader

    def test_operands_and_scripts_are_allowed(self):
        for command in ("cat a b > c", "cat -n a", "cat -- -f", "python3 -c 'print(1)'",
                        "python3 -m unittest discover -s tests", "python3 pdlc/bin/steps.py lock IN-0001",
                        "python3 script.py -", "node pdlc/bin/record_gif.mjs a b", "node --test tests/x.js",
                        "python3 --version", "node -e 'console.log(1)'"):
            with self.subTest(command=command):
                self.allowed(command)

    def test_the_output_of_a_substitution_is_an_operand(self):
        for command in ('cat $(git ls-files)', 'cat "$(ls)"', "cat <(echo hi)", "cat `ls`"):
            with self.subTest(command=command):
                self.allowed(command)

    def test_words_in_quotes_are_not_commands(self):
        for command in ('echo "cat > x"', "echo 'tee out'", "grep -n cat f", "echo ';' cat",
                        'echo "a $(echo "b; cat > x") c"', "git log --grep=python3", "ls node_modules"):
            with self.subTest(command=command):
                self.allowed(command)

    def test_a_comment_is_not_a_command(self):
        self.allowed("# cat > f is the old way\nls")
        self.allowed("ls # cat > f")

    # What it leaves alone

    def test_outside_a_pdlc_project_nothing_is_blocked(self):
        (self.root / "pdlc/config.md").unlink()
        self.allowed("cat > f")

    def test_a_subfolder_of_the_project_is_in_the_project(self):
        sub = self.root / "src/deep"
        sub.mkdir(parents=True)
        code, err = self.hook("cat > f", cwd=sub)
        self.assertEqual(code, 2)

    def test_other_tools_are_not_checked(self):
        for tool in ("Write", "Read", "Edit", "Grep"):
            with self.subTest(tool=tool):
                self.assertEqual(self.hook("cat > f", tool=tool), (0, ""))

    def test_a_command_that_cannot_be_parsed_is_allowed(self):
        for command in ("cat > f 'open quote", 'cat > f "open quote', "cat > f $(", "cat > f $'open",
                        "cat > f `open"):
            with self.subTest(command=command):
                self.allowed(command)

    def test_input_that_is_not_a_tool_call_is_allowed(self):
        for text in ("", "not json", "[]", '"cat"', '{"tool_name": "Bash"}',
                     '{"tool_name": "Bash", "tool_input": {"command": 5}}'):
            with self.subTest(text=text):
                run = subprocess.run([sys.executable, str(HOOK)], input=text, capture_output=True,
                                     text=True, timeout=30)
                self.assertEqual((run.returncode, run.stderr), (0, ""))

    # Configuration

    def test_hooks_json_runs_the_hook_before_bash(self):
        hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text())["hooks"]
        before = [h for entry in hooks.get("PreToolUse", []) if entry["matcher"] == "Bash"
                  for h in entry["hooks"]]
        self.assertTrue(any("hooks/stdin.py" in h["command"] for h in before))
        self.assertTrue((PLUGIN / "hooks/stdin.py").is_file())

    def test_the_guard_still_covers_the_file_tools(self):
        hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text())["hooks"]
        guard = [entry for entry in hooks["PreToolUse"]
                 if any("hooks/guard.py" in h["command"] for h in entry["hooks"])]
        self.assertEqual(len(guard), 1)
        self.assertNotIn("Bash", guard[0]["matcher"])


if __name__ == "__main__":
    unittest.main()
