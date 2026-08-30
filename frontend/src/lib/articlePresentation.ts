const markdownLinkPattern = /!?\[([^\]]*)\]\([^)]*\)/g;

export function toPlainTextPreview(markdown: string, maxLength = 420): string {
  const plainText = markdown
    .replace(/```[\s\S]*?```|~~~[\s\S]*?~~~/g, " ")
    .replace(markdownLinkPattern, "$1")
    .replace(/\[([^\]]+)\]\([^)]*(?:\)|$)/g, "$1")
    .replace(/<[^>]+>/g, " ")
    .replace(/^\s{0,3}(?:#{1,6}|>|[-+*]|\d+\.)\s+/gm, "")
    .replace(/(^|\s)#{1,6}(?=\s|$)\s*/g, "$1")
    .replace(/(\*\*|__|~~|`)/g, "")
    .replace(/\$\$?/g, "")
    .replace(/\\(?:begin|end)\{[^}]+\}/g, " ")
    .replace(/\\([A-Za-z]+)(?:\{([^{}]*)\})?/g, (_match, command: string, value?: string) => value ?? command)
    .replace(/\\([_*[\]()#+.!-])/g, "$1")
    .replace(/[\t\r\n ]+/g, " ")
    .trim();

  if (plainText.length <= maxLength) {
    return plainText;
  }
  return `${plainText.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}
