"""Tests for contracts.json: every hand-off between the prompts and the scripts is in the table,
and each prompt follows the form (A1: Goal, Inputs, Outputs, Constraints, Done when)."""
import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
TABLE = json.loads((PLUGIN / "contracts.json").read_text())
SKILLS = sorted(p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md"))
AGENTS = sorted(p.stem for p in (PLUGIN / "agents").glob("*.md"))
SCRIPTS = {"slice.py": PLUGIN / "bin/slice.py", "guard": PLUGIN / "hooks/guard.py"}
SECTIONS = ["Goal", "Inputs", "Outputs", "Constraints", "Done when"]


def prompts():
    for name in SKILLS:
        yield "skill " + name, name, PLUGIN / "skills" / name / "SKILL.md"
    for name in AGENTS:
        yield "agent " + name, name, PLUGIN / "agents" / (name + ".md")


def section(text, name):
    m = re.search(r"^## %s\n(.*?)(?=^## |\Z)" % re.escape(name), text, re.M | re.S)
    return m.group(1) if m else ""


def md_names(text):
    """The markdown file names that a prompt uses as records or templates."""
    text = re.sub(r"\$\{CLAUDE_PLUGIN_ROOT\}/templates/\w+\.md", "", text)
    return set(re.findall(r"(?<![\w/.-])((?:slice/)?(?:NNN-<name>/)?(?:review/)?[\w<>-]+\.md)\b", text)) - {"SKILL.md"}


def key_of(name):
    """The table key of a file name as a prompt writes it."""
    base = name.split("/")[-1]
    return "review/Sn.md" if base in ("Sn.md", "<Sn>.md") or "review/" in name else base


def files_by_base():
    return {"review/Sn.md" if "/review/" in k else k.split("/")[-1]: k for k in TABLE["files"]}


class Table(unittest.TestCase):
    def test_every_entry_has_a_producer_a_form_and_a_consumer(self):
        known = set(SKILLS) | set(AGENTS) | set(SCRIPTS)
        for path, e in TABLE["files"].items():
            self.assertIn(e["producer"], known, path)
            self.assertTrue(e["form"].strip(), path)
            self.assertTrue(e["consumers"], path)
            for c in e["consumers"]:
                self.assertIn(c, known, "%s: %s" % (path, c))

    def test_the_table_lists_the_subcommands_statuses_and_stages_of_the_script(self):
        script = SCRIPTS["slice.py"].read_text()
        statuses = re.search(r"^STATUSES = (\[.*?\])", script, re.M).group(1)
        self.assertEqual(TABLE["statuses"], json.loads(statuses.replace("'", '"')))
        usage = re.findall(r"slice\.py \[--root DIR\] \[--spec NNN\|NAME\] (\w+)", script, re.M)
        self.assertEqual(sorted(set(usage)), sorted(TABLE["subcommands"]))
        self.assertEqual(TABLE["stages"], ["spec", "plan", "domain", "interface", "build"])
        for stage in TABLE["stages"]:
            self.assertIn(stage, SKILLS)

    def test_the_fields_are_in_the_templates(self):
        for path, e in TABLE["files"].items():
            template = e.get("template")
            for field in e.get("fields", []):
                self.assertIsNotNone(template, path)
                self.assertIn(field, (PLUGIN / "templates" / template).read_text(), "%s: %s" % (path, field))

    def test_a_consumer_that_is_a_script_names_the_file(self):
        for path, e in TABLE["files"].items():
            for c in e["consumers"]:
                if c in SCRIPTS:
                    base = path.split("/")[-1]
                    self.assertIn(base, SCRIPTS[c].read_text(), "%s: %s" % (path, c))

    def test_the_templates_in_the_table_exist(self):
        for path, e in TABLE["files"].items():
            if "template" in e:
                self.assertTrue((PLUGIN / "templates" / e["template"]).is_file(), path)


class Prompts(unittest.TestCase):
    def test_each_prompt_has_the_five_sections_in_order(self):
        for label, _, path in prompts():
            text = path.read_text()
            heads = re.findall(r"^## (.+)$", text, re.M)
            self.assertEqual([h for h in heads if h in SECTIONS], SECTIONS, label)

    def test_each_prompt_has_the_exactly_what_it_reads_constraint(self):
        for label, _, path in prompts():
            self.assertRegex(section(path.read_text(), "Constraints"), r"exactly what", label)

    def test_each_output_names_its_reader(self):
        for label, _, path in prompts():
            items = re.findall(r"^- (.*(?:\n  .*)*)", section(path.read_text(), "Outputs"), re.M)
            self.assertTrue(items, label)
            for item in items:
                if "`slice/" in item or "tests folder" in item or "Stubs" in item or "stubs" in item:
                    self.assertRegex(item, r"[Rr]ead by", "%s: %s" % (label, item[:50]))

    def test_every_file_a_prompt_names_is_in_the_table(self):
        by_base = files_by_base()
        for label, _, path in prompts():
            for name in md_names(path.read_text()):
                self.assertIn(key_of(name), by_base, "%s names %s" % (label, name))

    def test_a_prompt_that_reads_a_file_is_a_consumer_of_it(self):
        by_base = files_by_base()
        for label, name, path in prompts():
            for fname in md_names(section(path.read_text(), "Inputs")):
                entry = TABLE["files"][by_base[key_of(fname)]]
                self.assertIn(name, entry["consumers"], "%s reads %s" % (label, fname))

    def test_a_prompt_that_writes_a_file_is_its_producer(self):
        by_base = files_by_base()
        for label, name, path in prompts():
            for fname in md_names(section(path.read_text(), "Outputs")):
                entry = TABLE["files"][by_base[key_of(fname)]]
                self.assertEqual(entry["producer"], name, "%s writes %s" % (label, fname))

    def test_a_producer_and_each_consumer_name_the_file(self):
        texts = {name: path.read_text() for _, name, path in prompts()}
        for key, e in TABLE["files"].items():
            base = key.split("/")[-1].replace(".md", "")
            for who in [e["producer"]] + e["consumers"]:
                if who in texts:
                    self.assertRegex(texts[who], r"\b%s\b" % re.escape(base) if base != "Sn" else r"review/", "%s: %s" % (key, who))

    def test_the_script_calls_use_known_subcommands_and_statuses(self):
        for label, _, path in prompts():
            text = path.read_text()
            for sub in re.findall(r"slice\.py (?:--\S+ \S+ )*([a-z]+)", text):
                self.assertIn(sub, TABLE["subcommands"], label)
            for status in re.findall(r"slice\.py set <Sn> (\w+)", text):
                self.assertIn(status, TABLE["statuses"], label)
            for kind in re.findall(r"slice\.py round <Sn> (\w+)", text):
                self.assertIn(kind, ("test", "review"), label)

    def test_the_slash_commands_name_a_skill_of_the_plugin(self):
        for label, _, path in prompts():
            for cmd in re.findall(r"/slice:(\w+)", path.read_text()):
                self.assertIn(cmd, SKILLS, label)
            self.assertNotRegex(path.read_text(), r"`/quiz`|/quiz\b", label)

    def test_the_templates_a_prompt_names_exist(self):
        for label, _, path in prompts():
            for t in re.findall(r"templates/(\w+\.md)", path.read_text()):
                self.assertTrue((PLUGIN / "templates" / t).is_file(), "%s: %s" % (label, t))

    def test_the_numbered_spec_folder_is_the_only_home_of_the_spec_records(self):
        for label, _, path in prompts():
            self.assertNotRegex(path.read_text(), r"`slice/(spec|slices|interface|domain)\.md`", label)


class Rules(unittest.TestCase):
    def read(self, rel):
        return (PLUGIN / rel).read_text()

    def test_the_reviewer_has_the_three_part_remit(self):
        text = self.read("agents/reviewer.md")
        for word in ("requirement", "architecture", "security", "OWASP", "Do not quote or show test code"):
            self.assertIn(word, text)

    def test_the_security_floor_is_in_the_three_prompts(self):
        for rel in ("skills/interface/SKILL.md", "agents/implementer.md", "agents/reviewer.md"):
            self.assertIn("OWASP Top 10", self.read(rel), rel)

    def test_the_spec_skill_recommends_a_stack(self):
        text = self.read("skills/spec/SKILL.md")
        for word in ("stack", "modern", "minimal", "config.md"):
            self.assertIn(word, text)

    def test_the_stubs_raise_the_not_implemented_error(self):
        for rel in ("skills/interface/SKILL.md", "templates/interface.md"):
            self.assertIn("NotImplementedError", self.read(rel), rel)

    def test_the_test_writer_does_not_read_the_stubs(self):
        text = self.read("agents/test-writer.md")
        inputs = section(text, "Inputs")
        self.assertNotRegex(inputs.lower(), r"stubs")
        self.assertNotIn("--red", section(text, "Done when"))
        self.assertIn("source folders", text)

    def test_the_interface_skill_runs_the_red_check_and_commits_the_interface(self):
        text = self.read("skills/interface/SKILL.md")
        self.assertIn("test <Sn> --red", text)
        self.assertIn("commit interface", text)

    def test_the_domain_stage(self):
        text = self.read("skills/domain/SKILL.md")
        for word in ("domain.md", "boundary", "gap", "state machine", "no code"):
            self.assertIn(word, text.lower() if word != "domain.md" else text)
        template = self.read("templates/domain.md")
        for word in ("## Requirement map", "## State machines", "## Bounded contexts", "Not allowed"):
            self.assertIn(word, template)
        self.assertIn("domain", self.read("skills/interface/SKILL.md"))

    def test_numbered_requirements_in_the_templates(self):
        self.assertIn("- R1 ", self.read("templates/spec.md"))
        self.assertIn("- D1 ", self.read("templates/spec.md"))
        self.assertIn("- Requirements: R1", self.read("templates/slices.md"))

    def test_the_test_names_cite_the_requirement(self):
        self.assertRegex(self.read("agents/test-writer.md"), r"test_S1_R\d")


if __name__ == "__main__":
    unittest.main()
