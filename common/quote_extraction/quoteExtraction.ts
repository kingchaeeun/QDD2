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

export interface QuoteWithId {
  id: number;
  text: string;
  section: "headline" | "body";
}

/**
 * 헤드라인과 본문을 분리해서 받되,
 * 1) 헤드라인에서 먼저 직접인용문을 찾고 (id = 1, 2, ...)
 * 2) 본문에서 위에서부터 순서대로 이어서 id를 부여한다.
 *
 * Python 쪽 `extract_quotes_advanced`와 동일한 패턴/로직을 따르되,
 * id와 섹션 정보를 함께 리턴한다.
 */
export function extractQuotesWithIds(
  headline: string,
  body: string,
  minLength = 6,
): QuoteWithId[] {
  const result: QuoteWithId[] = [];
  const seen = new Set<string>();

  const scan = (section: "headline" | "body", text: string) => {
    if (!text) return;
    for (const base of QUOTE_PATTERNS) {
      const pattern = new RegExp(base.source, base.flags);
      let match: RegExpExecArray | null;
      while ((match = pattern.exec(text)) !== null) {
        const cleaned = normalizeQuote(match[1]);
        if (cleaned.length < minLength || seen.has(cleaned)) continue;
        seen.add(cleaned);
        result.push({
          id: result.length + 1,
          text: cleaned,
          section,
        });
      }
    }
  };

  scan("headline", headline || "");
  scan("body", body || "");

  return result;
}