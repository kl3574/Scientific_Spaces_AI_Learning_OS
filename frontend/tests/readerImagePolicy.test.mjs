import { strict as assert } from "node:assert";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ReactMarkdown from "react-markdown";

import {
  isAllowedReaderInlineImageUrl,
  readerMarkdownUrlTransform,
} from "../src/lib/readerImagePolicy.js";

const PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAACXBIWXMAAAPoAAAD6AG1e1JrAAAAEUlEQVQImWPgmXDnPwgzwBgAUoQJ3bE27EYAAAAASUVORK5CYII=";
const ORIGIN = "https://reader.example";
const OBJECT_ID = "11111111-1111-4111-8111-111111111111";
const BLOB = `blob:${ORIGIN}/${OBJECT_ID}`;

function withBrowserWindow(value, callback) {
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  if (value === undefined) {
    delete globalThis.window;
  } else {
    Object.defineProperty(globalThis, "window", { configurable: true, value });
  }
  try {
    return callback();
  } finally {
    if (previous) {
      Object.defineProperty(globalThis, "window", previous);
    } else {
      delete globalThis.window;
    }
  }
}

function withBrowserOrigin(origin, callback) {
  return withBrowserWindow({ location: { origin } }, callback);
}

function markdownUrls(markdown) {
  const images = [];
  const links = [];
  renderToStaticMarkup(createElement(ReactMarkdown, {
    urlTransform: readerMarkdownUrlTransform,
    components: {
      img: ({ src, alt }) => {
        images.push({ src, alt });
        return null;
      },
      a: ({ href, children }) => {
        links.push(href);
        return createElement("span", null, children);
      },
    },
  }, markdown));
  return { images, links };
}

test("Reader Markdown preserves the complete qualified 150-character PNG source", () => {
  const { images } = markdownUrls(`![Local raster](${PNG})`);
  assert.equal(PNG.length, 150);
  assert.equal(images.length, 1);
  assert.equal(images[0].src.length, 150);
  assert.equal(images[0].src, PNG);
  assert.equal(images[0].alt, "Local raster");
});

test("raster MIME admission accepts canonical encoding without claiming byte decoding", () => {
  for (const mime of ["png", "jpeg", "gif", "webp", "avif"]) {
    for (const payload of ["Zg==", "Zm8=", "Zm9v", "+/8=", "////"]) {
      const url = `data:image/${mime};base64,${payload}`;
      assert.equal(isAllowedReaderInlineImageUrl(url), true, url);
    }
  }
  const upper = PNG.replace("data:image/png;base64,", "DATA:IMAGE/PNG;BASE64,");
  assert.equal(isAllowedReaderInlineImageUrl(upper), true);
  assert.equal(markdownUrls(`![Raster](${upper})`).images[0].src, upper);
});

test("canonical base64 rejects incomplete quartets, padding errors and nonstandard alphabets", () => {
  for (const payload of ["", "A", "AA", "AAA", "AAAAA", "A===", "====", "AA=A",
    "AA===", "AAA==", "AAAA=", "AA==AAAA", "_w==", "-w==", "AA%3D%3D", "AA?="]) {
    assert.equal(isAllowedReaderInlineImageUrl(`data:image/png;base64,${payload}`), false, payload);
  }
});

test("canonical base64 requires zero unused bits for both padding lengths", () => {
  for (const payload of ["AA==", "AQ==", "Ag==", "Aw==", "AAA=", "AAE=", "AA8="]) {
    assert.equal(isAllowedReaderInlineImageUrl(`data:image/png;base64,${payload}`), true, payload);
  }
  for (const payload of ["AB==", "AP==", "AR==", "AZ==", "Zh==", "A/==", "AAB=", "AAC=", "AAD=", "Zm9="]) {
    assert.equal(isAllowedReaderInlineImageUrl(`data:image/png;base64,${payload}`), false, payload);
  }
});

test("inline admission rejects controls, whitespace and non-string values without coercion", () => {
  for (const character of [" ", "\t", "\r", "\n", "\u0000", "\u001f", "\u007f", "\u0085", "\u00a0"]) {
    for (const url of [character + PNG, PNG + character, PNG.replace("base64,", `base64,${character}`)]) {
      assert.equal(isAllowedReaderInlineImageUrl(url), false);
    }
  }
  for (const value of [undefined, null, 0, false, {}, { toString() { throw new Error("must not coerce"); } }]) {
    assert.equal(isAllowedReaderInlineImageUrl(value), false);
  }
});

test("actual Markdown image pipeline removes malformed and non-raster inline sources", () => {
  for (const url of [
    "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=", "data:text/html;base64,PGgxPng8L2gxPg==",
    "data:application/octet-stream;base64,AA==", "data:image/jpg;base64,AA==",
    "data:image/bmp;base64,AA==", "data:image/png;charset=utf-8;base64,AA==",
    "data:image/png;base64;charset=utf-8,AA==", "data:image/png;BASE64;name=x,AA==",
    "data:image/png,plain", "data:image/png;base64,", "data:image/png;base64,AA",
    "data:image/png;base64,AB==", "data:image/png;base64,AAB=", "data:image/png;base64,AA==#fragment",
  ]) {
    assert.equal(isAllowedReaderInlineImageUrl(url), false, url);
    assert.deepEqual(markdownUrls(`![Rejected](<${url}>)`).images, [{ src: "", alt: "Rejected" }], url);
  }
});

