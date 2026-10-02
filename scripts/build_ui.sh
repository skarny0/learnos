#!/usr/bin/env bash
# Build the desktop and copy it into the env package, so the env server (and Colab) can serve it
# without Node. Re-run after any change under ui/ and commit env/learnos_env/ui_dist.
set -euo pipefail
cd "$(dirname "$0")/../ui"
npm install --no-audit --no-fund
npm run build
rm -rf ../env/learnos_env/ui_dist
cp -r dist ../env/learnos_env/ui_dist
echo "desktop copied to env/learnos_env/ui_dist"
