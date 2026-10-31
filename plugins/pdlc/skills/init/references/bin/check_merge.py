#!/usr/bin/env python3
"""pdlc merge check.

A change may merge only when:
  - every requirement it lists is verified (and every retired one is gone from its spec);
  - each assumption marker in its change spec and requirements starts with "(assumed",
    with no emphasis around it: "(assumed)", "(assumed limit)", "(assumed: a reason)";
  - its checks are locked, and no check file changed after the lock;
  - the tests review judged the checks as they are locked now: its packet carries the
    current lock;
  - the tests review names a wrong version of the code that each check fails on. A
    re-review (its packet says "Earlier review:") names one only for each check that
    changed since the earlier lock. If no check changed, it needs none;
  - a change with "Tests-Locked: acceptance" is the only change of its intent, lists no check
    files, and its intent has locked acceptance checks. The acceptance review then stands
    for its tests review, and the tests remit needs no result of its own;
  - every review remit named in pdlc/config.md passed;
  - the branch merges into main without conflicts;
  - its intent is in pdlc/inbox, and every other change of the intent is "in review" or
    "merged" on its own branch, so the intent's changes merge together;
  - the acceptance checks of its intent are locked ("Acceptance-Locked:" in the intent), the
    tests review judged them at that lock with "Wrong versions", and the acceptance file did
    not change after the lock;
  - the acceptance checks passed at the top of the stack: the intent on the branch of its
    last change says "Acceptance-Passed: <hash>", that commit comes after the lock, and only
    pdlc/ files changed after it. A change that only retires requirements is permitted
    to have "Acceptance-Locked: none";
  - it hasn't merged already: a merged change's branch takes no new commits.

Usage:
  python3 pdlc/bin/check_merge.py CH-0031   check one change
  python3 pdlc/bin/check_merge.py           check the change for the current branch, or,
                                            if no change uses this branch, every change
                                            with status "in review"

In CI, the script reads the current branch from GITHUB_HEAD_REF when that variable is set.
Run it from the project root. Exit code 0 means the change may merge.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

REQ = re.compile(r"^### ((?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+)\b(.*)$", re.M)
KINDS = {"JOB": "jobs", "CAP": "capabilities", "DES": "design"}
DEFAULT_REMITS = ["tests", "specification", "security", "quality", "compliance", "privacy"]
READY = ("in review", "merged")
HASH = re.compile(r"^[0-9a-f]{7,40}$")
# A marker with emphasis (*(assumed)*), or brackets that hold the word "assumed". A marker
# passes when it starts with "(assumed".
MARKER = re.compile(r"[*_]+\(assumed\b[^()\n]*\)[*_]+|\([^()\n]*\bassumed\b[^()\n]*\)", re.I)


def section(text, title):
    """The text under a '## title' heading, up to the next '## ' heading."""
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else ""


def requirement_text(root, req_id):
    """The requirement's heading and text in its spec, or None if it isn't there."""
    spec_id = req_id.rsplit(".", 1)[0]
    spec = root / "pdlc" / "specs" / KINDS[spec_id.split("-", 1)[0]] / (spec_id + ".md")
    if not spec.exists():
        return None
    text = spec.read_text()
    heading = re.search(r"^### %s\b.*$" % re.escape(req_id), text, re.M)
    if not heading:
        return None
    body = text[heading.end():]
    end = re.search(r"^##", body, re.M)
    return heading.group(0) + (body[:end.start()] if end else body)


def status_of(root, req_id):
    """The requirement's status in its spec, 'missing' if it has none, None if not there."""
    body = requirement_text(root, req_id)
    if body is None:
        return None
    status = re.search(r"^Status:\s*([a-z ]+?)\s*(?:·|$)", body, re.M)
    return status.group(1) if status else "missing"


def marker_problems(where, text):
    """Each assumption marker in the text that does not start with "(assumed"."""
    return ['%s: write "%s" so it starts with "(assumed", for example "(assumed)"'
            % (where, found.group(0)) for found in MARKER.finditer(text or "")
            if not found.group(0).startswith("(assumed")]


def remits(root):
    """The review remits pdlc/config.md asks for."""
    config = root / "pdlc" / "config.md"
    text = config.read_text() if config.exists() else ""
    line = re.search(r"^- remits:\s*(.+)$", section(text, "Reviews"), re.M)
    if not line:
        return DEFAULT_REMITS
    return [r.strip() for r in line.group(1).split(",") if r.strip() and r.strip() != "none"]


