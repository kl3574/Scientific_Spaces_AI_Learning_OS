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
  src/lib/articles.ts \
  src/lib/articlePresentation.ts

node --test "$test_dir/tests/articles.test.js" "$test_dir/tests/articlePresentation.test.js"
