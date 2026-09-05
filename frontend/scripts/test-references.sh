#!/bin/sh
set -eu

test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT

./node_modules/.bin/tsc \
  --module commonjs \
  --target es2022 \
  --moduleResolution node \
  --esModuleInterop \
  --skipLibCheck \
  --outDir "$test_dir" \
  tests/referenceReview.test.ts \
  tests/references.test.ts \
  tests/zoteroLinkOperations.test.ts \
  src/lib/referenceReview.ts \
  src/lib/references.ts \
  src/lib/zotero.ts \
  src/lib/zoteroLinkOperations.ts

node --test \
  "$test_dir/tests/referenceReview.test.js" \
  "$test_dir/tests/references.test.js" \
  "$test_dir/tests/zoteroLinkOperations.test.js"
