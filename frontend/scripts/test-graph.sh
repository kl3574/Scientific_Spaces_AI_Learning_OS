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
  tests/graph.test.ts \
  src/lib/graph.ts \
  src/lib/graphPresentation.ts

node --test "$test_dir/tests/graph.test.js"
