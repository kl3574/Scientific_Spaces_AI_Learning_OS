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
  tests/tutor.test.ts \
  src/lib/tutor.ts \
  src/lib/tutorPresentation.ts

node --test "$test_dir/tests/tutor.test.js"
