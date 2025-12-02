import { createRoot } from 'react-dom/client';
import { useEffect, useState } from 'react';
import { ExtensionPanel } from '../overlay_ui/components/ExtensionPanel';
import { SourceModal } from '../overlay_ui/components/SourceModal';
import type { DetectedQuote, QuoteSource } from '../overlay_ui/data/quotesData';
import { isQuoteDistorted } from '../overlay_ui/data/quotesData';
import { createQuoteRegex, extractQuotesFromText } from '../../common/quote_extraction/quoteExtraction';

declare const chrome: {
  runtime?: {
    getURL?: (path: string) => string;
    sendMessage?: (message: unknown, callback?: (response: unknown) => void) => void;
    lastError?: { message?: string };
  };
} | undefined;

type RawQuote = {
  id: number;
  text: string;
  speaker: string;
};

type ArticleContext = {
  title: string;
  reporter?: string;
  paragraphs: string[];
  root: HTMLElement;
};

type HighlightSettings = {
  distorted: boolean;
  normal: boolean;
};

type InjectedAppProps = {
  quotes: DetectedQuote[];
  article: ArticleContext;
};

const TARGET_URL_PATTERN = /^https:\/\/n\.news\.naver\.com\/mnews\/article\/\d+\/\d+/i;
const PANEL_HOST_ID = 'qdd-panel-host';
const PANEL_ROOT_ID = 'qdd-panel-root';
const PANEL_STYLE_ID = 'qdd-extension-style';
const QUOTE_EVENT_NAME = 'qdd:quote-select';
const QUOTE_REGEX = createQuoteRegex();
const DISALLOWED_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'CODE', 'PRE']);

const quoteRegistry = new Map<number, HTMLElement>();
let currentHighlightSettings: HighlightSettings = { distorted: true, normal: false };

function safeTrim(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

void (async function bootstrap() {
  if (!TARGET_URL_PATTERN.test(window.location.href)) {
    return;
  }

  try {
    console.info('[QDD] Content script bootstrap start');

    await domReady();
    console.info('[QDD] DOM ready');

    if (document.getElementById(PANEL_HOST_ID)) {
      console.info('[QDD] Panel already injected, skipping duplicate bootstrap.');
      return;
    }

    injectHighlightStyles();

    const article = locateArticle();
    if (!article.root) {
      console.warn('[QDD] Unable to locate the article root element.');
      return;
    }

    console.info('[QDD] Article root detected', {
      title: article.title,
      paragraphs: article.paragraphs.length,
    });

    const rawQuotes = wrapDirectQuotes(getQuoteTargets(article));
    let quotesForScoring = rawQuotes;
    console.info('[QDD] Direct quotes detected', rawQuotes.length);

    if (quotesForScoring.length === 0) {
      const fallbackQuotes = extractQuotesFromText(article.paragraphs.join('\n'));
      quotesForScoring = fallbackQuotes.map((text, index) => ({
        id: index + 1,
        text,
        speaker: 'Article quote',
      }));
      console.info('[QDD] Fallback text-based quote extraction', quotesForScoring.length);
    }

    const enrichedQuotes = await requestDistortionScores(quotesForScoring, article);
    console.info('[QDD] Distortion scores resolved', enrichedQuotes.length);

    enrichedQuotes.forEach((quote, index) => {
      const isDistorted = isQuoteDistorted(quote);
      const target = quoteRegistry.get(index);
      if (target) {
        target.dataset.qddDistorted = String(isDistorted);
      }
    });

    applyHighlightState();
    mountPanel(enrichedQuotes, article);
    console.info('[QDD] Panel mounted');
  } catch (error) {
    console.error('[QDD] Bootstrap failed', error);
  }
})();

function InjectedApp({ quotes, article }: InjectedAppProps) {
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const [activeQuoteIndex, setActiveQuoteIndex] = useState(0);
  const [selectedSource, setSelectedSource] = useState<QuoteSource | null>(null);
  const [highlightSettings, setHighlightSettings] = useState<HighlightSettings>(currentHighlightSettings);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ index: number }>).detail;
      if (typeof detail?.index === 'number') {
        setActiveQuoteIndex(detail.index);
        setIsPanelOpen(true);
      }
    };

    document.addEventListener(QUOTE_EVENT_NAME, handler as EventListener);
    return () => document.removeEventListener(QUOTE_EVENT_NAME, handler as EventListener);
  }, []);

  useEffect(() => {
    focusQuoteSpan(activeQuoteIndex);
  }, [activeQuoteIndex]);

  useEffect(() => {
    currentHighlightSettings = highlightSettings;
    applyHighlightState();
  }, [highlightSettings]);

  const handleQuoteChange = (nextIndex: number) => {
    setActiveQuoteIndex(nextIndex);
  };

  return (
    <>
      <div className={`qdd-panel ${isPanelOpen ? 'qdd-panel--open' : 'qdd-panel--closed'}`}>
        <div className="h-full flex flex-col bg-white">
          <div className="px-6 py-3 border-b border-gray-200">
            <p className="text-xs text-gray-500 uppercase tracking-wide">?꾩옱 湲곗궗</p>
            <p className="text-sm font-semibold text-gray-800 leading-tight">{article.title}</p>
            {article.reporter && (
              <p className="text-xs text-gray-500 mt-1">湲곗옄: {article.reporter}</p>
            )}
          </div>

          <div className="flex-1 min-h-0">
            <ExtensionPanel
              quotes={quotes}
              onViewSource={setSelectedSource}
              initialQuoteIndex={activeQuoteIndex}
              onQuoteChange={handleQuoteChange}
              onClose={() => setIsPanelOpen(false)}
              highlightSettings={highlightSettings}
              onHighlightSettingsChange={setHighlightSettings}
            />
          </div>
        </div>
      </div>

      {!isPanelOpen && (
        <button className="qdd-reopen-btn" onClick={() => setIsPanelOpen(true)}>
          QDD
        </button>
      )}

      {selectedSource && (
        <SourceModal source={selectedSource} onClose={() => setSelectedSource(null)} />
      )}
    </>
  );
}

