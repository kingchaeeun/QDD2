/**
 * Shared quote-extraction helpers for both the extension and any JS runtime.
 * Mirrors the Python helpers in common/quote_extraction/quote_extraction.py.
 */

export const COMMON_QUOTE_REGEX = /["'\u201c\u2018][^"'\u201d\u2019]+["'\u201d\u2019]/g;

const QUOTE_PATTERNS = [
  /“([^”]+)”/g, // Korean/English curly quotes
  /"([^"]+)"/g, // straight double quotes
  /'([^']+)'/g, // straight single quotes
  /‘([^’]+)’/g, // curly single quotes
];

export function normalizeQuote(text: string | undefined | null): string {
  return (text ?? "").replace(/\s+/g, " ").trim();
}

export function createQuoteRegex(): RegExp {
  return new RegExp(COMMON_QUOTE_REGEX.source, COMMON_QUOTE_REGEX.flags);
}

export function extractQuotesFromText(text: string, minLength = 6): string[] {
  if (!text) return [];

  const unique = new Set<string>();
  const quotes: string[] = [];

  for (const base of QUOTE_PATTERNS) {
    const pattern = new RegExp(base.source, base.flags);
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(text)) !== null) {
      const cleaned = normalizeQuote(match[1]);
      if (cleaned.length < minLength || unique.has(cleaned)) continue;
      unique.add(cleaned);
      quotes.push(cleaned);
    }
  }

  return quotes;
}
