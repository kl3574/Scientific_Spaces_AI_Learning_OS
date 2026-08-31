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
  tests/articles.test.ts \
  tests/articlePresentation.test.ts \
  tests/articleWorkspace.test.ts \
  tests/dashboard.test.ts \
  tests/learningWorkflow.test.ts \
  src/lib/articles.ts \
  src/lib/articlePresentation.ts \
  src/lib/articleWorkspace.ts \
  src/lib/dashboard.ts \
  src/lib/learningWorkflow.ts

node --test \
  "$test_dir/tests/articles.test.js" \
  "$test_dir/tests/articlePresentation.test.js" \
  "$test_dir/tests/articleWorkspace.test.js" \
  "$test_dir/tests/dashboard.test.js" \
  "$test_dir/tests/learningWorkflow.test.js"