async function domReady(): Promise<void> {
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    return;
  }

  await new Promise<void>((resolve) => {
    document.addEventListener('DOMContentLoaded', () => resolve(), { once: true });
  });
}

function locateArticle(): ArticleContext {
  const titleSelectors = [
    '#title_area',
    '.media_end_head_headline',
    'meta[property="og:title"]',
    'h2',
    'h1',
  ];

  const reporterSelectors = [
    '.journalistcard_summary_name',
    '.media_end_head_info_datestamp_author span',
    '.media_end_head_author_name',
    '.byline',
  ];

  const rootSelectors = ['#newsct_article', '.newsct_article', '#dic_area', 'article'];

  const title =
    findFirstText(titleSelectors, (el) =>
      el instanceof HTMLMetaElement ? el.content : el.textContent,
    ) || document.title;

  const reporter = findFirstText(reporterSelectors, (text) => text)?.replace(/\s+/g, ' ');

  const root =
    (findFirstElement(rootSelectors) as HTMLElement | null) ?? document.querySelector('body');

  const paragraphElements = Array.from(root?.querySelectorAll('p') ?? []);
  const paragraphs = paragraphElements
    .map((paragraph) => safeTrim(paragraph.textContent))
    .filter((content) => content.length > 0);

  return {
    title: safeTrim(title) || document.title,
    reporter: reporter ? safeTrim(reporter) : undefined,
    paragraphs,
    root: root ?? document.body,
  };
}

function findFirstText(
  selectors: string[],
  getter: (element: Element) => string | null | undefined,
): string | null {
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      const text = getter(element);
      const cleaned = safeTrim(text);
      if (cleaned.length > 0) {
        return cleaned;
      }
    }
  }
  return null;
}

function findFirstElement(selectors: string[]): Element | null {
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      return element;
    }
  }
  return null;
}

function getQuoteTargets(article: ArticleContext): HTMLElement[] {
  const targets: HTMLElement[] = [];
  const seen = new Set<HTMLElement>();

  const pushIfValid = (element: HTMLElement | null) => {
    if (element && !seen.has(element)) {
      seen.add(element);
      targets.push(element);
    }
  };

  pushIfValid(article.root);

  const headlineSelectors = ['#title_area', '.media_end_head_headline', '.media_end_head_title', '.media_end_head'];
  headlineSelectors.forEach((selector) => {
    const el = document.querySelector(selector);
    pushIfValid(el as HTMLElement | null);
  });

  return targets;
}

