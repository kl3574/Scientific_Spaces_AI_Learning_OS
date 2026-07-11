#!/usr/bin/env node

import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const packageJson = process.env.SCIENTIFIC_SPACES_FRONTEND_PACKAGE_JSON;
if (!packageJson) {
  throw new Error("SCIENTIFIC_SPACES_FRONTEND_PACKAGE_JSON is required");
}

const require = createRequire(pathToFileURL(packageJson));
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

async function importResolved(packageName) {
  return import(pathToFileURL(require.resolve(packageName)).href);
}

const reactMarkdownModule = await importResolved("react-markdown");
const ReactMarkdown = reactMarkdownModule.default;
const { defaultUrlTransform } = reactMarkdownModule;
const remarkGfm = (await importResolved("remark-gfm")).default;
const remarkMath = (await importResolved("remark-math")).default;
const rehypeKatex = (await importResolved("rehype-katex")).default;

const SKIP_HTML = true;
const SAFE_INLINE_IMAGE = /^data:image\/(?:png|jpe?g|gif|webp|svg\+xml|bmp);base64,/i;
const TRUSTED_KATEX_COMMANDS = new Set(["\\htmlStyle"]);

function localKatexTrust(context) {
  return TRUSTED_KATEX_COMMANDS.has(context.command);
}

function localPdfUrlTransform(url, key) {
  if (key === "src" && SAFE_INLINE_IMAGE.test(url)) {
    return url;
  }
  return defaultUrlTransform(url);
}

function markdownToHtml(markdown) {
  return renderToStaticMarkup(
    React.createElement(ReactMarkdown, {
      skipHtml: SKIP_HTML,
      remarkPlugins: [remarkGfm, remarkMath],
      rehypePlugins: [[rehypeKatex, { strict: false, throwOnError: false, trust: localKatexTrust }]],
      urlTransform: localPdfUrlTransform,
      children: markdown,
    }),
  );
}

function writeResponse(response) {
  process.stdout.write(JSON.stringify(response) + "\n");
}

function handleLine(line) {
  const trimmed = line.trim();
  if (!trimmed) {
    return;
  }

  let request;
  try {
    request = JSON.parse(trimmed);
  } catch (error) {
    writeResponse({ request_id: null, status: "error", error: `invalid json: ${error.message}` });
    return;
  }

  if (typeof request?.markdown !== "string") {
    writeResponse({
      request_id: request?.request_id ?? null,
      status: "error",
      error: "request.markdown must be a string",
    });
    return;
  }

  try {
    const html = markdownToHtml(request.markdown);
    writeResponse({ request_id: request.request_id, status: "ok", html });
  } catch (error) {
    writeResponse({
      request_id: request.request_id,
      status: "error",
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

let buffer = "";
process.stdin.setEncoding("utf-8");
process.stdin.on("data", (chunk) => {
  buffer += chunk;
  let index = buffer.indexOf("\n");
  while (index >= 0) {
    const line = buffer.slice(0, index);
    buffer = buffer.slice(index + 1);
    handleLine(line);
    index = buffer.indexOf("\n");
  }
});
