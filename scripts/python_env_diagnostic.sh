#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

printf 'project_python_requirement: '
awk -F '"' '/^requires-python[[:space:]]*=/ { print $2; found=1; exit } END { if (!found) print "unknown" }' pyproject.toml

if command -v python >/dev/null 2>&1; then
  printf 'system_python: '
  python --version
else
  printf '%s\n' 'system_python: unavailable'
fi

if command -v uv >/dev/null 2>&1; then
  printf 'uv: '
  uv --version
else
  printf '%s\n' 'uv: unavailable'
  printf '%s\n' 'project_environment: unusable'
  printf '%s\n' 'pytest: unavailable'
  exit 0
fi

project_python="$(uv run --no-sync python --version 2>&1)"
project_python_status=$?
if [[ "$project_python_status" -eq 0 ]]; then
  printf 'project_python: %s\n' "$project_python"
  printf '%s\n' 'project_environment: usable'
else
  printf '%s\n' "project_python: unavailable ($project_python)"
  printf '%s\n' 'project_environment: unusable'
fi

pytest_version="$(uv run --no-sync pytest --version 2>&1)"
pytest_status=$?
if [[ "$pytest_status" -eq 0 ]]; then
  printf 'pytest: %s\n' "$pytest_version"
else
  printf '%s\n' "pytest: unavailable ($pytest_version)"
fi