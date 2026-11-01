#!/usr/bin/env python3
"""Make plugins/pdlc/skills/upgrade/references/known.json.

The file holds, for each pdlc file that a project can have (a path under pdlc/), the hash of
each version that the git history of this repository has. The upgrade script uses it for a
project with no pdlc/version.json: a file with a known hash was not edited.

Usage:
  python3 scripts/pdlc_known_files.py           write known.json
  python3 scripts/pdlc_known_files.py --check   write nothing; exit 1 when a hash is missing
                                                source file is missing from known.json
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins/pdlc"
REFS = "plugins/pdlc/skills/init/references"
KNOWN = PLUGIN / "skills/upgrade/references/known.json"

spec = importlib.util.spec_from_file_location("upgrade", PLUGIN / "skills/upgrade/scripts/upgrade.py")
upgrade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade)


def git(*args):
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else None


def project_path(source):
    """The path under pdlc/ of a source path under references/, or None when it is not managed."""
    rel = source[len(REFS) + 1:]
    folder, _, name = rel.partition("/")
    if not name or "/" in name or name in upgrade.SKIP_NAMES:
        return None
    if folder == "templates":
        return None if name == "config.md" else ("README.md" if name == "README.md" else rel)
    if folder == "defaults":
        return "specs/design/" + name
    return rel if folder in ("ports", "adapters", "bin", "reviews") else None


def versions(source):
    """The text of each git version of a source path."""
    commits = (git("log", "--all", "--full-history", "--format=%H", "--", source) or "").split()
    texts = []
    for commit in commits:
        text = git("show", "%s:%s" % (commit, source))
        if text is not None:
            texts.append(text)
    return texts


def build():
    if (git("rev-parse", "--is-shallow-repository") or "").strip() == "true":
        print("This repository is shallow, so its history is incomplete. "
              "Run git fetch --unshallow and try again.")
        sys.exit(1)
    sources = set()
    for line in (git("log", "--all", "--full-history", "--name-only", "--format=", "--", REFS) or "").splitlines():
        if line.startswith(REFS + "/"):
            sources.add(line)
    known = {}
    for source in sorted(sources):
        path = project_path(source)
        if not path:
            continue
        hashes = set(known.get(path, []))
        for text in versions(source):
            if path.startswith("specs/design/"):
                text = upgrade.strip_question(text)
            hashes.add(upgrade.digest_for(path, text))
        known[path] = sorted(hashes)
    # The working tree counts too, so that the list is right before the commit of a change.
    for path, text in upgrade.plugin_files(str(PLUGIN)).items():
        known[path] = sorted(set(known.get(path, [])) | {upgrade.digest_for(path, text)})
    return known


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        try:
            known = json.loads(KNOWN.read_text())
        except (OSError, ValueError):
            print("known.json is missing or not valid. Run python3 scripts/pdlc_known_files.py")
            return 1
        wanted = build()
        missing = [path for path, hashes in sorted(wanted.items())
                   if any(h not in known.get(path, []) for h in hashes)]
        for path in missing:
            print("known.json lacks a hash for pdlc/%s" % path)
        if missing:
            print("Run python3 scripts/pdlc_known_files.py and commit known.json.")
            return 1
        print("known.json covers every current source file.")
        return 0
    known = build()
    KNOWN.parent.mkdir(parents=True, exist_ok=True)
    KNOWN.write_text(json.dumps(known, indent=1, sort_keys=True) + "\n")
    print("Wrote %s (%d paths)." % (KNOWN.relative_to(ROOT), len(known)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
