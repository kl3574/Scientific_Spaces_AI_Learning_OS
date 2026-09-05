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
  tests/articleSessionPlanning.test.ts \
  tests/articlePresentation.test.ts \
  tests/articleWorkspace.test.ts \
  tests/dashboard.test.ts \
  tests/learningWorkflow.test.ts \
  tests/navigation.test.ts \
  tests/readerLearningMutations.test.ts \
  src/lib/articles.ts \
  src/lib/articleSessionPlanning.ts \
  src/lib/articlePresentation.ts \
  src/lib/articleWorkspace.ts \
  src/lib/dashboard.ts \
  src/lib/learningWorkflow.ts \
  src/lib/navigation.ts \
  src/lib/readerLearningMutations.ts

node --test \
  "$test_dir/tests/articles.test.js" \
  "$test_dir/tests/articleSessionPlanning.test.js" \
  "$test_dir/tests/articlePresentation.test.js" \
  "$test_dir/tests/articleWorkspace.test.js" \
  "$test_dir/tests/dashboard.test.js" \
  "$test_dir/tests/learningWorkflow.test.js" \
  "$test_dir/tests/navigation.test.js" \
  "$test_dir/tests/readerLearningMutations.test.js"