function wrapDirectQuotes(targets: HTMLElement[]): RawQuote[] {
  const rawQuotes: RawQuote[] = [];
  const nodes: Text[] = [];
  const seenNodes = new Set<Text>();

  targets.forEach((root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const currentNode = walker.currentNode as Text;
      if (shouldSkipNode(currentNode) || seenNodes.has(currentNode)) {
        continue;
      }
      seenNodes.add(currentNode);
      nodes.push(currentNode);
    }
  });

  nodes.forEach((node) => {
    const text = typeof node.nodeValue === 'string' ? node.nodeValue : '';
    if (!text.trim()) {
      return;
    }

    const matches = [...text.matchAll(QUOTE_REGEX)];
    if (!matches.length) {
      return;
    }

    const fragment = document.createDocumentFragment();
    let lastIndex = 0;

    matches.forEach((match) => {
      const [raw] = match;
      const index = match.index ?? 0;

      if (index > lastIndex) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex, index)));
      }

      const quoteIndex = rawQuotes.length;
      const span = document.createElement('span');
      span.textContent = raw;
      span.className = 'qdd-quote';
      span.dataset.quoteIndex = String(quoteIndex);
      span.addEventListener('click', () => {
        const event = new CustomEvent(QUOTE_EVENT_NAME, { detail: { index: quoteIndex } });
        document.dispatchEvent(event);
      });

      fragment.appendChild(span);
      registerQuoteSpan(quoteIndex, span);

      const cleanedQuote = safeTrim((match[1] as string | undefined) ?? raw.replace(/^[\'"\u201c\u2018]|[\'"\u201d\u2019]$/g, ""));

      rawQuotes.push({
        id: quoteIndex + 1,
        text: cleanedQuote,
        speaker: 'Article quote',
      });

      lastIndex = index + raw.length;
    });

    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
    }

    node.parentNode?.replaceChild(fragment, node);
  });

  return rawQuotes;
}

function shouldSkipNode(node: Text): boolean {
  const parent = node.parentElement;
  if (!parent) {
    return true;
  }

  if (DISALLOWED_TAGS.has(parent.tagName)) {
    return true;
  }

  if (parent.closest(`#${PANEL_HOST_ID}`)) {
    return true;
  }

  if (!node.nodeValue) {
    return true;
  }

  QUOTE_REGEX.lastIndex = 0;
  return !QUOTE_REGEX.test(node.nodeValue);
}

async function requestDistortionScores(
  quotes: RawQuote[],
  article: ArticleContext,
): Promise<DetectedQuote[]> {
  const serializableArticle = {
    title: article.title,
    reporter: article.reporter,
    paragraphs: article.paragraphs,
    url: window.location.href,
    text: article.paragraphs.join('\n'),
  };

  const message = {
    type: 'qdd:analyze-quotes',
    quotes,
    article: serializableArticle,
  };

  if (typeof chrome !== 'undefined' && chrome?.runtime?.sendMessage) {
    const response = await new Promise<{ ok: boolean; data?: unknown; error?: string }>((resolve) => {
      try {
        chrome.runtime?.sendMessage?.(message, (res) => {
          if (chrome.runtime?.lastError) {
            resolve({ ok: false, error: chrome.runtime.lastError.message });
            return;
          }
          resolve((res as { ok: boolean; data?: unknown; error?: string }) ?? { ok: false, error: 'No response' });
        });
      } catch (error) {
        resolve({ ok: false, error: String(error) });
      }
    });

    if (response?.ok && response.data && Array.isArray((response.data as { quotes?: unknown }).quotes)) {
      return (response.data as { quotes: DetectedQuote[] }).quotes;
    }

    console.warn('[QDD] Backend call failed, using local mock scores', response?.error);
  }

  return buildLocalMock(quotes);
}

function buildLocalMock(quotes: RawQuote[]): DetectedQuote[] {
  return quotes.map((quote, index) => {
    const sources = Array.from({ length: 5 }, (_, sourceIndex) => {
      const mockScore = 45 + (((index + sourceIndex) * 13) % 50);
      return {
        id: index * 5 + sourceIndex + 1,
        title: `Source candidate ${sourceIndex + 1}`,
        sourceLink: `https://example.com/source-${index + 1}-${sourceIndex + 1}`,
        originalText: quote.text,
        distortionScore: mockScore,
        similarityScore: 60 + (((index + sourceIndex) * 7) % 35),
        scores: {
          semanticReduction: 40 + (((index + sourceIndex) * 5) % 50),
          interpretiveExtension: 35 + (((index + sourceIndex) * 9) % 55),
          lexicalColoring: mockScore,
        },
      };
    });

    return {
      ...quote,
      sources,
    };
  });
}

