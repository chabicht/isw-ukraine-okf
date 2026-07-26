#!/usr/bin/env bash
set -euo pipefail

FILE="$1"
PROMPT="$(echo -e "please read okf.md and rules.md and incorporate the file $FILE\nyou're running in auto mode, so don't ask questions and complete the task autonomously.\nfeel free to spawn subagents as suitable.\nif you're done and the validation passes, commit the update under the date yyyy-mm-dd and with a short list of changes.")"

echo "Processing: $FILE"
git add "$FILE"
opencode run --auto "$PROMPT" 
