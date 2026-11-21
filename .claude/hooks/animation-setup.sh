#!/bin/bash
# SessionStart: make the animation skill's renderer use the Playwright that cloud
# sessions already ship with, so no `npm install` (and no Chromium download) is needed.
# On a machine where `npm install` was already run in the scripts folder, this does nothing.
DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}/.claude/skills/animation/scripts"
[ -d "$DIR" ] || exit 0
[ -e "$DIR/node_modules/playwright" ] && exit 0
GLOBAL="$(npm root -g 2>/dev/null)"
[ -d "$GLOBAL/playwright" ] || exit 0
mkdir -p "$DIR/node_modules"
ln -sfn "$GLOBAL/playwright" "$DIR/node_modules/playwright"
[ -d "$GLOBAL/playwright-core" ] && ln -sfn "$GLOBAL/playwright-core" "$DIR/node_modules/playwright-core"
exit 0
