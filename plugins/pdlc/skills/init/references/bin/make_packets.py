#!/usr/bin/env python3
"""pdlc review packets. Builds one packet per review remit for a change.

Usage:
  python3 pdlc/bin/make_packets.py CH-0001            every remit in pdlc/config.md
  python3 pdlc/bin/make_packets.py CH-0001 tests      one remit

Each packet is pdlc/changes/<change>/review/<remit>/packet.md. Writing a packet removes
that remit's old result.md, so a result is always about the packet next to it. A packet
holds:
  - the remit, from pdlc/reviews/<remit>.md;
  - the spec:
    - the change spec;
    - the title and summary of the spec it covers (everything above its requirements);
    - the full text of each requirement it lists;
    - every spec it relies on. DES-writing-style goes only to the specification remit,
      because only that remit judges writing;
  - the material: for the tests remit, the check files and nothing else; for every other
    remit, the changed app files and nothing else.
The compliance remit gets a result in place of a packet when its remit file still says
"Rules: none listed yet." and the change touches no dependency file. Then the script
writes result.md with "Result: pass" and the reason, and no reviewer is needed.
The specification packet also holds the writing check and points to the visual review
frames. The writing check is the output of check_writing.py for the lines this change
wrote in its .md files: README, docs, specs and the change spec.

Run it from the project root, on the change's branch.
"""
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_REMITS = ["tests", "specification", "security", "quality", "compliance", "privacy"]
KINDS = {"JOB": "jobs", "CAP": "capabilities", "DES": "design"}
WRITING_CHECK = Path(__file__).parent / "check_writing.py"
# Files that declare dependencies. When a project lists no compliance rules, a change that
# touches none of these files has nothing for the compliance remit to judge.
DEPENDENCY_FILES = re.compile(
    r"(^|/)(requirements[^/]*\.txt|pyproject\.toml|setup\.py|setup\.cfg|Pipfile(\.lock)?|"
    r"package(-lock)?\.json|yarn\.lock|pnpm-lock\.yaml|go\.(mod|sum)|Cargo\.(toml|lock)|"
    r"Gemfile(\.lock)?|pom\.xml|build\.gradle(\.kts)?|composer\.(json|lock)|[^/]*\.csproj)$")
NO_RULES = "Rules: none listed yet."


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


def compliance_applies(remit_text, changed):
    """False when the project lists no compliance rules and no dependency file changed."""
    return NO_RULES not in remit_text or any(DEPENDENCY_FILES.search(f) for f in changed)


def spec_file(root, spec_id):
    return root / "pdlc" / "specs" / KINDS[spec_id.split("-", 1)[0]] / (spec_id + ".md")


def requirement_text(root, req_id):
    path = spec_file(root, req_id.rsplit(".", 1)[0])
    if not path.exists():
        return "(%s not found)" % req_id
    text = path.read_text()
    match = re.search(r"^### %s\b.*?(?=^### |^## |\Z)" % re.escape(req_id), text, re.M | re.S)
    return match.group(0).strip() if match else "(%s is not in its spec)" % req_id


def spec_head(root, spec_id):
    """A spec's title, summary and code map: everything above its '## Requirements'."""
    path = spec_file(root, spec_id)
    if not path.exists():
        return "(%s not found)" % spec_id
    return re.split(r"^## Requirements\b", path.read_text(), maxsplit=1, flags=re.M)[0].strip()


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


