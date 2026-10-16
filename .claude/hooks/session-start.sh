#!/bin/bash
# Sets up a Claude Code cloud session: Cloudflare tools plus Pat's skills.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

repo="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Cloudflare: cf CLI, skills and MCP servers
command -v cf >/dev/null || npm install -g cf
claude plugin marketplace add cloudflare/skills
claude plugin install cloudflare@cloudflare
mkdir -p ~/.claude
grep -qs 'use the cf CLI' ~/.claude/CLAUDE.md \
  || echo 'When interacting with Cloudflare, use the cf CLI unless the project has a Wrangler configuration file.' >> ~/.claude/CLAUDE.md

# Pat's skills: every top-level folder with a SKILL.md, plus the pdlc plugin
mkdir -p ~/.claude/skills
for d in "$repo"/*/; do
  [ -f "$d/SKILL.md" ] && cp -r "$d" ~/.claude/skills/
done
claude plugin marketplace add ptetau/pskills
claude plugin install pdlc@pskills --scope user

# /argue needs z3; the pdlc tests need pytest
pip install -q z3-solver pytest
