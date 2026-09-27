#!/usr/bin/env python3
"""pdlc review packets. Builds one packet per review remit for a change.

Usage:
  python3 pdlc/bin/make_packets.py CH-0001            every remit in pdlc/config.md
  python3 pdlc/bin/make_packets.py CH-0001 tests      one remit

Each packet is pdlc/changes/<change>/review/<remit>/packet.md and holds:
  - the remit, from pdlc/reviews/<remit>.md;
  - the spec: the change spec, the full text of each requirement it lists, and every spec
    it relies on;
  - the material: for the tests remit, the check files and nothing else; for every other
    remit, the changed app files and nothing else. The specification packet also points to
    the visual review frames.

Run it from the project root, on the change's branch.
"""
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_REMITS = ["tests", "specification", "security", "quality", "compliance", "privacy"]
KINDS = {"JOB": "jobs", "CAP": "capabilities", "DES": "design"}


def section(text, title):
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else ""


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout


def remits(root):
    config = root / "pdlc" / "config.md"
    text = config.read_text() if config.exists() else ""
    line = re.search(r"^- remits:\s*(.+)$", section(text, "Reviews"), re.M)
    if not line:
        return DEFAULT_REMITS
    return [r.strip() for r in line.group(1).split(",") if r.strip() and r.strip() != "none"]


def spec_file(root, spec_id):
    return root / "pdlc" / "specs" / KINDS[spec_id.split("-", 1)[0]] / (spec_id + ".md")


def requirement_text(root, req_id):
    path = spec_file(root, req_id.rsplit(".", 1)[0])
    if not path.exists():
        return "(%s not found)" % req_id
    text = path.read_text()
    match = re.search(r"^### %s\b.*?(?=^### |^## |\Z)" % re.escape(req_id), text, re.M | re.S)
    return match.group(0).strip() if match else "(%s is not in its spec)" % req_id


def fence(text):
    return "````\n" + text.rstrip() + "\n````"


def material(root, base, files, title):
    parts = ["## %s\n" % title]
    if not files:
        return parts[0] + "\nNone changed.\n"
    parts.append("### Diff against %s\n\n%s\n" % (base, fence(git(root, "diff", base + "...HEAD", "--", *files))))
    for name in files:
        path = root / name
        body = path.read_text(errors="replace") if path.exists() else "(deleted)"
        parts.append("### %s\n\n%s\n" % (name, fence(body)))
    return "\n".join(parts)


def main(argv, root=Path(".")):
    if len(argv) < 2:
        print(__doc__)
        return 1
    folders = sorted(p.parent for p in (root / "pdlc" / "changes").glob(argv[1] + "-*/change.md"))
    if not folders:
        print("No change spec found for %s" % argv[1])
        return 1
    folder = folders[0]
    change = (folder / "change.md").read_text()
    found = re.search(r"Base:\s*([^\s·]+)", change)
    base = found.group(1) if found else "main"

    checks = re.findall(r"^-\s+`?([^`\s]+)`?", section(change, "Check files"), re.M)
    checks = [c for c in checks if c.lower() != "none"]
    changed = [f for f in git(root, "diff", "--name-only", base + "...HEAD").split() if f]
    tests = [f for f in changed if f in checks]
    code = [f for f in changed if f not in checks and not f.startswith("pdlc/")]

    reqs = re.findall(r"^### ((?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+)", section(change, "Requirements"), re.M)
    relies = re.findall(r"\b((?:JOB|CAP|DES)-[a-z0-9-]+)\b", section(change, "Relies on"))
    spec = ["## The change spec\n", fence(change), "\n## The requirements, in full\n"]
    spec += [requirement_text(root, r) + "\n" for r in reqs]
    spec.append("## Specs it relies on\n")
    for spec_id in dict.fromkeys(relies):
        path = spec_file(root, spec_id)
        spec.append("### %s\n\n%s\n" % (spec_id, fence(path.read_text()) if path.exists() else "(not found)"))
    spec = "\n".join(spec)

    frames = sorted((folder / "frames").glob("*.png")) if (folder / "frames").exists() else []
    chosen = argv[2:] or remits(root)
    for remit in chosen:
        remit_file = root / "pdlc" / "reviews" / (remit + ".md")
        remit_text = remit_file.read_text() if remit_file.exists() else "# Remit: %s\n" % remit
        out = ["# Review packet · %s · %s\n" % (folder.name, remit),
               "Judge only what is in this packet. Write your result next to it, in result.md.\n",
               remit_text.strip() + "\n", spec]
        if remit == "tests":
            out.append(material(root, base, tests, "The checks"))
        else:
            out.append(material(root, base, code, "The code"))
        if remit == "specification" and frames:
            out.append("## Visual review frames\n\nRead each frame to see the change working:\n")
            out += ["- %s" % f.relative_to(root).as_posix() for f in frames]
        target = folder / "review" / remit
        target.mkdir(parents=True, exist_ok=True)
        (target / "packet.md").write_text("\n".join(out) + "\n")
        print("wrote %s" % (target / "packet.md").relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
