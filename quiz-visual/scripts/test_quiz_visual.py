#!/usr/bin/env python3
"""Tests for render_quiz.py and check_quiz.py. Run: python3 test_quiz_visual.py"""

import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_quiz  # noqa: E402
import render_quiz  # noqa: E402

EXAMPLE = os.path.join(HERE, "..", "examples", "summit-welcome.quiz.json")


def example():
    with open(EXAMPLE, encoding="utf-8") as f:
        return json.load(f)


def small():
    return {
        "title": "Test Quiz", "intro": "One question shows two options.",
        "questions": [{
            "id": "tone", "label": "Tone", "question": "Which tone suits the email?",
            "options": [
                {"id": "a", "label": "Warm", "text": "A warm voice is friendly, but it has less energy.",
                 "preview": {"kind": "sample", "body": ["Hello there."]}},
                {"id": "b", "label": "Plain", "text": "A plain voice gives the facts, but it feels cold.",
                 "preview": {"kind": "none"}},
            ],
        }],
    }


class ValidateTests(unittest.TestCase):
    def test_example_is_valid(self):
        self.assertEqual(render_quiz.validate(example()), [])

    def errors(self, mutate):
        spec = small()
        mutate(spec)
        return "\n".join(render_quiz.validate(spec))

    def test_recommended_needs_evidence(self):
        self.assertIn("evidence", self.errors(lambda s: s["questions"][0]["options"][0].update(recommended=True)))

    def test_two_recommended(self):
        def m(s):
            for o in s["questions"][0]["options"]:
                o["recommended"] = True
            s["questions"][0]["evidence"] = "You said so."
        self.assertIn("at most one", self.errors(m))

    def test_evidence_without_recommendation(self):
        self.assertIn("no option is recommended", self.errors(lambda s: s["questions"][0].update(evidence="You said so.")))

    def test_label_too_long(self):
        self.assertIn("12 characters", self.errors(lambda s: s["questions"][0].update(label="A very long label")))

    def test_question_needs_question_mark(self):
        self.assertIn("ends with '?'", self.errors(lambda s: s["questions"][0].update(question="Pick a tone.")))

    def test_too_few_options(self):
        self.assertIn("2 to 5 options", self.errors(lambda s: s["questions"][0].update(options=s["questions"][0]["options"][:1])))

    def test_duplicate_ids(self):
        self.assertIn("two times", self.errors(lambda s: s["questions"][0]["options"][1].update(id="a")))

    def test_unknown_kind(self):
        self.assertIn("preview.kind", self.errors(lambda s: s["questions"][0]["options"][0].update(preview={"kind": "video"})))

    def test_svg_needs_alt(self):
        p = {"kind": "svg", "svg": "<svg viewBox='0 0 1 1'></svg>"}
        self.assertIn("alt", self.errors(lambda s: s["questions"][0]["options"][0].update(preview=p)))

    def test_web_address_is_refused(self):
        p = {"kind": "html", "alt": "A box.", "html": "<img src='https://example.com/a.png'>"}
        self.assertIn("web address", self.errors(lambda s: s["questions"][0]["options"][0].update(preview=p)))

    def test_svg_namespace_is_allowed(self):
        p = {"kind": "svg", "alt": "A box.", "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'}
        self.assertEqual(self.errors(lambda s: s["questions"][0]["options"][0].update(preview=p)), "")

    def test_js_only_for_demo(self):
        p = {"kind": "html", "alt": "A box.", "html": "<b>x</b>", "js": "1"}
        self.assertIn("only for the demo", self.errors(lambda s: s["questions"][0]["options"][0].update(preview=p)))

    def test_bad_colour(self):
        p = {"kind": "swatch", "colors": [{"name": "A", "value": "red"}, {"name": "B", "value": "#fff"}]}
        self.assertIn("#1a2b3c", self.errors(lambda s: s["questions"][0]["options"][0].update(preview=p)))

    def test_unknown_wireframe_block(self):
        p = {"kind": "wireframe", "rows": ["header", "banana"]}
        self.assertIn("unknown block", self.errors(lambda s: s["questions"][0]["options"][0].update(preview=p)))


class RenderTests(unittest.TestCase):
    def test_renders_each_option(self):
        spec = example()
        page = render_quiz.render(spec)
        for q in spec["questions"]:
            self.assertIn('id="q-%s"' % q["id"], page)
            for o in q["options"]:
                self.assertIn('id="%s--%s"' % (q["id"], o["id"]), page)

    def test_is_deterministic(self):
        self.assertEqual(render_quiz.render(example()), render_quiz.render(example()))

    def test_text_is_escaped(self):
        spec = small()
        spec["questions"][0]["options"][0]["text"] = "A <script>alert(1)</script> voice, but it is odd."
        page = render_quiz.render(spec)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_embedded_json_cannot_close_the_script(self):
        spec = small()
        spec["title"] = "Close </script> Quiz"
        page = render_quiz.render(spec)
        start = page.index('id="quiz-spec">') + len('id="quiz-spec">')
        end = page.index("</script>", start)
        self.assertEqual(json.loads(page[start:end])["title"], "Close </script> Quiz")

    def test_frames_are_sandboxed(self):
        page = render_quiz.render(example())
        frames = [t for t in __import__("re").findall(r"<iframe\b[^>]*>", page)]
        self.assertTrue(frames)
        self.assertTrue(all("sandbox=" in t for t in frames))
        self.assertIn('sandbox="allow-scripts"', page)
        self.assertIn('sandbox=""', page)
        self.assertIn("Content-Security-Policy", page)
        self.assertNotIn("allow-same-origin", page)

    def test_multi_question_uses_checkboxes(self):
        spec = small()
        spec["questions"][0]["multi"] = True
        page = render_quiz.render(spec)
        self.assertIn('type="checkbox"', page)
        self.assertNotIn('type="radio"', page)

    def test_long_flow_is_a_column(self):
        spec = small()
        spec["questions"][0]["options"][0]["preview"] = {"kind": "flow", "steps": [{"label": s} for s in "ABCD"]}
        self.assertIn("pv-flow col", render_quiz.render(spec))

    def test_artifact_form(self):
        page = render_quiz.render(example(), artifact=True)
        for tag in ("<html", "<head>", "<body", "<!doctype", "<meta charset", "name=\"viewport\""):
            self.assertNotIn(tag, page)
        self.assertTrue(page.startswith("<title>"))
        self.assertIn("<style>", page)
        self.assertIn('claude:viewport-fit-sides', page)

    def test_invalid_spec_raises(self):
        spec = small()
        spec["title"] = "One"
        with self.assertRaises(ValueError):
            render_quiz.render(spec)

    def test_recommended_shows_the_evidence(self):
        spec = small()
        spec["questions"][0]["options"][0]["recommended"] = True
        spec["questions"][0]["evidence"] = "You said this is a gym"
        page = render_quiz.render(spec)
        self.assertIn("Suggested", page)
        self.assertIn("You said this is a gym.", page)


class CheckTests(unittest.TestCase):
    def test_example_passes_with_no_warnings(self):
        errors, warns = check_quiz.check_spec(example())
        self.assertEqual((errors, warns), ([], []))
        self.assertEqual(check_quiz.check_page(example(), render_quiz.render(example())), [])

    def test_should_in_a_question_is_a_warning(self):
        spec = small()
        spec["questions"][0]["question"] = "What tone should the email have?"
        _, warns = check_quiz.check_spec(spec)
        self.assertTrue(any("should" in w for w in warns))

    def test_all_none_is_a_warning(self):
        spec = small()
        spec["questions"][0]["options"][0]["preview"] = {"kind": "none"}
        _, warns = check_quiz.check_spec(spec)
        self.assertTrue(any("no option has a preview" in w for w in warns))

    def test_page_with_a_different_question_fails(self):
        spec, other = small(), small()
        other["questions"][0]["options"][1]["id"] = "z"
        errs = check_quiz.check_page(spec, render_quiz.render(other))
        self.assertTrue(any("different from the spec" in e for e in errs))

    def test_unsandboxed_frame_and_network_load_fail(self):
        spec = example()
        page = render_quiz.render(spec).replace('sandbox="allow-scripts"', "", 1)
        page = page.replace("</main>", '<img src="https://example.com/x.png"></main>')
        errs = "\n".join(check_quiz.check_page(spec, page))
        self.assertIn("no sandbox", errs)
        self.assertIn("example.com", errs)

    def test_duplicate_id_fails(self):
        spec = small()
        page = render_quiz.render(spec).replace("</main>", '<i id="q-tone"></i></main>')
        self.assertTrue(any("used two times" in e for e in check_quiz.check_page(spec, page)))


if __name__ == "__main__":
    unittest.main(verbosity=1)
