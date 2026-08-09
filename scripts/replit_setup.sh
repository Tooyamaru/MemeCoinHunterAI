#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

required_files=(
  "REPLIT_RULES.md"
  "PROJECT_STATE.md"
  "README.md"
  "docs/MASTER_BLUEPRINT.md"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    printf 'ERROR: required file is missing: %s\n' "$file" >&2
    exit 1
  fi
done

mkdir -p apps/dashboard backend/api workers \
  core/data core/signals core/opportunity core/decision core/risk \
  core/execution core/learning database tests

printf 'Meme Coin Hunter AI foundation is ready.\n'
printf 'Read REPLIT_RULES.md, then PROJECT_STATE.md before continuing.\n'
printf 'No secrets, credentials, dependencies, or future trading services were configured.\n'