def check_files(text):
    """The paths listed under '## Check files'."""
    paths = re.findall(r"^-\s+`?([^`\s]+)`?", section(text, "Check files"), re.M)
    return [p for p in paths if p.lower() != "none"]


def has_lock(packet, lock, name="Tests-Locked"):
    """True when the text of a tests packet carries this lock, copied from the change spec
    (Tests-Locked) or from the intent (Acceptance-Locked)."""
    seen = re.findall(r"^%s:\s*([0-9a-f]{7,40})\b" % name, packet or "", re.M)
    return bool(seen) and (seen[-1].startswith(lock) or lock.startswith(seen[-1]))


def reviewed_lock(folder, lock):
    """True when the tests packet carries this lock, copied from the change spec."""
    packet = folder / "review" / "tests" / "packet.md"
    return packet.exists() and has_lock(packet.read_text(), lock)


def wrong_version_lines(text):
    """The lines under "Wrong versions" in the text of a tests review's result."""
    block = re.search(r"^#*\s*Wrong versions:?\s*$(.*?)(?=^[^\s-]|\Z)", text or "", re.M | re.S)
    lines = re.findall(r"^\s*-\s+(.+?)\s*$", block.group(1), re.M) if block else []
    return [line for line in lines if line.lower() != "none"]


def wrong_versions(folder):
    """The lines under "Wrong versions" in the tests review's result."""
    result = folder / "review" / "tests" / "result.md"
    return wrong_version_lines(result.read_text() if result.exists() else "")


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def checks_unchanged_since_earlier_review(root, folder, lock, checks):
    """True when the tests packet is a re-review, and no check file changed between the
    lock that the earlier review judged and this lock."""
    packet = folder / "review" / "tests" / "packet.md"
    return unchanged_since_earlier_review(root, packet.read_text() if packet.exists() else "",
                                          lock, checks)


def unchanged_since_earlier_review(root, text, lock, checks):
    """True when the text of a tests packet is a re-review, and no check file changed
    between the lock that the earlier review judged and this lock."""
    earlier = re.search(r"^Earlier review:\s*([0-9a-f]{7,40})\b", text or "", re.M)
    if not earlier or not lock:
        return False
    diff = git(root, "diff", "--name-only", earlier.group(1), lock, "--", *checks)
    return diff.returncode == 0 and not diff.stdout.strip()


def field(text, name):
    """A header field of a change spec or intent, such as Status or Branch. The value is
    bare: "IN-0001 (poll-input-errors)" gives "IN-0001", and "`pdlc/CH-0001-x`" gives
    "pdlc/CH-0001-x"."""
    match = re.search(r"\b%s:[ \t]*([^·\n]*?)[ \t]*(?:·|$)" % name, text, re.M)
    if not match:
        return None
    value = match.group(1).replace("`", "")
    return re.sub(r"\s+\(.*\)$", "", value).strip()


def show(root, ref, path):
    """A file as it is on a branch, or None if git can't find it there."""
    out = git(root, "show", "%s:%s" % (ref, path))
    return out.stdout if out.returncode == 0 else None


def branches(root):
    """Every local and remote branch git knows."""
    out = git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
    return out.stdout.split() if out.returncode == 0 else []


def change_id(folder):
    """CH-0031 for the folder CH-0031-email-templates."""
    return "-".join(folder.name.split("-", 2)[:2])


def own_branch(root, path, refs):
    """The branch, as git knows it, that a change spec names as its own. None when the
    change has no branch."""
    for ref in refs:
        text = show(root, ref, path)
        branch = field(text, "Branch") if text else None
        if branch and branch != "none" and (ref == branch or ref.endswith("/" + branch)):
            return ref
    return None


def status_on_own_branch(root, path, refs):
    """A change's status on its own branch, the one its change spec names. A change whose
    branch is gone counts as merged if main's copy reads "in review" or "merged". None
    when it has no branch."""
    ref = own_branch(root, path, refs)
    if ref:
        return field(show(root, ref, path), "Status")
    on_main = show(root, "main", path) or show(root, "origin/main", path)
    status = field(on_main, "Status") if on_main else None
    return status if status in READY else None


