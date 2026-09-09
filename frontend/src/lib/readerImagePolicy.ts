import { defaultUrlTransform, type UrlTransform } from "react-markdown";

const RASTER_DATA_PREFIX = /^data:image\/(?:png|jpeg|gif|webp|avif);base64,/i;
const BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
const BLOB_URL = /^blob:(https?:\/\/[^/?#\\]+)\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function parsedHttpOrigin(value: unknown): string | null {
  if (typeof value !== "string" || !/^https?:\/\/[^/?#\\\s\u0000-\u001f\u007f-\u009f]+\/?$/i.test(value)) {
    return null;
  }
  try {
    const parsed = new URL(value);
    return parsed.username || parsed.password || parsed.origin === "null" ? null : parsed.origin;
  } catch {
    return null;
  }
}

function isSameOriginBlobUrl(value: string): boolean {
  const match = BLOB_URL.exec(value);
  if (!match || typeof window === "undefined") {
    return false;
  }
  try {
    const origin = parsedHttpOrigin(window.location.origin);
    return origin !== null
      && parsedHttpOrigin(match[1]) === origin
      && new URL(value).origin === origin;
  } catch {
    return false;
  }
}

function isCanonicalBase64(payload: string): boolean {
  if (!payload || payload.length % 4 !== 0 || !/^[A-Za-z0-9+/]+={0,2}$/.test(payload)) {
    return false;
  }
  // Two padding characters leave four unused bits; one leaves two.
  if (payload.endsWith("==")) {
    return (BASE64_ALPHABET.indexOf(payload[payload.length - 3]) & 15) === 0;
  }
  if (payload.endsWith("=")) {
    return (BASE64_ALPHABET.indexOf(payload[payload.length - 2]) & 3) === 0;
  }
  return true;
}

/** URL admission only: neither decoded image bytes nor blob lifetime is proved. */
export function isAllowedReaderInlineImageUrl(value: string): boolean {
  if (typeof value !== "string" || /[\s\u0000-\u001f\u007f-\u009f]/u.test(value)) {
    return false;
  }
  const prefix = RASTER_DATA_PREFIX.exec(value);
  return prefix !== null
    ? isCanonicalBase64(value.slice(prefix[0].length))
    : isSameOriginBlobUrl(value);
}

export const readerMarkdownUrlTransform: UrlTransform = (url, key, node) => {
  if (node.tagName === "img" && key === "src" && isAllowedReaderInlineImageUrl(url)) {
    return url;
  }
  return defaultUrlTransform(url);
};