function mountPanel(quotes: DetectedQuote[], article: ArticleContext) {
  const host = document.createElement('div');
  host.id = PANEL_HOST_ID;
  host.style.position = 'fixed';
  host.style.top = '0';
  host.style.right = '0';
  host.style.width = '420px';
  host.style.height = '100vh';
  host.style.zIndex = '2147483647';
  host.style.pointerEvents = 'auto';

  document.body.appendChild(host);
  const shadowRoot = host.attachShadow({ mode: 'open' });

  const cssLink = document.createElement('link');
  cssLink.rel = 'stylesheet';
  cssLink.href = getExtensionAssetUrl('dist/assets/popup.css');
  shadowRoot.appendChild(cssLink);

  const localStyles = document.createElement('style');
  localStyles.textContent = `
    :host {
      all: initial;
    }
    .qdd-shell {
      width: 420px;
      height: 100vh;
      position: relative;
      font-family: 'Pretendard Variable', 'Noto Sans KR', sans-serif;
    }
    .qdd-panel {
      width: 100%;
      height: 100%;
      box-shadow: -6px 0 18px rgba(0, 0, 0, 0.2);
      background: #fff;
      transition: transform 0.25s ease;
    }
    .qdd-panel--closed {
      transform: translateX(100%);
    }
    .qdd-panel--open {
      transform: translateX(0);
    }
    .qdd-reopen-btn {
      position: absolute;
      top: 50%;
      right: 440px;
      transform: translateY(-50%);
      background: #3D5AFE;
      color: #fff;
      border: none;
      border-radius: 999px;
      padding: 10px 18px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 8px 16px rgba(61, 90, 254, 0.35);
    }
  `;
  shadowRoot.appendChild(localStyles);

  const rootElement = document.createElement('div');
  rootElement.id = PANEL_ROOT_ID;
  rootElement.className = 'qdd-shell';
  shadowRoot.appendChild(rootElement);

  const root = createRoot(rootElement);
  root.render(<InjectedApp quotes={quotes} article={article} />);
}

function injectHighlightStyles() {
  if (document.getElementById(PANEL_STYLE_ID)) {
    return;
  }

  const style = document.createElement('style');
  style.id = PANEL_STYLE_ID;
  style.textContent = `
    .qdd-quote {
      background: rgba(255, 233, 147, 0.85);
      border-radius: 4px;
      padding: 0 2px;
      cursor: pointer;
      transition: background 0.2s ease, box-shadow 0.2s ease;
    }
    .qdd-quote:hover {
      background: rgba(255, 210, 92, 0.95);
    }
    .qdd-quote--muted {
      background: transparent !important;
      box-shadow: none !important;
    }
    .qdd-quote--active {
      box-shadow: 0 0 0 2px #3D5AFE;
    }
  `;

  document.head.appendChild(style);
}

function registerQuoteSpan(index: number, element: HTMLElement) {
  quoteRegistry.set(index, element);
}

function focusQuoteSpan(index: number) {
  const element = quoteRegistry.get(index);
  if (!element) {
    return;
  }

  element.classList.add('qdd-quote--active');
  element.scrollIntoView({ behavior: 'smooth', block: 'center' });

  window.setTimeout(() => {
    element.classList.remove('qdd-quote--active');
  }, 1800);
}

function applyHighlightState() {
  quoteRegistry.forEach((element) => {
    const isDistorted = element.dataset.qddDistorted === 'true';
    const shouldHighlight = isDistorted ? currentHighlightSettings.distorted : currentHighlightSettings.normal;
    element.classList.toggle('qdd-quote--muted', !shouldHighlight);
  });
}

function getExtensionAssetUrl(relativePath: string): string {
  if (typeof chrome !== 'undefined' && chrome?.runtime?.getURL) {
    return chrome.runtime.getURL(relativePath);
  }

  return relativePath;
}


