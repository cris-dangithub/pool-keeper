#!/usr/bin/env sh
# Install pool-keeper for Codex and/or Claude Code (user level) from a clone of this repo, by
# linking skills/pool-keeper into the agents' skill folders. Standard library Python only:
# there is no environment to create.
#
#   ./install.sh            # codex + claude
#   ./install.sh codex      # only Codex   (~/.codex/skills/pool-keeper)
#   ./install.sh claude     # only Claude  (~/.claude/skills/pool-keeper)
#
# Claude Code users can also install it as a plugin instead (see README).
set -eu
SRC="$(cd "$(dirname "$0")" && pwd)/skills/pool-keeper"
TARGETS="${*:-codex claude}"
PY="$(command -v python3 || command -v python)"

for t in $TARGETS; do
  case "$t" in
    codex)  DEST="${CODEX_HOME:-$HOME/.codex}/skills/pool-keeper" ;;
    claude) DEST="$HOME/.claude/skills/pool-keeper" ;;
    *) echo "unknown target: $t (use codex or claude)"; exit 2 ;;
  esac
  mkdir -p "$(dirname "$DEST")"
  if [ -e "$DEST" ] && [ ! -L "$DEST" ]; then
    echo "skip $t: $DEST exists and is not a link (remove it first)"; continue
  fi
  ln -sfn "$SRC" "$DEST"
  echo "linked $DEST -> $SRC"
done

"$PY" "$SRC/pk.py" doctor || true
echo
echo "Done. Open your agent anywhere and say: set up pool-keeper (or attach your CV)."
