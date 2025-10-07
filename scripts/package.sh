#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
PACKAGE_NAME="open_api_package"

mkdir -p "$DIST_DIR"
rm -f "$DIST_DIR/$PACKAGE_NAME.tar.gz" "$DIST_DIR/$PACKAGE_NAME.zip"

# Build tarball excluding local-only artifacts and build caches
TAR_EXCLUDES=(
  "--exclude=.git"
  "--exclude=.venv"
  "--exclude=dist"
  "--exclude=data"
  "--exclude=.env"
  "--exclude=*.log"
  "--exclude=*.log.*"
  "--exclude=*.pyc"
  "--exclude=__pycache__"
  "--exclude=.pytest_cache"
  "--exclude=src/frontend/node_modules"
  "--exclude=src/frontend/.next"
  "--exclude=src/backend/data"
)

tar -czf "$DIST_DIR/$PACKAGE_NAME.tar.gz" \
  "${TAR_EXCLUDES[@]}" \
  -C "$ROOT_DIR" .

# Build zip archive with the same exclusions
ZIP_EXCLUDES=(
  ".git/*"
  ".venv/*"
  "dist/*"
  "data/*"
  ".env"
  "*.log"
  "*.log.*"
  "*.pyc"
  "__pycache__/*"
  "*/__pycache__/*"
  ".pytest_cache/*"
  "*/.pytest_cache/*"
  "src/frontend/node_modules/*"
  "src/frontend/.next/*"
  "src/backend/data/*"
)

(
  cd "$ROOT_DIR"
  zip -r "$DIST_DIR/$PACKAGE_NAME.zip" . -x "${ZIP_EXCLUDES[@]}"
)

echo "Package artifacts created:"
echo "  $DIST_DIR/$PACKAGE_NAME.tar.gz"
echo "  $DIST_DIR/$PACKAGE_NAME.zip"
