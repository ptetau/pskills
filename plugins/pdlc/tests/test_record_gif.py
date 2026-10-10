"""Tests for pdlc's GIF recorder, terminal kind. Run: python3 -m unittest discover plugins/pdlc/tests

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


@unittest.skipUnless(node_modules(), "needs node, playwright, gifenc and pngjs")
class TerminalRecording(unittest.TestCase):
    BANNER = 44  # the caption bar covers the rows above this

    def record(self, steps, height=300):
        tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        tools = tmp / "pdlc/.tools/node_modules"
        tools.mkdir(parents=True)
        for root in node_modules():
            for name in ("playwright", "playwright-core", "gifenc", "pngjs"):
                if (Path(root) / name).is_dir() and not (tools / name).exists():
                    (tools / name).symlink_to(Path(root) / name)
        (tmp / "visual.json").write_text(json.dumps(
            {"kind": "terminal", "title": "CH-0001 · test", "width": 600, "height": height,
             "steps": steps}))
        run = subprocess.run(["node", str(SCRIPT), "visual.json", "out"], cwd=tmp,
                             capture_output=True, text=True, timeout=180)
        self.assertEqual(run.returncode, 0, run.stderr)
        return tmp / "out/frames"

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


if __name__ == "__main__":
    unittest.main()