def partners_not_ready(root, folder, text):
    """Problems with the other changes of this change's intent: each must be ready too."""
    intent = field(text, "Intent")
    if not intent or intent == "none":
        return []
    found = sorted((root / "pdlc" / "inbox").glob("%s-*.md" % intent))
    if not found:
        return ["%s is not in pdlc/inbox, so the check cannot find the other changes of the "
                "intent" % intent]
    listed = re.findall(r"\bCH-\d+\b", section(found[0].read_text(), "Changes"))
    problems, refs = [], branches(root)
    for other in dict.fromkeys(listed):
        if other == change_id(folder):
            continue
        specs = sorted((root / "pdlc" / "changes").glob(other + "-*/change.md"))
        path = "pdlc/changes/%s/change.md" % specs[0].parent.name if specs else None
        status = status_on_own_branch(root, path, refs) if path else None
        if status is None:
            problems.append("%s of %s is not ready (no branch)" % (other, intent))
        elif status not in READY:
            problems.append("%s of %s is not ready (status: %s)" % (other, intent, status))
    return problems


def record(text, name):
    """The value of a line such as "Acceptance-Locked: 1a2b3c4" in the "Acceptance checks"
    section of an intent: the last such line, without backticks. None if there is none."""
    found = re.findall(r"^%s:[ \t]*`?([^`\s]+)`?" % re.escape(name),
                       section(text or "", "Acceptance checks"), re.M)
    return found[-1] if found else None


def changed_files(root, old, new, *paths):
    """The files that differ between two commits, or None if git can't compare them."""
    out = git(root, "diff", "--name-only", old, new, "--", *paths)
    return out.stdout.split() if out.returncode == 0 else None


def is_ancestor(root, old, new):
    return git(root, "merge-base", "--is-ancestor", old, new).returncode == 0


def acceptance_problems(root, folder, text, reqs):
    """Problems with the acceptance checks of this change's intent. The checks must be
    locked, reviewed at the lock, unchanged since the lock, and recorded as passing at the
    top of the stack: the branch of the last change of the intent."""
    intent = field(text, "Intent")
    found = sorted((root / "pdlc" / "inbox").glob("%s-*.md" % intent)) if intent else []
    if not found:
        return []  # partners_not_ready names the missing intent
    listed = list(dict.fromkeys(re.findall(r"\bCH-\d+\b", section(found[0].read_text(), "Changes"))))
    top_id = listed[-1] if listed else change_id(folder)
    # The top of the stack is the branch of the last change. In CI, HEAD can be a merge of
    # the pull request into main, so HEAD stands in only when git knows no such branch.
    specs = sorted((root / "pdlc" / "changes").glob(top_id + "-*/change.md"))
    top = own_branch(root, specs[0].relative_to(root).as_posix(), branches(root)) if specs else None
    if not top and top_id == change_id(folder):
        top = "HEAD"

    def read(path):
        """A file at the top of the stack. This checkout stands in when the top is HEAD, or
        when the top change has no branch yet."""
        if top and top != "HEAD":
            return show(root, top, path)
        return (root / path).read_text() if (root / path).exists() else None

    intent_text = read(found[0].relative_to(root).as_posix()) or found[0].read_text()
    checks, lock = record(intent_text, "Acceptance-File"), record(intent_text, "Acceptance-Locked")
    passed = record(intent_text, "Acceptance-Passed")
    if not lock or not HASH.match(lock):
        if lock == "none" and reqs and all("(retire)" in rest for _, rest in reqs):
            return []
        return ["acceptance checks of %s are not locked (no Acceptance-Locked hash in the "
                "intent); run /pdlc:acceptance" % intent]
    if not checks or checks == "none":
        return ["%s names no Acceptance-File, so the check cannot find its acceptance checks"
                % intent]
    problems = []

    if "tests" in remits(root):
        review = "pdlc/acceptance/%s/review/tests/" % found[0].stem
        packet, result = read(review + "packet.md"), read(review + "result.md")
        if not has_lock(packet, lock, "Acceptance-Locked"):
            problems.append("acceptance review of %s is not of the current lock %s; review the "
                            "acceptance checks again" % (intent, lock))
        if result is None:
            problems.append("acceptance review of %s has no result. Run python3 "
                            "pdlc/bin/make_packets.py %s, and start a reviewer" % (intent, intent))
        elif not re.match(r"\s*Result:\s*pass\b", result, re.I):
            problems.append("acceptance review of %s did not pass" % intent)
        else:
            lines = wrong_version_lines(result)
            if not lines and not unchanged_since_earlier_review(root, packet, lock, [checks]):
                problems.append('acceptance review of %s lists no "Wrong versions"; review the '
                                'acceptance checks again' % intent)
            for line in lines:
                if re.search(r"·\s*passes\b", line, re.I):
                    problems.append("acceptance review of %s: a check passes a wrong version: %s"
                                    % (intent, line))

    # A change below a later lock holds an older copy of the file. That copy must not change
    # after the change got it, so the diff starts where this branch and the lock meet.
    since = git(root, "merge-base", "HEAD", lock).stdout.strip()
    changed = changed_files(root, since, "HEAD", checks) if since else None
    if changed is None:
        problems.append("can't compare the acceptance checks of %s with the lock %s" % (intent, lock))
    locked_changed = list(changed or [])

    if not top:
        return problems  # partners_not_ready says that the top change has no branch
    if not passed or not HASH.match(passed):
        problems.append("acceptance checks of %s are not ready: no Acceptance-Passed at the top "
                        "of the stack (%s)" % (intent, top_id))
    elif not is_ancestor(root, lock, passed):
        problems.append("Acceptance-Passed %s of %s does not come after its lock %s; run the acceptance "
                        "checks again" % (passed, intent, lock))
    elif not is_ancestor(root, passed, top):
        problems.append("Acceptance-Passed %s of %s is not on the branch of %s; run the acceptance "
                        "checks there" % (passed, intent, top_id))
    else:
        locked_changed += changed_files(root, lock, passed, checks) or []
        later = [f for f in changed_files(root, passed, top) or [] if not f.startswith("pdlc/")]
        if later:
            problems.append("files changed after the acceptance checks of %s passed: %s; run them "
                            "again" % (intent, ", ".join(later)))
    problems += ["changed after the acceptance checks were locked: %s" % path
                 for path in dict.fromkeys(locked_changed)]
    return problems


