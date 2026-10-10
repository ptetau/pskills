"""Tests for pdlc's GIF recorder. Run: python3 -m unittest discover plugins/pdlc/tests

These run the real recorder, so they need node, playwright with a browser, gifenc and pngjs.
They look in PDLC_TEST_NODE_MODULES (a node_modules folder) and in `npm root -g`, and skip
when anything is missing.
"""
import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "skills/init/references/bin/record_gif.mjs"


def node_modules():
    """A list of node_modules folders that hold the recorder's packages, or None."""
    if not shutil.which("node"):
        return None
    roots = [os.environ.get("PDLC_TEST_NODE_MODULES", "")]
    try:
        roots.append(subprocess.run(["npm", "root", "-g"], capture_output=True, text=True,
                                    timeout=30).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    roots = [r for r in roots if r and Path(r).is_dir()]
    for name in ("playwright", "gifenc", "pngjs"):
        if not any((Path(r) / name).is_dir() for r in roots):
            return None
    return roots


def read_png(path):
    """(width, height, rows of (r, g, b)) for an 8-bit RGB or RGBA png."""
    data = Path(path).read_bytes()
    pos, idat = 8, b""
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color = struct.unpack(">IIBB", body[:10])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    assert depth == 8 and color in (2, 6), "unexpected png format"
    bpp = 3 if color == 2 else 4
    raw, stride, prev, rows = zlib.decompress(idat), width * bpp, bytearray(width * bpp), []
    for y in range(height):
        start = y * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for i in range(stride):
            left = line[i - bpp] if i >= bpp else 0
            up, corner = prev[i], (prev[i - bpp] if i >= bpp else 0)
            if kind == 1:
                line[i] = (line[i] + left) & 255
            elif kind == 2:
                line[i] = (line[i] + up) & 255
            elif kind == 3:
                line[i] = (line[i] + (left + up) // 2) & 255
            elif kind == 4:
                p = left + up - corner
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - corner)
                line[i] = (line[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else corner)) & 255
        rows.append([tuple(line[x * bpp:x * bpp + 3]) for x in range(width)])
        prev = line
    return width, height, rows


def green(px):
    """The prompt's green, #34d399, allowing for anti-aliasing."""
    return px[1] > 140 and px[1] - px[0] > 60 and px[1] - px[2] > 20


def bands(rows, test, top):
    """Runs of rows below `top` holding at least one pixel that passes `test`."""
    found, start = [], None
    for y, row in enumerate(rows):
        hit = y >= top and any(test(px) for px in row)
        if hit and start is None:
            start = y
        if not hit and start is not None:
            found.append((start, y - 1))
            start = None
    if start is not None:
        found.append((start, len(rows) - 1))
    return found


class Recording(unittest.TestCase):
    BANNER = 44  # the caption bar covers the rows above this

    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        tools = self.tmp / "pdlc/.tools/node_modules"
        tools.mkdir(parents=True)
        for root in node_modules():
            for name in ("playwright", "playwright-core", "gifenc", "pngjs"):
                if (Path(root) / name).is_dir() and not (tools / name).exists():
                    (tools / name).symlink_to(Path(root) / name)

    def run_recorder(self, steps, kind="terminal", height=300):
        (self.tmp / "visual.json").write_text(json.dumps(
            {"kind": kind, "title": "CH-0001 · test", "width": 600, "height": height,
             "steps": steps}))
        return subprocess.run(["node", str(SCRIPT), "visual.json", "out"], cwd=self.tmp,
                              capture_output=True, text=True, timeout=180)

    def record(self, steps, kind="terminal", height=300):
        run = self.run_recorder(steps, kind, height)
        self.assertEqual(run.returncode, 0, run.stderr)
        return self.tmp / "out/frames"

    def refused(self, steps, kind="terminal"):
        """The recorder's error output, after checking it failed and wrote no GIF."""
        run = self.run_recorder(steps, kind)
        self.assertNotEqual(run.returncode, 0, "the recorder accepted it:\n" + run.stdout)
        self.assertFalse((self.tmp / "out/review.gif").exists(), "a GIF was written anyway")
        return run.stderr

    def page(self, name, html):
        """A local page for a web script, as a file:// address."""
        path = self.tmp / name
        path.write_text("<!doctype html><meta charset='utf-8'>" + html)
        return path.as_uri()


@unittest.skipUnless(node_modules(), "needs node, playwright, gifenc and pngjs")
class TerminalRecording(Recording):

    def test_the_newest_command_stays_in_the_frame(self):
        frames = self.record([{"caption": "CAP-x.R1 · long output", "run": "seq 1 60"},
                              {"caption": "CAP-x.R2 · then one line", "run": "echo last"}])
        _, height, rows = read_png(frames / "02.png")
        prompts = bands(rows, green, self.BANNER)
        self.assertTrue(prompts, "no prompt in the frame")
        self.assertGreater(prompts[-1][0], height // 2,
                           "the newest prompt is not near the bottom: older output fills the frame")

    def test_a_command_that_succeeds_shows_its_error_output(self):
        frames = self.record([{"caption": "CAP-x.R1 · warns", "run": "echo warning >&2"}])
        _, _, rows = read_png(frames / "01.png")
        text = bands(rows, lambda px: min(px) > 120, self.BANNER)
        self.assertGreaterEqual(len(text), 2, "only the command line shows, not what it printed")

    def test_a_blank_frame_fails_and_names_its_step(self):
        err = self.refused([{"caption": "CAP-x.R1 · nothing run yet"}])
        self.assertIn("step 1", err)
        self.assertIn("blank", err)

    def test_a_command_that_prints_nothing_fails_and_names_its_step(self):
        err = self.refused([{"caption": "CAP-x.R1 · prints", "run": "echo one"},
                            {"caption": "CAP-x.R2 · silent", "run": "true"}])
        self.assertIn('step 2 · run "true"', err)
        self.assertIn("printed nothing", err)
        self.assertNotIn("step 1", err)

    def test_a_step_marked_unchanged_may_print_nothing(self):
        self.record([{"caption": "CAP-x.R1 · prints", "run": "echo one"},
                     {"caption": "CAP-x.R2 · says nothing", "run": "true", "unchanged": True}])


@unittest.skipUnless(node_modules(), "needs node, playwright, gifenc and pngjs")
class WebRecording(Recording):
    def test_a_blank_page_fails_and_names_its_step(self):
        url = self.page("blank.html", "<body style='background:#fff'></body>")
        err = self.refused([{"caption": "JOB-x.R1 · the answer shows", "goto": url}], "web")
        self.assertIn("step 1", err)
        self.assertIn("blank", err)

    def test_a_click_that_changes_nothing_fails_and_names_its_step(self):
        url = self.page("dead.html", "<h1>Reset</h1><button id='go' style='all:unset'>Go</button>")
        err = self.refused([{"caption": "JOB-x.R1 · open", "goto": url},
                            {"caption": "JOB-x.R1 · click shows the answer", "click": "#go"}], "web")
        self.assertIn('step 2 · click "#go"', err)
        self.assertIn("did not change", err)

    def test_typing_that_changes_nothing_fails(self):
        url = self.page("hidden.html", "<h1>Form</h1><input id='name' style='opacity:0'>")
        err = self.refused([{"caption": "JOB-x.R1 · open", "goto": url},
                            {"caption": "JOB-x.R1 · type a name", "type": ["#name", "Ana"]}], "web")
        self.assertIn('step 2 · type "#name"', err)

    def test_the_frame_shows_what_a_click_brings_not_the_page_before_it(self):
        url = self.page("slow.html", """
            <h1>Reset</h1><button id='go' style='all:unset'>Go</button>
            <p id='out' style='position:absolute;top:150px;left:20px;margin:0;
               font:bold 48px sans-serif;color:#000'></p>
            <script>document.getElementById('go').onclick = () =>
              setTimeout(() => { document.getElementById('out').textContent = 'DONE'; }, 600);
            </script>""")
        frames = self.record([{"caption": "JOB-x.R1 · open", "goto": url},
                              {"caption": "JOB-x.R1 · the answer shows", "click": "#go"}], "web")
        _, _, rows = read_png(frames / "02.png")
        dark = [px for row in rows[150:210] for px in row[20:200] if max(px) < 80]
        self.assertGreater(len(dark), 200, "frame 2 was taken before the answer appeared")

    def test_a_step_marked_unchanged_may_leave_the_page_as_it_was(self):
        url = self.page("same.html", "<h1>Reset</h1><button id='go' style='all:unset'>Go</button>")
        self.record([{"caption": "JOB-x.R1 · open", "goto": url},
                     {"caption": "JOB-x.R2 · nothing happens", "click": "#go", "unchanged": True}],
                    "web")


if __name__ == "__main__":
    unittest.main()
