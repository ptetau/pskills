#!/usr/bin/env python3
"""Tests for fingerprint.py. Run: python3 test_fingerprint.py"""

import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fingerprint  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class FingerprintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = os.path.realpath(self.tmp.name)
        self.skill = os.path.join(self.base, "alpha", "SKILL.md")
        write(self.skill, "skill text\n")
        write(os.path.join(self.base, "alpha", "references", "a.md"), "A\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_skill_hash_is_sha256_of_file(self):
        fp = fingerprint.fingerprint(self.skill)
        self.assertEqual(fp["skillSha256"], hashlib.sha256(b"skill text\n").hexdigest())
        self.assertNotIn("workflowSha256", fp)

    def test_workflow_hash(self):
        wf = os.path.join(self.base, "wf.js")
        write(wf, "run()\n")
        fp = fingerprint.fingerprint(self.skill, wf)
        self.assertEqual(fp["workflowSha256"], hashlib.sha256(b"run()\n").hexdigest())

    def test_tree_hash_changes_with_reference_file(self):
        before = fingerprint.fingerprint(self.skill)
        write(os.path.join(self.base, "alpha", "references", "a.md"), "B\n")
        after = fingerprint.fingerprint(self.skill)
        self.assertEqual(before["skillSha256"], after["skillSha256"])
        self.assertNotEqual(before["skillTreeSha256"], after["skillTreeSha256"])

    def test_tree_hash_changes_with_new_file_and_rename(self):
        before = fingerprint.fingerprint(self.skill)["skillTreeSha256"]
        write(os.path.join(self.base, "alpha", "new.txt"), "x")
        added = fingerprint.fingerprint(self.skill)["skillTreeSha256"]
        self.assertNotEqual(before, added)
        os.rename(os.path.join(self.base, "alpha", "new.txt"), os.path.join(self.base, "alpha", "other.txt"))
        self.assertNotEqual(added, fingerprint.fingerprint(self.skill)["skillTreeSha256"])

    def test_skips_pycache_git_and_pyc(self):
        before = fingerprint.fingerprint(self.skill)["skillTreeSha256"]
        write(os.path.join(self.base, "alpha", "__pycache__", "x.cpython-311.pyc"), "1")
        write(os.path.join(self.base, "alpha", ".git", "HEAD"), "ref")
        write(os.path.join(self.base, "alpha", "scripts", "m.pyc"), "2")
        self.assertEqual(before, fingerprint.fingerprint(self.skill)["skillTreeSha256"])

    def test_tree_hash_is_stable_and_sorted(self):
        a = fingerprint.fingerprint(self.skill)["skillTreeSha256"]
        self.assertEqual(a, fingerprint.fingerprint(self.skill)["skillTreeSha256"])
        entries = fingerprint.tree_entries(os.path.join(self.base, "alpha"))
        self.assertEqual(entries, sorted(entries))

    def test_skill_folder_is_root_outside_a_plugin(self):
        self.assertEqual(fingerprint.tree_root(self.skill), os.path.join(self.base, "alpha"))
        # A skills folder without a plugin manifest is not a plugin.
        loose = os.path.join(self.base, "proj", "skills", "beta", "SKILL.md")
        write(loose, "b")
        self.assertEqual(fingerprint.tree_root(loose), os.path.dirname(loose))

    def test_plugin_folder_is_root_inside_a_plugin(self):
        plugin = os.path.join(self.base, "plug")
        skill = os.path.join(plugin, "skills", "one", "SKILL.md")
        write(skill, "one")
        write(os.path.join(plugin, ".claude-plugin", "plugin.json"), "{}")
        write(os.path.join(plugin, "agents", "x.md"), "agent")
        self.assertEqual(fingerprint.tree_root(skill), plugin)
        before = fingerprint.fingerprint(skill)["skillTreeSha256"]
        write(os.path.join(plugin, "agents", "x.md"), "agent changed")
        self.assertNotEqual(before, fingerprint.fingerprint(skill)["skillTreeSha256"])

    def test_order_of_writing_does_not_change_hash(self):
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        root2 = os.path.realpath(other.name)
        names = ["z.md", "m.md", "a.md"]
        skill1 = os.path.join(self.base, "ord1", "SKILL.md")
        skill2 = os.path.join(root2, "ord2", "SKILL.md")
        write(skill1, "s")
        write(skill2, "s")
        for n in names:
            write(os.path.join(self.base, "ord1", n), n)
        for n in reversed(names):
            write(os.path.join(root2, "ord2", n), n)
        e = fingerprint.tree_entries(os.path.join(self.base, "ord1"))
        self.assertEqual([r for r, _ in e], ["SKILL.md", "a.md", "m.md", "z.md"])
        self.assertEqual(fingerprint.fingerprint(skill1)["skillTreeSha256"],
                         fingerprint.fingerprint(skill2)["skillTreeSha256"])

    def test_nested_paths_are_sorted(self):
        write(os.path.join(self.base, "alpha", "z", "1.md"), "1")
        write(os.path.join(self.base, "alpha", "b", "2.md"), "2")
        rels = [r for r, _ in fingerprint.tree_entries(os.path.join(self.base, "alpha"))]
        self.assertEqual(rels, sorted(rels))
        self.assertLess(rels.index("b/2.md"), rels.index("z/1.md"))

    def test_skill_not_under_skills_folder_uses_skill_folder(self):
        plug = os.path.join(self.base, "plug2")
        write(os.path.join(plug, ".claude-plugin", "plugin.json"), "{}")
        skill = os.path.join(plug, "other", "x", "SKILL.md")
        write(skill, "x")
        self.assertEqual(fingerprint.tree_root(skill), os.path.dirname(skill))

    def test_repo_root_tree_ignores_run_output(self):
        plug = os.path.join(self.base, "rootplug")
        skill = os.path.join(plug, "skills", "one", "SKILL.md")
        write(skill, "one")
        write(os.path.join(plug, ".claude-plugin", "plugin.json"), "{}")
        before = fingerprint.fingerprint(skill)["skillTreeSha256"]
        write(os.path.join(plug, "evals", "x", "runs", "1", "results.json"), "{}")
        write(os.path.join(plug, ".claude", "worktrees", "a", ".vet-tmp", "n"), "n")
        write(os.path.join(plug, ".vet-capture", "c"), "c")
        write(os.path.join(plug, "node_modules", "m", "i.js"), "m")
        write(os.path.join(plug, ".DS_Store"), "d")
        write(os.path.join(plug, "skills", "one", ".git"), "gitdir: x")
        self.assertEqual(before, fingerprint.fingerprint(skill)["skillTreeSha256"])

    def test_skill_tree_is_relative_inside_a_repo(self):
        here = os.path.dirname(os.path.abspath(__file__))
        fp = fingerprint.fingerprint(os.path.join(here, "..", "SKILL.md"))
        self.assertEqual(fp["skillTree"], "vet")


if __name__ == "__main__":
    unittest.main()