def writing_check(root, base, files):
    """The packet section with the writing check of the lines this change wrote."""
    title = "## Writing check\n\n"
    if not files:
        return title + "No text files changed.\n"
    done = subprocess.run([sys.executable, str(WRITING_CHECK), "--since", base, *files],
                          cwd=root, capture_output=True, text=True)
    return title + ("`pdlc/bin/check_writing.py --since %s` on %s:\n\n%s\n"
                    % (base, ", ".join(files), fence(done.stdout + done.stderr)))


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
    listed = subprocess.run(["git", "diff", "--name-only", base + "...HEAD"], cwd=root,
                            capture_output=True, text=True)
    if listed.returncode != 0:
        print("Can't diff against %s: %s" % (base, listed.stderr.strip()))
        return 1
    changed = [f for f in listed.stdout.splitlines() if f]
    tests = [f for f in changed if f in checks]
    code = [f for f in changed if f not in checks and not f.startswith("pdlc/")]
    change_spec = (folder / "change.md").relative_to(root).as_posix()
    text_files = [f for f in changed if f.endswith(".md") and (root / f).exists()
                  and (not f.startswith("pdlc/") or f.startswith("pdlc/specs/") or f == change_spec)]

    reqs = re.findall(r"^### ((?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+)", section(change, "Requirements"), re.M)
    relies = re.findall(r"\b((?:JOB|CAP|DES)-[a-z0-9-]+)\b", section(change, "Relies on"))
    scope = re.search(r"Scope:\s*((?:JOB|CAP|DES)-[a-z0-9-]+)", change)
    spec = ["## The change spec\n", fence(change)]
    if scope:
        spec += ["\n## The spec it covers: title and summary\n", fence(spec_head(root, scope.group(1)))]
    spec.append("\n## The requirements, in full\n")
    spec += [requirement_text(root, r) + "\n" for r in reqs]
    spec.append("## Specs it relies on\n")
    relied = []
    for spec_id in dict.fromkeys(relies):
        path = spec_file(root, spec_id)
        relied.append((spec_id, "### %s\n\n%s\n" % (spec_id, fence(path.read_text()) if path.exists() else "(not found)")))
    # The writing rules go only to the remit that judges writing. The other remits judge code or checks.
    spec_for = {}
    for kind in ("specification", "other"):
        parts = [text for spec_id, text in relied if kind == "specification" or spec_id != "DES-writing-style"]
        spec_for[kind] = "\n".join(spec + parts)

    frames = sorted((folder / "frames").glob("*.png")) if (folder / "frames").exists() else []
    chosen = argv[2:] or remits(root)
    for remit in chosen:
        remit_file = root / "pdlc" / "reviews" / (remit + ".md")
        remit_text = remit_file.read_text() if remit_file.exists() else "# Remit: %s\n" % remit
        if remit == "compliance" and not compliance_applies(remit_text, changed):
            target = folder / "review" / remit
            target.mkdir(parents=True, exist_ok=True)
            (target / "packet.md").unlink(missing_ok=True)
            (target / "result.md").write_text(
                "Result: pass\n\nRemit: compliance\n\nProblems: none\n\nFollow-ups: none\n\nNotes:\n"
                "- Not applicable. The project lists no compliance rules, and the change touches no\n"
                "  dependency file. make_packets.py wrote this result, so no reviewer is needed.\n")
            print("wrote %s (compliance does not apply: no rules and no dependency file. Start no reviewer for it.)"
                  % (target / "result.md").relative_to(root).as_posix())
            continue
        out = ["# Review packet · %s · %s\n" % (folder.name, remit),
               "Judge only what is in this packet. Write your result next to it, in result.md.\n",
               remit_text.strip() + "\n", spec_for["specification" if remit == "specification" else "other"]]
        if remit == "tests":
            out.append(material(root, base, tests, "The checks"))
        else:
            out.append(material(root, base, code, "The code"))
        if remit == "specification":
            out.append(writing_check(root, base, text_files))
        if remit == "specification" and frames:
            out.append("## Visual review frames\n\nRead each frame to see the change working:\n")
            out += ["- %s" % f.relative_to(root).as_posix() for f in frames]
        target = folder / "review" / remit
        target.mkdir(parents=True, exist_ok=True)
        (target / "packet.md").write_text("\n".join(out) + "\n")
        stale = target / "result.md"
        if stale.exists():
            stale.unlink()
        print("wrote %s" % (target / "packet.md").relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
