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
  tests/savedLibrary.test.ts \
  src/lib/savedLibrary.ts \
  src/lib/articleWorkspace.ts \
  src/lib/learning.ts \
  src/lib/learningWorkflow.ts \
  src/lib/readingHistory.ts

node --test "$test_dir/tests/savedLibrary.test.js"