def merged_already(root, folder):
    """True when main says this change merged, yet this branch has commits main doesn't."""
    on_main = show(root, "main", "pdlc/changes/%s/change.md" % folder.name)
    if not on_main or field(on_main, "Status") != "merged":
        return False
    ahead = git(root, "rev-list", "--count", "main..HEAD")
    return ahead.returncode == 0 and int(ahead.stdout.strip() or 0) > 0


def conflicts_with_main(root):
    """Files that conflict when this branch merges into main. Empty when it merges
    cleanly, when there is no main, when this is main, or when git can't tell."""
    try:
        head = git(root, "rev-parse", "--verify", "-q", "HEAD")
        main = git(root, "rev-parse", "--verify", "-q", "main")
        if head.returncode or main.returncode or head.stdout == main.stdout:
            return []
        out = git(root, "merge-tree", "--write-tree", "--name-only", "--no-messages",
                  "main", "HEAD")
    except OSError:
        return []
    if out.returncode != 1:
        return []
    return sorted(set(out.stdout.split()[1:]))


def acceptance_serves(root, folder, text, checks):
    """Problems with a change that has "Tests-Locked: acceptance". The acceptance checks of
    its intent are also its checks. That holds only when the change lists no check files,
    when it is the only change of its intent, and when the intent has locked acceptance
    checks. The review and the pass of those checks come from acceptance_problems."""
    problems = []
    if checks:
        problems.append('Tests-Locked: acceptance needs "- none" under "Check files"')
    intent = field(text, "Intent")
    found = sorted((root / "pdlc" / "inbox").glob("%s-*.md" % intent)) if intent else []
    if not found:
        return problems  # partners_not_ready names the missing intent
    intent_text = found[0].read_text()
    listed = list(dict.fromkeys(re.findall(r"\bCH-\d+\b", section(intent_text, "Changes"))))
    if listed != [change_id(folder)]:
        problems.append("Tests-Locked: acceptance is only for the only change of an intent. "
                        "%s lists %s. Run /pdlc:tests" % (intent, ", ".join(listed) or "no changes"))
    lock = record(intent_text, "Acceptance-Locked")
    if not lock or not HASH.match(lock):
        problems.append("Tests-Locked: acceptance needs the acceptance checks of %s locked"
                        % intent)
    return problems