test("inline exception applies only to the exact img.src attribute", () => {
  withBrowserOrigin(ORIGIN, () => {
    for (const url of [PNG, BLOB]) {
      assert.equal(readerMarkdownUrlTransform(url, "src", { tagName: "img" }), url);
      for (const [tagName, key] of [["a", "href"], ["img", "href"], ["img", "srcSet"],
        ["video", "src"], ["iframe", "src"], ["IMG", "src"]]) {
        assert.equal(readerMarkdownUrlTransform(url, key, { tagName }), "", `${tagName}.${key}`);
      }
    }
  });
});

test("actual Markdown links still reject inline and executable schemes", () => {
  withBrowserOrigin(ORIGIN, () => {
    for (const url of [PNG, BLOB, "data:text/html;base64,PGgxPng8L2gxPg==", "javascript:alert(1)", "vbscript:msgbox(1)"]) {
      assert.deepEqual(markdownUrls(`[Blocked](<${url}>)`).links, [""], url);
    }
  });
});

test("ordinary links retain upstream URL behavior through the actual Markdown pipeline", () => {
  for (const url of ["https://example.test/article?q=one#section", "http://example.test/a",
    "mailto:reader@example.test", "irc://example.test/channel", "xmpp:reader@example.test",
    "/articles/example", "../article", "#section", "//example.test/article"]) {
    assert.deepEqual(markdownUrls(`[Source](<${url}>)`).links, [url], url);
  }
});

test("remote and relative image URLs remain available to the existing placeholder renderer", () => {
  for (const url of ["https://example.test/plot.png", "http://example.test/plot.png",
    "//example.test/plot.png", "/assets/plot.png", "./plot.png", "../plot.png"]) {
    assert.equal(isAllowedReaderInlineImageUrl(url), false, url);
    assert.deepEqual(markdownUrls(`![Remote](<${url}>)`).images, [{ src: url, alt: "Remote" }], url);
  }
});

test("same-origin blob sources survive the actual Markdown pipeline without a lifetime claim", () => {
  withBrowserOrigin(ORIGIN, () => {
    assert.equal(isAllowedReaderInlineImageUrl(BLOB), true);
    assert.deepEqual(markdownUrls(`![Object](<${BLOB}>)`).images, [{ src: BLOB, alt: "Object" }]);
  });
});

test("blob origins use URL parsing including normalized hosts and default ports", () => {
  for (const [origin, url] of [
    ["https://READER.example:443", BLOB],
    [ORIGIN, `blob:https://READER.example:443/${OBJECT_ID}`],
    ["http://127.0.0.1:3000", `blob:http://127.0.0.1:3000/${OBJECT_ID}`],
    ["http://[::1]:3000", `blob:http://[::1]:3000/${OBJECT_ID}`],
  ]) {
    withBrowserOrigin(origin, () => assert.equal(isAllowedReaderInlineImageUrl(url), true, url));
  }
});

test("blob admission rejects foreign, opaque, malformed and credential-bearing object URLs", () => {
  withBrowserOrigin(ORIGIN, () => {
    for (const url of [
      `blob:https://foreign.example/${OBJECT_ID}`, `blob:http://reader.example/${OBJECT_ID}`,
      `blob:https://reader.example:444/${OBJECT_ID}`, `blob:https://reader.example.evil.test/${OBJECT_ID}`,
      `blob:https://reader.example@foreign.example/${OBJECT_ID}`, `blob:https://user:pass@reader.example/${OBJECT_ID}`,
      `blob:null/${OBJECT_ID}`, `blob:data:text/plain,${OBJECT_ID}`, `blob:file:///${OBJECT_ID}`,
      "blob:", "blob:https://reader.example", "blob:https://reader.example/", "blob:relative/object",
      `blob:https://reader.example/path/${OBJECT_ID}`, `blob:https://reader.example/../${OBJECT_ID}`,
      "blob:https://reader.example/not-an-object-id", `blob:https://reader.example/%31${OBJECT_ID.slice(1)}`,
      BLOB + "?", BLOB + "#", BLOB + "?x=1", BLOB + "#fragment", BLOB + "/",
    ]) {
      assert.equal(isAllowedReaderInlineImageUrl(url), false, url);
      assert.deepEqual(markdownUrls(`![Rejected](<${url}>)`).images, [{ src: "", alt: "Rejected" }], url);
    }
    for (const character of ["\t", "\n", "\u0000", "\u007f"]) {
      assert.equal(isAllowedReaderInlineImageUrl(BLOB + character), false);
    }
  });
});

test("blob admission fails closed without a trusted non-opaque browser origin", () => {
  const windows = [undefined, {}, { location: {} }, ...[
    undefined, null, "", "null", "file:///tmp/reader", "data:text/html,x", "/relative",
    "https://reader.example/path", "https://user@reader.example", ORIGIN + "?x=1", ORIGIN + "#fragment",
    ORIGIN + "\n", ORIGIN + "\r", ORIGIN + "\t", ORIGIN + "\u0000", ORIGIN + "\u0085",
  ].map((origin) => ({ location: { origin } }))];
  for (const value of windows) {
    withBrowserWindow(value, () => {
      assert.equal(isAllowedReaderInlineImageUrl(BLOB), false);
      assert.deepEqual(markdownUrls(`![Object](${BLOB})`).images, [{ src: "", alt: "Object" }]);
      assert.equal(isAllowedReaderInlineImageUrl(PNG), true);
    });
  }
});

test("validator and transform share the current trusted origin instead of caching an earlier one", () => {
  for (const origin of [ORIGIN, "https://foreign.example", ORIGIN]) {
    withBrowserOrigin(origin, () => {
      const allowed = origin === ORIGIN;
      assert.equal(isAllowedReaderInlineImageUrl(BLOB), allowed);
      assert.equal(readerMarkdownUrlTransform(BLOB, "src", { tagName: "img" }), allowed ? BLOB : "");
    });
  }
});
