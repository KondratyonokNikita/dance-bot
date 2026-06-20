#!/usr/bin/env bash
set -euo pipefail

# Обновляет ветку index до текущего master для GitHub Pages.
# Запускайте вручную, когда нужно опубликовать изменения на сайте.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if ! git rev-parse --verify master >/dev/null 2>&1; then
	echo "Local branch master not found." >&2
	exit 1
fi

git push origin master:index
echo "origin/index updated to master@$(git rev-parse --short master)"
