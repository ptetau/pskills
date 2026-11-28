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


class Transforms(unittest.TestCase):
    def test_group_sum_sort_top_pct(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  r: [{s: a, ms: 1}, {s: a, ms: 3}, {s: b, ms: 10}, {s: c, ms: 2}]\n"
                                 "  g: {from: r, group: s, sum: [ms], pct: [ms], sort: -ms, top: 2}\nlayout: [{table: g}]")
        self.assertEqual(ctx.errors, [])
        self.assertEqual(plan["data"]["g"]["rows"], [{"s": "b", "count": 1, "ms": 10, "ms_pct": 62.5},
                                                     {"s": "a", "count": 2, "ms": 4, "ms_pct": 25.0}])

    def test_where_join_explode(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  names: [{id: S1, step: Freeze}, {id: S2, step: Build}]\n"
                                 "  plan:\n    rows: [{id: S2, after: [S1]}, {id: S3, after: [S1, S2]}]\n"
                                 "    explode: after\n    join: {data: names, on: [after, id], cols: [step]}\n"
                                 "    where: {id: '!=S9'}\nlayout: [{table: plan}]")
        self.assertEqual(ctx.errors, [])
        rows = plan["data"]["plan"]["rows"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["step"], "Freeze")

    def test_describe_and_corr(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  o: {rows: [{arm: a, m: 1, k: 2}, {arm: a, m: 3, k: 6}, {arm: b, m: 5, k: 1}, {arm: b, m: 7, k: 0}],"
                                 " describe: [m], by: arm}\n  c: {rows: [{x: 1, y: 2}, {x: 2, y: 4}, {x: 3, y: 6}], corr: [x, y]}\nlayout: [{table: o}]")
        self.assertEqual(ctx.errors, [])
        d = plan["data"]["o"]["rows"]
        self.assertEqual((d[0]["arm"], d[0]["n"], d[0]["mean"]), ("a", 2, 2.0))
        self.assertEqual(plan["data"]["c"]["rows"][1]["r"], 1.0)

    def test_bad_column_names_the_columns(self):
        ctx, _ = compile_yaml("title: T\ndata:\n  g: {rows: [{suite: a}], group: zzz}\nlayout: [{table: g}]")
        self.assertTrue(any("Columns: suite" in e for e in ctx.errors))

    def test_nested_parts(self):
        d = Path(tempfile.mkdtemp())
        (d / "x.json").write_text('{"cash": {"bank": 5}, "uc": {"name": "n", "steps": ["a", "b"]}}')
        ctx, plan = compile_yaml("title: T\ndata: {x: x.json}\nlayout: [{table: x.uc.steps}, {kv: {data: x.cash}}]", d)
        self.assertEqual(ctx.errors, [])
        self.assertEqual(plan["data"]["x.uc.steps"]["rows"][1], {"n": 2, "value": "b"})


class NewComponents(unittest.TestCase):
    def test_truth_table_rows(self):
        ctx, plan = compile_yaml("title: T\nlayout:\n- truth: {inputs: [a, b], outputs: {y: a and not b, x: a xor b}}")
        self.assertEqual(ctx.errors, [])
        rows = plan["layout"][0]["p"]["rows"]
        self.assertEqual([(r["y"], r["x"]) for r in rows], [(0, 0), (0, 1), (1, 1), (0, 0)])

    def test_truth_unknown_input(self):
        ctx, _ = compile_yaml("title: T\nlayout:\n- truth: {inputs: [a], outputs: {y: a and c}}")
        self.assertTrue(any("unknown input(s) c" in e for e in ctx.errors))

    def test_er_and_classes(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  s: [{t: users, c: id, ty: uuid, k: pk}, {t: orders, c: user_id, ty: uuid, k: fk, r: users.id}]\n"
                                 "  k: [{n: Order, f: 'id: Id, buyer: User'}, {n: User, f: [id: Id]}]\n"
                                 "layout:\n- er: {data: s, table: t, column: c, type: ty, key: k, ref: r}\n- classes: {data: k, name: n, fields: f}")
        self.assertEqual(ctx.errors, [])
        self.assertIn('users ||--o{ orders : "user_id"', plan["layout"][0]["p"]["src"])
        self.assertIn("Order --> User : buyer", plan["layout"][1]["p"]["src"])

    def test_sankey_cycle_is_an_error(self):
        ctx, _ = compile_yaml("title: T\ndata: {f: [{a: x, b: y, v: 1}, {a: y, b: x, v: 1}]}\nlayout:\n- sankey: {data: f, from: a, to: b, value: v}")
        self.assertTrue(any("cycle: x → y → x" in e for e in ctx.errors))

    def test_decision_weights_from_dataset(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  o: [{name: A, scores: {cost: 3}}]\n  w: [{criterion: cost, weight: 0.5}]\n"
                                 "layout:\n- decision: {data: o, option: name, scores: scores, weights: w}")
        self.assertEqual(plan["layout"][0]["p"]["weights"], {"cost": 0.5})

    def test_signed_graph_edges(self):
        ctx, plan = compile_yaml("title: T\ndata: {e: [{a: x, b: y, s: '-'}]}\nlayout:\n- graph: {data: e, from: a, to: b, sign: s}")
        src = plan["layout"][0]["p"]["src"]
        self.assertIn("-.->", src)
        self.assertIn("linkStyle 0 stroke:#dc3c3d", src)


class RoundTwoFixes(unittest.TestCase):
    def test_where_skips_nulls(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  d: {rows: [{a: 1, b: 2}, {a: 2}], where: {b: '>0'}}\nlayout: [{table: d}]")
        self.assertEqual(len(plan["data"]["d"]["rows"]), 1)

    def test_keyword_column_in_expression(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  d: {rows: [{from: a, to: b, my col: 3}], add: {pair: \"from + '>' + to\", x: '`my col` * 2'}}\n"
                                 "layout: [{table: d}]")
        self.assertEqual(ctx.errors, [])
        self.assertEqual((plan["data"]["d"]["rows"][0]["pair"], plan["data"]["d"]["rows"][0]["x"]), ("a>b", 6))

    def test_pivot_union_group_all_multisort(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  a: [{acc: x, m: jan, v: 1}, {acc: x, m: feb, v: 2}]\n  b: [{acc: y, m: jan, v: 5}]\n"
                                 "  p: {from: a, union: [b], pivot: {index: acc, columns: m, values: v}, sort: [-jan, acc]}\n"
                                 "  t: {from: a, group: all, sum: [v]}\nlayout: [{table: p}]")
        self.assertEqual(ctx.errors, [])
        self.assertEqual(plan["data"]["p"]["rows"][0], {"acc": "y", "jan": 5})
        self.assertEqual(plan["data"]["t"]["rows"], [{"count": 2, "v": 3}])

    def test_bytes_function(self):
        ctx, plan = compile_yaml("title: T\ndata:\n  d: {rows: [{s: 1.5 GB}, {s: 64 kB}], add: {b: bytes(s)}}\nlayout: [{table: d}]")
        self.assertEqual([r["b"] for r in plan["data"]["d"]["rows"]], [1.5 * 1024 ** 3, 64 * 1024])

    def test_pct_on_fractions_becomes_ratio(self):
        ctx, plan = compile_yaml("title: T\ndata: {d: [{m: 0.146}, {m: 0.5}]}\nlayout: [{table: {data: d, fmt: {m: pct}}}]")
        self.assertEqual(plan["layout"][0]["p"]["fmt"], {"m": "ratio"})
        self.assertTrue(any("ratio" in f for f in ctx.fixes))

    def test_truth_from_object(self):
        d = Path(tempfile.mkdtemp())
        (d / "l.json").write_text('{"inputs": ["a", "b"], "outputs": {"y": "a and b"}}')
        ctx, plan = compile_yaml("title: T\ndata: {l: l.json}\nlayout: [{truth: {data: l, highlight: y}}]", d)
        self.assertEqual(ctx.errors, [])
        self.assertEqual(len(plan["layout"][0]["p"]["rows"]), 4)

    def test_graph_cycles(self):
        ctx, plan = compile_yaml("title: T\ndata: {e: [{a: x, b: y}, {a: y, b: x}, {a: y, b: z}]}\nlayout:\n- graph: {data: e, from: a, to: b, cycles: true}")
        p = plan["layout"][0]["p"]
        self.assertEqual(p["cyclelist"], [["x", "y", "x"]])
        self.assertIn("linkStyle 0 stroke:#dc3c3d", p["src"])
        self.assertNotIn("linkStyle 2", p["src"])

    def test_object_file_is_one_row(self):
        d = Path(tempfile.mkdtemp())
        (d / "c.json").write_text('{"bank": 5, "savings": 7}')
        ctx, plan = compile_yaml("title: T\ndata:\n  c: {file: c.json, add: {total: bank + savings}}\nlayout: [{kv: {data: c}}]", d)
        self.assertEqual(plan["data"]["c"]["rows"], [{"bank": 5, "savings": 7, "total": 12}])


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
        self.assertLess(len(out), 5600)

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
