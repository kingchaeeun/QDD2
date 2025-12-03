declare const chrome: {
  runtime: {
    onMessage: {
      addListener: (
        listener: (message: unknown, sender: unknown, sendResponse: (response: unknown) => void) => void,
      ) => void;
    };
  };
};

const API_BASE = 'http://127.0.0.1:8000';

type AnalyzeRequest = {
  type: 'qdd:analyze-quotes';
  article: unknown;
  quotes: unknown;
};

chrome.runtime.onMessage.addListener((message: AnalyzeRequest, _sender, sendResponse) => {
  if (!message?.type || message.type !== 'qdd:analyze-quotes') {
    return;
  }

  runAnalysis(message)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((error) => sendResponse({ ok: false, error: String(error) }));

  return true; // keep the message channel open for async response
});

async function runAnalysis(payload: AnalyzeRequest) {
  const response = await fetch(`${API_BASE}/api/v1/analyze-quotes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      article: payload.article,
      quotes: payload.quotes,
    }),
  });

  if (!response.ok) {
    throw new Error(`Backend responded with ${response.status}`);
  }

  return response.json();
}
