#!/usr/bin/env python3
"""pdlc review packets. Builds one packet per review remit for a change.

Usage:
  python3 pdlc/bin/make_packets.py CH-0001            every remit in pdlc/config.md
  python3 pdlc/bin/make_packets.py CH-0001 --verify   every remit in pdlc/config.md except
                                                      tests, for the verify stage
  python3 pdlc/bin/make_packets.py CH-0001 tests      one remit
  python3 pdlc/bin/make_packets.py IN-0001            the tests packet for the acceptance
                                                      checks of an intent

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
    remit, the changed app files and nothing else. The acceptance files of an intent are
    checks, so no packet of a change holds them.
The compliance remit gets a result in place of a packet when its remit file still says
"Rules: none listed yet." and the change touches no dependency file. Then the script
writes result.md with "Result: pass" and the reason, and no reviewer is needed.
The specification packet also holds the writing check and points to the visual review
frames. The writing check is the output of check_writing.py for the lines this change
wrote in its .md files: README, docs, specs and the change spec.

Each packet records the commit that it was made at ("Made at:"). If this remit already
has a result for this change, the new packet is a re-review. The script finds the newest
result in the folder, or else in git. A re-review packet adds a "Re-review" section:
  - "Earlier review:", the commit that the earlier review judged: for tests, the lock in
    its packet; for every other remit, its "Made at";
  - the problems from the earlier result;
  - the diff of the material since that commit.
On a re-review, the writing check covers only the lines changed since that commit, and
the frame list marks each frame that did not change.

The packet for the acceptance checks of an intent is
pdlc/acceptance/<intent>/review/tests/packet.md. It holds the tests remit, the intent, the
full text of each requirement that the intent lists, the "Interface" of each change of
the intent, the specs that those changes rely on (but not DES-writing-style), and the
acceptance file that the intent names under "Acceptance-File:". It also holds the diff of
each acceptance file of an earlier intent that the lock commit changed. It holds no app
code and no component checks. A re-review starts from the lock in the earlier packet
("Acceptance-Locked:").

Run it from the project root, on the change's branch. For an intent, run it on the newest
branch of the intent.
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
# A file name that holds the word "acceptance" and an intent ID is an acceptance file, also
# when pdlc/config.md has no "acceptance file:" line.
ACCEPTANCE_NAME = re.compile(r"(?=.*acceptance)(?=.*(?<![a-z0-9])in[-_]?\d{4}(?!\d))", re.I)


def section(text, title):
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else ""


def field(text, name):
    """A header field of a change spec or intent, such as Status or Branch. The value is
    bare: "IN-0001 (poll-input-errors)" gives "IN-0001", and "`pdlc/CH-0001-x`" gives
    "pdlc/CH-0001-x"."""
    match = re.search(r"\b%s:[ \t]*([^·\n]*?)[ \t]*(?:·|$)" % name, text, re.M)
    if not match:
        return None
    value = match.group(1).replace("`", "")
    return re.sub(r"\s+\(.*\)$", "", value).strip()


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout


def show(root, ref, path):
    """A file as it is at a commit, or None if git cannot find it there."""
    out = subprocess.run(["git", "show", "%s:%s" % (ref, path)], cwd=root,
                         capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def remits(root):
    config = root / "pdlc" / "config.md"
    text = config.read_text() if config.exists() else ""
    line = re.search(r"^- remits:\s*(.+)$", section(text, "Reviews"), re.M)
    if not line:
        return DEFAULT_REMITS
    return [r.strip() for r in line.group(1).split(",") if r.strip() and r.strip() != "none"]


def acceptance_file(root):
    """A regex for the path of an acceptance file, from "acceptance file:" in pdlc/config.md,
    or None. "{intent}" in the path stands for any intent ID."""
    config = root / "pdlc" / "config.md"
    text = config.read_text() if config.exists() else ""
    line = re.search(r"^- acceptance file:\s*`([^`]+)`", text, re.M)
    if not line or "{intent}" not in line.group(1):
        return None
    parts = line.group(1).strip("/ ").split("{intent}")
    return re.compile("^%s$" % r"IN[-_]?\d+".join(re.escape(part) for part in parts), re.I)


def is_acceptance(path, pattern):
    """True when the path is the acceptance file of an intent."""
    return bool((pattern and pattern.match(path)) or ACCEPTANCE_NAME.match(path.rsplit("/", 1)[-1]))


def record(text, name):
    """The value of a line such as "Acceptance-Locked: 1a2b3c4" in the "Acceptance checks"
    section of an intent: the last such line, without backticks. None if there is none."""
    found = re.findall(r"^%s:[ \t]*`?([^`\s]+)`?" % re.escape(name), section(text, "Acceptance checks"), re.M)
    return found[-1] if found else None


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


def earlier_review(root, target, remit, lock="Tests-Locked"):
    """The commit that an earlier review of this remit judged, and the problems that it
    found. The newest result is in the folder, or else in the newest commit that has it.
    None when there is no earlier result, or its packet does not say what it judged. For
    the acceptance checks of an intent, the lock is "Acceptance-Locked"."""
    result, packet = target / "result.md", target / "packet.md"
    found = None
    if result.exists():
        found = result.read_text(), (packet.read_text() if packet.exists() else "")
    else:
        path = result.relative_to(root).as_posix()
        for sha in git(root, "log", "--format=%H", "--", path).split():
            text = show(root, sha, path)
            if text is not None:
                found = text, show(root, sha, packet.relative_to(root).as_posix()) or ""
                break
    if not found:
        return None
    text, old_packet = found
    locks = re.findall(r"^%s:\s*([0-9a-f]{7,40})\b" % lock, old_packet, re.M)
    made = re.findall(r"^Made at:\s*([0-9a-f]{7,40})\b", old_packet, re.M)
    shas = (locks[-1:] if remit == "tests" else []) + made[:1]
    if not shas:
        return None
    problems = re.search(r"^[#*_ \t]*Problems\b[*_:]*(.*?)(?=^[^\s-]|\Z)", text,
                         re.M | re.S | re.I)
    problems = problems.group(1).strip() if problems else ""
    if problems.lower().strip("-. ") in ("", "none"):
        # If this cannot find the problems of a failed result, the whole result goes in.
        # Thus, no problem is lost.
        passed = re.match(r"\s*Result:\s*pass\b", text, re.I)
        problems = "none" if passed else fence(text)
    return shas[0], problems


def re_review(remit, sha, problems, diff):
    """The section that makes a packet a re-review."""
    judged = "the checks locked at" if remit == "tests" else "this change at"
    rule = ("Do not raise a new problem on material that did not change. This rule also applies"
            "\nto a problem that the earlier review missed.")
    if remit == "tests":
        rule += ('\nWrite a "Wrong versions" line only for each check that changed. If no check'
                 '\nchanged, write "none" under "Wrong versions".')
    return "\n".join([
        "## Re-review\n",
        "Earlier review: %s\n" % sha,
        "An earlier review of this remit judged %s %s. Judge only these two things:\n"
        % (judged, sha[:12]),
        '1. Each earlier problem below. If the problem is not fixed, list it again under'
        ' "Problems".',
        "2. The changes since the earlier review, in the diff below. List a new problem only",
        "   where a changed line causes the problem.\n",
        rule + "\n",
        "### Earlier problems\n", problems + "\n",
        "### Changes since the earlier review\n",
        (fence(diff) if diff.strip() else "Nothing changed.") + "\n"])


def diff_since(root, sha, files):
    """The diff of the files from the commit to HEAD. None if git cannot make it."""
    if not files:
        return ""
    out = subprocess.run(["git", "diff", sha, "HEAD", "--", *files], cwd=root,
                         capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def unchanged_since(root, sha, path):
    """True when the file is the same now as at the commit."""
    then = subprocess.run(["git", "rev-parse", "-q", "--verify", "%s:%s" % (sha, path)],
                          cwd=root, capture_output=True, text=True).stdout.strip()
    now = git(root, "hash-object", path).strip()
    return bool(then) and then == now


def writing_check(root, base, files):
    """The packet section with the writing check of the lines this change wrote."""
    title = "## Writing check\n\n"
    if not files:
        return title + "No text files changed.\n"
    done = subprocess.run([sys.executable, str(WRITING_CHECK), "--since", base, *files],
                          cwd=root, capture_output=True, text=True)
    return title + ("`pdlc/bin/check_writing.py --since %s` on %s:\n\n%s\n"
                    % (base, ", ".join(files), fence(done.stdout + done.stderr)))


def intent_packet(root, intent):
    """The tests packet for the acceptance checks of an intent."""
    found = sorted((root / "pdlc" / "inbox").glob(intent + "-*.md"))
    if not found:
        print("No intent found for %s" % intent)
        return 1
    text = found[0].read_text()
    checks, lock = record(text, "Acceptance-File"), record(text, "Acceptance-Locked")
    if not checks or checks == "none":
        print("%s names no Acceptance-File, so it has no acceptance checks to review" % intent)
        return 1
    if not lock or not re.match(r"[0-9a-f]{7,40}$", lock):
        print("Lock the acceptance checks of %s first: its Acceptance-Locked has no hash" % intent)
        return 1

    reqs = re.findall(r"\b((?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+)\b", section(text, "Requirements"))
    changes, relies = [], []
    for change in dict.fromkeys(re.findall(r"\bCH-\d+\b", section(text, "Changes"))):
        specs = sorted((root / "pdlc" / "changes").glob(change + "-*/change.md"))
        spec = specs[0].read_text() if specs else ""
        title = re.search(r"^# .*$", spec, re.M)
        changes.append("### %s\n\n%s\n" % (title.group(0)[2:] if title else change,
                                            fence(section(spec, "Interface").strip() or "(no Interface)")))
        relies += re.findall(r"\b((?:JOB|CAP|DES)-[a-z0-9-]+)\b", section(spec, "Relies on"))

    target = root / "pdlc" / "acceptance" / found[0].stem / "review" / "tests"
    earlier = earlier_review(root, target, "tests", lock="Acceptance-Locked")
    diff = diff_since(root, earlier[0], [checks]) if earlier else None
    earlier = earlier + (diff,) if diff is not None else None
    remit = root / "pdlc" / "reviews" / "tests.md"
    path = root / checks
    out = ["# Review packet · %s · tests (acceptance checks)\n" % found[0].stem,
           "Judge only what is in this packet. Write your result next to it, in result.md.\n",
           "Made at: %s\n" % git(root, "rev-parse", "HEAD").strip(),
           "Acceptance-Locked: %s\n" % lock,
           "These are the acceptance checks of an intent. Judge them by the section \"Acceptance",
           "checks of an intent\" of the remit below, and by its \"Wrong versions\".\n"]
    if earlier:
        out.append(re_review("tests", *earlier))
    out += [(remit.read_text() if remit.exists() else "# Remit: tests\n").strip() + "\n",
            "## The intent\n", fence(text), "\n## The requirements, in full\n"]
    out += [requirement_text(root, r) + "\n" for r in dict.fromkeys(reqs)]
    out.append("## The interface of each change of the intent\n")
    out += changes
    out.append("## Specs the changes rely on\n")
    for spec_id in dict.fromkeys(relies):
        if spec_id != "DES-writing-style":
            spec = spec_file(root, spec_id)
            out.append("### %s\n\n%s\n" % (spec_id, fence(spec.read_text()) if spec.exists() else "(not found)"))
    out += ["## The acceptance checks\n", "### %s\n" % checks,
            fence(path.read_text(errors="replace") if path.exists() else "(missing)") + "\n"]
    # A check of a requirement that this intent changes or retires leaves the acceptance file
    # of the earlier intent. The lock commit holds each such removal.
    pattern = acceptance_file(root)
    touched = [f for f in git(root, "diff", "--name-only", lock + "~1", lock).splitlines()
               if f != checks and is_acceptance(f, pattern)]
    out.append("## Checks removed from earlier intents\n")
    out.append(fence(git(root, "diff", lock + "~1", lock, "--", *touched)) + "\n" if touched
               else "None. The lock changed no acceptance file of an earlier intent.\n")
    target.mkdir(parents=True, exist_ok=True)
    (target / "packet.md").write_text("\n".join(out) + "\n")
    (target / "result.md").unlink(missing_ok=True)
    print("wrote %s" % (target / "packet.md").relative_to(root).as_posix())
    return 0


def main(argv, root=Path(".")):
    verify = "--verify" in argv[1:]
    args = [a for a in argv[1:] if a != "--verify"]
    if not args:
        print(__doc__)
        return 1
    if args[0].startswith("IN-"):
        return intent_packet(root, args[0])
    folders = sorted(p.parent for p in (root / "pdlc" / "changes").glob(args[0] + "-*/change.md"))
    if not folders:
        print("No change spec found for %s" % args[0])
        return 1
    folder = folders[0]
    change = (folder / "change.md").read_text()
    base = field(change, "Base") or "main"

    checks = re.findall(r"^-\s+`?([^`\s]+)`?", section(change, "Check files"), re.M)
    checks = [c for c in checks if c.lower() != "none"]
    listed = subprocess.run(["git", "diff", "--name-only", base + "...HEAD"], cwd=root,
                            capture_output=True, text=True)
    if listed.returncode != 0:
        print("Can't diff against %s: %s" % (base, listed.stderr.strip()))
        return 1
    changed = [f for f in listed.stdout.splitlines() if f]
    tests = [f for f in changed if f in checks]
    acceptance = acceptance_file(root)
    code = [f for f in changed if f not in checks and not f.startswith("pdlc/")
            and not is_acceptance(f, acceptance)]
    change_spec = (folder / "change.md").relative_to(root).as_posix()
    text_files = [f for f in changed if f.endswith(".md") and (root / f).exists()
                  and (not f.startswith("pdlc/") or f.startswith("pdlc/specs/") or f == change_spec)]

    reqs = re.findall(r"^### ((?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+)", section(change, "Requirements"), re.M)
    relies = re.findall(r"\b((?:JOB|CAP|DES)-[a-z0-9-]+)\b", section(change, "Relies on"))
    scope = re.match(r"(?:JOB|CAP|DES)-[a-z0-9-]+", field(change, "Scope") or "")
    spec = ["## The change spec\n", fence(change)]
    if scope:
        spec += ["\n## The spec it covers: title and summary\n", fence(spec_head(root, scope.group(0)))]
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
    head = git(root, "rev-parse", "HEAD").strip()
    if verify:
        chosen = [r for r in remits(root) if r != "tests"] + args[1:]
    else:
        chosen = args[1:] or remits(root)
    for remit in dict.fromkeys(chosen):
        remit_file = root / "pdlc" / "reviews" / (remit + ".md")
        remit_text = remit_file.read_text() if remit_file.exists() else "# Remit: %s\n" % remit
        target = folder / "review" / remit
        if remit == "compliance" and not compliance_applies(remit_text, changed):
            target.mkdir(parents=True, exist_ok=True)
            (target / "packet.md").unlink(missing_ok=True)
            (target / "result.md").write_text(
                "Result: pass\n\nRemit: compliance\n\nProblems: none\n\nFollow-ups: none\n\nNotes:\n"
                "- Not applicable. The project lists no compliance rules, and the change touches no\n"
                "  dependency file. make_packets.py wrote this result, so no reviewer is needed.\n")
            print("wrote %s (compliance does not apply: no rules and no dependency file. Start no reviewer for it.)"
                  % (target / "result.md").relative_to(root).as_posix())
            continue
        judged = tests if remit == "tests" else code
        if remit == "specification":
            judged = list(dict.fromkeys(code + text_files))
        earlier = earlier_review(root, target, remit)
        diff = diff_since(root, earlier[0], judged) if earlier else None
        earlier = earlier + (diff,) if diff is not None else None
        out = ["# Review packet · %s · %s\n" % (folder.name, remit),
               "Judge only what is in this packet. Write your result next to it, in result.md.\n",
               "Made at: %s\n" % head]
        if earlier:
            out.append(re_review(remit, *earlier))
        out += [remit_text.strip() + "\n", spec_for["specification" if remit == "specification" else "other"]]
        if remit == "tests":
            out.append(material(root, base, tests, "The checks"))
        else:
            out.append(material(root, base, code, "The code"))
        if remit == "specification":
            out.append(writing_check(root, earlier[0] if earlier else base, text_files))
        if remit == "specification" and frames:
            out.append("## Visual review frames\n\nRead each frame to see the change working:\n")
            for frame in frames:
                path = frame.relative_to(root).as_posix()
                same = earlier and unchanged_since(root, earlier[0], path)
                out.append("- %s%s" % (path, " (unchanged since the earlier review)" if same else ""))
        target.mkdir(parents=True, exist_ok=True)
        (target / "packet.md").write_text("\n".join(out) + "\n")
        stale = target / "result.md"
        if stale.exists():
            stale.unlink()
        print("wrote %s" % (target / "packet.md").relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
