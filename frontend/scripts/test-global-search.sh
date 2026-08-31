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
  tests/globalSearch.test.ts \
  src/lib/globalSearch.ts \
  src/lib/articlePresentation.ts \
  src/lib/articles.ts \
  src/lib/references.ts \
  src/lib/graph.ts \
  src/lib/graphPresentation.ts \
  src/lib/learningWorkflow.ts \
  src/lib/navigation.ts

node --test "$test_dir/tests/globalSearch.test.js"
