#!/usr/bin/env bash
set -euo pipefail

# --- CONFIG ---
APP="philly-p-sniper-web"
FILE="hard_rock_model.py"
COMMIT_MSG="Fix bankroll to reflect active exposure"
HEROKU_REMOTE="heroku"
# If your Heroku primary branch is master, change TARGET_BRANCH to "master"
TARGET_BRANCH="main"
# ----------------

echo "1/ Verifying git repo..."
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: Not inside a git repository. Abort."
  exit 1
fi

echo "2/ Checking for changes to ${FILE}..."
if git diff --quiet -- "$FILE" && git ls-files --error-unmatch "$FILE" >/dev/null 2>&1; then
  echo "No changes detected for ${FILE} (or file missing from index). Will still push current branch to Heroku."
else
  echo "Staging and committing ${FILE} and dashboard.py..."
  git add dashboard.py
  git add "$FILE"
  git commit -m "$COMMIT_MSG"
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

echo "3/ Ensuring Heroku remote exists..."
if ! git remote | grep -q "^${HEROKU_REMOTE}$"; then
  echo "Adding Heroku git remote for app ${APP}..."
  heroku git:remote -a "$APP"
fi

echo "4/ Pushing $CURRENT_BRANCH to Heroku ${TARGET_BRANCH}..."
git push "$HEROKU_REMOTE" "$CURRENT_BRANCH":"$TARGET_BRANCH"

echo "5/ Running one-off dyno: python ${FILE} (output -> run_output.txt)"
heroku run python "$FILE" --app "$APP" > run_output.txt 2>&1

echo "6/ Showing relevant error/debug lines from run_output.txt"
egrep -n "Traceback|calculate_match_stats|TypeError|\[ERROR\]" run_output.txt || echo "No matching lines found."

echo ""
echo "You can inspect the full output at ./run_output.txt"
echo "To tail live Heroku logs: heroku logs --tail --app $APP"