def check_change(root, folder):
    """A list of problems with one change. Empty means it may merge."""
    problems = []
    text = (folder / "change.md").read_text()

    reqs = REQ.findall(section(text, "Requirements"))
    if not reqs:
        problems.append("lists no requirements")
    for req_id, rest in reqs:
        status = status_of(root, req_id)
        if "(retire)" in rest:
            if status is not None:
                problems.append("%s is marked (retire) but is still in its spec" % req_id)
        elif status is None:
            problems.append("%s is not in its spec" % req_id)
        elif status != "verified":
            problems.append("%s is %s, not verified" % (req_id, status))

    problems += marker_problems("change.md", text)
    for req_id, _ in reqs:
        problems += marker_problems(req_id, requirement_text(root, req_id))

    checks = check_files(text)
    # A re-lock may leave the older line in place. The newest (last) line counts. The value
    # "acceptance" says that the acceptance checks of the intent are also the checks of this
    # change, so this change has no tests lock and no tests review of its own.
    values = re.findall(r"^Tests-Locked:[ \t]*`?([^`\s]+)`?", text, re.M)
    by_acceptance = bool(values) and values[-1] == "acceptance"
    locks = list(re.finditer(r"^Tests-Locked:\s*([0-9a-f]{7,40})\b", text, re.M))
    lock = locks[-1] if locks and not by_acceptance else None
    if by_acceptance:
        problems += acceptance_serves(root, folder, text, checks)
    elif checks and not lock:
        problems.append("tests are not locked (no Tests-Locked line)")
    elif checks:
        diff = git(root, "diff", "--name-only", lock.group(1), "HEAD", "--", *checks)
        if diff.returncode != 0:
            problems.append("can't compare tests with the lock %s" % lock.group(1))
        for path in diff.stdout.split():
            problems.append("changed after the tests were locked: %s" % path)

    wanted = remits(root)
    if lock and "tests" in wanted and not reviewed_lock(folder, lock.group(1)):
        problems.append("tests review is not of the current lock %s; review the checks again"
                        % lock.group(1))

    for remit in wanted:
        if remit == "tests" and by_acceptance:
            continue  # acceptance_problems reads the acceptance review in its place
        result = folder / "review" / remit / "result.md"
        if not result.exists():
            problems.append("%s review has no result. Run python3 pdlc/bin/make_packets.py %s %s, "
                            "and start a reviewer if it writes a packet"
                            % (remit, change_id(folder), remit))
        elif not re.match(r"\s*Result:\s*pass\b", result.read_text(), re.I):
            problems.append("%s review did not pass" % remit)

    if (checks and not by_acceptance and "tests" in wanted
            and (folder / "review" / "tests" / "result.md").exists()):
        lines = wrong_versions(folder)
        if not lines and not checks_unchanged_since_earlier_review(
                root, folder, lock.group(1) if lock else None, checks):
            problems.append('tests review lists no "Wrong versions"; review the checks again')
        for line in lines:
            if re.search(r"·\s*passes\b", line, re.I):
                problems.append("tests review: a check passes a wrong version: %s" % line)

    for path in conflicts_with_main(root):
        problems.append("conflicts with main: %s" % path)

    problems += partners_not_ready(root, folder, text)
    problems += acceptance_problems(root, folder, text, reqs)

    if merged_already(root, folder):
        problems.append("%s already merged; new commits on its branch won't reach main. "
                        "Start a new change." % change_id(folder))
    return problems


def current_branch(root):
    """The branch being merged: GITHUB_HEAD_REF in CI, else git's current branch."""
    if os.environ.get("GITHUB_HEAD_REF"):
        return os.environ["GITHUB_HEAD_REF"]
    try:
        out = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    except OSError:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def main(argv, root=Path("."), branch=None):
    changes = root / "pdlc" / "changes"
    everything = sorted(p.parent for p in changes.glob("CH-*/change.md"))
    if len(argv) > 1:
        folders = [f for f in everything if f.name.startswith(argv[1] + "-")]
        if not folders:
            print("No change spec found for %s" % argv[1])
            return 1
    else:
        branch = branch or current_branch(root)
        folders = [f for f in everything
                   if branch and field((f / "change.md").read_text(), "Branch") == branch]
        if not folders:
            folders = [f for f in everything
                       if field((f / "change.md").read_text(), "Status") == "in review"]
    failed = False
    for folder in folders:
        problems = check_change(root, folder)
        name = change_id(folder)
        if problems:
            failed = True
            print("FAIL %s" % name)
            for problem in problems:
                print("  - %s" % problem)
        else:
            print("ok   %s" % name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
