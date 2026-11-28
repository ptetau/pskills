#!/usr/bin/env python3
"""Tests for softui.py. Standard library only; the browser check is skipped (--fast)."""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import softui  # noqa: E402


def compile_yaml(text, base=None):
    return softui.compile_spec(softui.load_yaml(text), Path(base or tempfile.mkdtemp()))


def run(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = softui.main(list(argv))
    return rc, buf.getvalue()


class DataForms(unittest.TestCase):
    def test_csv_text(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  d: |\n    a,b\n    1,x\n    2,y\nlayout: [{table: d}]")
        self.assertEqual(plan["data"]["d"]["rows"], [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])
        self.assertEqual(plan["data"]["d"]["types"]["a"], "num")

    def test_toon_text(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  d: |\n    [2]{a,b}:\n    1,x\n    2,y\nlayout: [{table: d}]")
        self.assertEqual(plan["data"]["d"]["rows"][1], {"a": 2, "b": "y"})

    def test_json_file_and_dates_stay_strings(self):
        d = Path(tempfile.mkdtemp())
        (d / "r.json").write_text('[{"day": "2026-01-02", "n": 3}]')
        ctx, plan = compile_yaml("title: T\ndata: {r: r.json}\nlayout: [{table: r}]", d)
        self.assertEqual(plan["data"]["r"]["types"]["day"], "date")
        ctx, plan = compile_yaml("title: T\ndata:\n  r: [{day: 2026-01-02}]\nlayout: [{table: r}]")
        self.assertEqual(plan["data"]["r"]["rows"][0]["day"], "2026-01-02")

    def test_missing_file_is_an_error(self):
        ctx, _ = compile_yaml("title: T\ndata: {r: nope.json}\nlayout: [{text: hi}]")
        self.assertTrue(any("not found" in e for e in ctx.errors))


class Computed(unittest.TestCase):
    def test_add_columns(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  d:\n    rows: [{a: 2, b: 3}]\n"
                                 "    add: {s: a + b, r: 'round(b / a, 2)', big: \"'yes' if b > 2 else 'no'\"}\nlayout: [{table: d}]")
        self.assertEqual(ctx.errors, [])
        self.assertEqual(plan["data"]["d"]["rows"][0], {"a": 2, "b": 3, "s": 5, "r": 1.5, "big": "yes"})

    def test_add_unknown_column_and_unsafe_call(self):
        ctx, _ = compile_yaml("title: T\ndata:\n  d: {rows: [{after: 1}], add: {x: aftr + 1, y: __import__('os')}}\nlayout: [{table: d}]")
        self.assertTrue(any('did you mean "after"' in e for e in ctx.errors))
        self.assertTrue(any("add.y" in e for e in ctx.errors))


class Repairs(unittest.TestCase):
    def test_typo_component_alias_and_prop(self):
        ctx, plan = compile_yaml("title: T\ndata: {d: [{Name: a, n: 1}]}\nlayout:\n"
                                 "- tabel: {data: d}\n- barchart: {data: d, x_axis: name, y: N}")
        self.assertEqual(ctx.errors, [])
        self.assertEqual([n["c"] for n in plan["layout"]], ["table", "chart"])
        ch = plan["layout"][1]["p"]
        self.assertEqual((ch["kind"], ch["x"], ch["y"]), ("bar", "Name", ["n"]))
        self.assertTrue(all("Next time:" in f for f in ctx.fixes))

    def test_type_field_wins_over_alias_key(self):
        ctx, plan = compile_yaml("title: T\ndata: {d: [{a: 1}]}\nlayout:\n- {type: table, data: d, columns: [a]}")
        self.assertEqual(plan["layout"][0]["c"], "table")
        self.assertEqual(plan["layout"][0]["p"]["cols"], ["a"])

    def test_page_keys_and_stray_components(self):
        ctx, plan = compile_yaml("name: X\ncomponents: [{text: hi}]\ncallout: careful")
        self.assertEqual(plan["title"], "X")
        self.assertEqual([n["c"] for n in plan["layout"]], ["text", "callout"])

    def test_mermaid_header_added(self):
        ctx, plan = compile_yaml("title: T\nlayout:\n- sequence: 'A->>B: hi'")
        self.assertTrue(plan["layout"][0]["p"]["src"].startswith("sequenceDiagram"))

    def test_tone_map_without_column(self):
        ctx, plan = compile_yaml("title: T\ndata: {d: [{sev: high}, {sev: low}]}\nlayout:\n- table: {data: d, tone: {high: bad}}")
        self.assertEqual(plan["layout"][0]["p"]["tone"], {"sev": {"high": "bad"}})

    def test_chart_without_y_counts(self):
        ctx, plan = compile_yaml("title: T\ndata: {d: [{s: a}]}\nlayout:\n- chart: {data: d, x: s}")
        self.assertEqual(plan["layout"][0]["p"]["agg"], "count")

    def test_unknown_column_is_an_error_with_the_list(self):
        ctx, _ = compile_yaml("title: T\ndata: {d: [{alpha: 1}]}\nlayout:\n- table: {data: d, cols: [zzz]}")
        self.assertTrue(any("Columns: alpha" in e for e in ctx.errors))

    def test_unknown_component_is_an_error(self):
        ctx, _ = compile_yaml("title: T\nlayout:\n- wibble: {a: 1}")
        self.assertTrue(any("no component" in e for e in ctx.errors))


class CodeAndDiff(unittest.TestCase):
    def test_parse_patch(self):
        files = softui.parse_patch("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1,2 +1,2 @@\n a\n-b\n+c\n")
        self.assertEqual(files[0]["new"], "x.py")
        self.assertEqual((files[0]["add"], files[0]["del"]), (1, 1))
        self.assertEqual(files[0]["hunks"][0]["lines"][1], ["d", 2, None, "b"])

    def test_before_after_diff(self):
        ctx, plan = compile_yaml("title: T\nlayout:\n- diff: {before: \"a\\nb\", after: \"a\\nc\"}")
        self.assertEqual(plan["layout"][0]["p"]["files"][0]["add"], 1)

    def test_code_line_range(self):
        d = Path(tempfile.mkdtemp())
        (d / "m.py").write_text("\n".join(f"l{i}" for i in range(1, 21)))
        ctx, plan = compile_yaml("title: T\nlayout:\n- code: {src: m.py, lines: 5-7}", d)
        p = plan["layout"][0]["p"]
        self.assertEqual((p["src"], p["start"], p["lang"]), ("l5\nl6\nl7", 5, "python"))

    def test_graph_to_mermaid(self):
        ctx, plan = compile_yaml("title: T\ndata: {e: [{a: web, b: api}]}\nlayout:\n- graph: {data: e, from: a, to: b}")
        src = plan["layout"][0]["p"]["src"]
        self.assertIn("flowchart LR", src)
        self.assertIn('"web"', src)


class Cli(unittest.TestCase):
    def test_catalog_lists_every_component(self):
        rc, out = run("catalog")
        self.assertEqual(rc, 0)
        for name in softui.R.C:
            self.assertIn(f"  {name}:", out)
        self.assertLess(len(out), 4500)

    def test_explain_alias(self):
        rc, out = run("explain", "kanban")
        self.assertIn("board (you wrote 'kanban')", out)

    def test_render_writes_page_and_artifact_form(self):
        d = Path(tempfile.mkdtemp())
        (d / "s.yaml").write_text("title: Hello\nlayout:\n- text: hi\n- diagram: 'flowchart LR\\n A-->B'")
        rc, out = run("render", str(d / "s.yaml"), "--fast")
        self.assertEqual(rc, 0, out)
        page = (d / "s.html").read_text()
        self.assertIn("<!doctype html>", page)
        self.assertIn("mermaid", page)
        rc, out = run("render", str(d / "s.yaml"), "-o", str(d / "a.html"), "--artifact", "--fast")
        art = (d / "a.html").read_text()
        self.assertNotIn("<html", art)
        self.assertTrue(art.startswith("<title>Hello</title>"))

    def test_render_error_writes_nothing(self):
        d = Path(tempfile.mkdtemp())
        (d / "s.yaml").write_text("title: T\nlayout:\n- table: {data: nope}")
        rc, out = run("render", str(d / "s.yaml"), "--fast")
        self.assertEqual(rc, 1)
        self.assertIn("FAILED", out)
        self.assertFalse((d / "s.html").exists())

    def test_yaml_error_is_short(self):
        d = Path(tempfile.mkdtemp())
        (d / "s.yaml").write_text("title: T\nlayout:\n- text: a: b")
        rc, out = run("render", str(d / "s.yaml"), "--fast")
        self.assertEqual(rc, 1)
        self.assertIn("line 3", out)


if __name__ == "__main__":
    unittest.main()
