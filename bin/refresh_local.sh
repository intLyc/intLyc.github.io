#!/usr/bin/env bash
# Refresh Google Scholar citation data from a residential IP (home Mac) and push
# the changes so the site rebuilds automatically.
#
# Why: Google Scholar blocks GitHub Actions datacenter IPs
# ("Cannot Fetch from Google Scholar"), so citations can ONLY be fetched from a
# non-datacenter IP. This script is invoked by the launchd agent
# com.intlyc.refresh (see ~/Library/LaunchAgents/com.intlyc.refresh.plist).
#
# Stars/visitors are NOT handled here — they refresh on CI during every deploy.
set -euo pipefail

# Operate on the repo that contains this script. When installed via the
# launchd agent we use a dedicated clone at ~/intlyc-refresh/intLyc.github.io
# (NOT ~/Documents) because macOS TCC blocks launchd-spawned processes from
# accessing the Documents folder. Override with the REPO env var if needed.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(dirname "$SCRIPT_DIR")}"
LOG="$HOME/Library/Logs/intlyc-refresh.log"

exec >>"$LOG" 2>&1
echo "=== refresh $(date '+%Y-%m-%d %H:%M:%S %z') in $REPO ==="

cd "$REPO" || { echo "repo not found: $REPO"; exit 1; }

# Bring the working tree up to date before writing/pushing.
git pull --rebase --autostash --quiet || echo "git pull skipped/failed"

# Locate a python3 that has `scholarly` installed (conda base on this Mac).
PYTHON="${REFRESH_PYTHON:-}"
if [ -z "$PYTHON" ]; then
  for c in \
    "$HOME/miniconda3/bin/python3" \
    "$HOME/anaconda3/bin/python3" \
    "$HOME/miniconda/bin/python3" \
    "/opt/homebrew/Caskroom/miniconda/base/bin/python3"; do
    if [ -x "$c" ]; then PYTHON="$c"; break; fi
  done
fi
PYTHON="${PYTHON:-python3}"

if ! "$PYTHON" bin/update_scholar_citations.py; then
  echo "citations fetch failed (no push)"
  exit 0
fi

if git diff --quiet -- _data/citations.yml; then
  echo "no citation changes"
else
  git add _data/citations.yml
  git -c user.name="intlyc-refresh" \
      -c user.email="intlyc-refresh@users.noreply.github.com" \
      commit -m "chore: auto-refresh Google Scholar citations"
  git push --quiet
  echo "pushed citation update (triggers deploy)"
fi
