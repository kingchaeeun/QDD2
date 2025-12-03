import { Quote, Settings, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { QuoteCard } from './QuoteCard';
import { SourceCarousel } from './SourceCarousel';
import { useState, useEffect, useRef } from 'react';
import type { DetectedQuote } from '../data/quotesData';

interface ExtensionPanelProps {
  quotes: DetectedQuote[];
  onViewSource: (source: any) => void;
  initialQuoteIndex?: number;
  onClose: () => void;
  highlightSettings: {
    distorted: boolean;
    normal: boolean;
  };
  onHighlightSettingsChange: (settings: { distorted: boolean; normal: boolean }) => void;
  onQuoteChange?: (index: number) => void;
}

export function ExtensionPanel({ 
  quotes,
  onViewSource, 
  initialQuoteIndex = 0, 
  onClose,
  highlightSettings,
  onHighlightSettingsChange,
  onQuoteChange,
}: ExtensionPanelProps) {
  const [currentQuoteIndex, setCurrentQuoteIndex] = useState(initialQuoteIndex);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);
  const availableQuotes = quotes ?? [];
  const hasQuotes = availableQuotes.length > 0;

  const clampIndex = (index: number) => {
    if (!hasQuotes) {
      return 0;
    }
    return Math.min(Math.max(index, 0), availableQuotes.length - 1);
  };

  useEffect(() => {
    setCurrentQuoteIndex(clampIndex(initialQuoteIndex));
  }, [initialQuoteIndex, availableQuotes.length]);

  useEffect(() => {
    if (typeof onQuoteChange === 'function') {
      onQuoteChange(currentQuoteIndex);
    }
  }, [currentQuoteIndex, onQuoteChange]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
        setIsSettingsOpen(false);
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handlePrevQuote = () => {
    setCurrentQuoteIndex((prevIndex) => clampIndex(prevIndex > 0 ? prevIndex - 1 : availableQuotes.length - 1));
  };

  const handleNextQuote = () => {
    setCurrentQuoteIndex((prevIndex) => clampIndex(prevIndex < availableQuotes.length - 1 ? prevIndex + 1 : 0));
  };

  const activeQuote = hasQuotes ? availableQuotes[currentQuoteIndex] : null;
  const activeSources = activeQuote?.sources ?? [];

  return (
    <div className="h-full flex flex-col">
      {/* Title Bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Quote className="w-5 h-5 text-[#3D5AFE]" />
          <span>Quote Distortion Detection</span>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors" onClick={() => setIsSettingsOpen(!isSettingsOpen)}>
            <Settings className="w-5 h-5 text-gray-600" />
          </button>
          <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors" onClick={onClose}>
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6 relative">
        {/* Navigation Arrows */}
        <button 
          className="absolute left-2 top-1/2 -translate-y-1/2 z-10 p-2 hover:bg-white/90 bg-white/70 rounded-full shadow-md transition-all disabled:opacity-30 disabled:cursor-not-allowed" 
          onClick={handlePrevQuote}
          disabled={!hasQuotes || currentQuoteIndex === 0}
        >
          <ChevronLeft className="w-5 h-5 text-gray-700" />
        </button>
        
        <button 
          className="absolute right-2 top-1/2 -translate-y-1/2 z-10 p-2 hover:bg-white/90 bg-white/70 rounded-full shadow-md transition-all disabled:opacity-30 disabled:cursor-not-allowed" 
          onClick={handleNextQuote}
          disabled={!hasQuotes || currentQuoteIndex === availableQuotes.length - 1}
        >
          <ChevronRight className="w-5 h-5 text-gray-700" />
        </button>

        {/* Current Detected Quote with Sources */}
        <div>
          {!hasQuotes && (
            <div className="text-center text-gray-500">
              <p>이 기사에서 직접 인용문을 찾지 못했어요.</p>
              <p className="text-sm mt-2">다른 기사에서 다시 시도해 주세요.</p>
            </div>
          )}

          {hasQuotes && activeQuote && (
            <section>
              <h2 className="mb-4 text-gray-700 flex items-center gap-2">
                Detected Quote
                <sup className="text-[10px] text-black ml-0.5">{currentQuoteIndex + 1}</sup>
              </h2>
              <QuoteCard quote={activeQuote} />
              
              <div className="mt-4">
                <h3 className="mb-3 text-gray-700">
                  Recommended Sources ({activeSources.length})
                </h3>
                {activeSources.length > 0 ? (
                  <SourceCarousel sources={activeSources} onViewSource={onViewSource} />
                ) : (
                  <div className="text-sm text-gray-500">
                    충분한 비교 소스를 아직 불러오지 못했어요.
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      </div>

      {/* Page Indicator */}
      <div className="flex items-center justify-center px-6 py-4 border-t border-gray-200">
        <div className="flex items-center gap-2">
          {availableQuotes.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentQuoteIndex(index)}
              className={`w-2 h-2 rounded-full transition-colors ${
                index === currentQuoteIndex ? 'bg-[#3D5AFE]' : 'bg-gray-300'
              }`}
              aria-label={`Go to quote ${index + 1}`}
            />
          ))}
        </div>
      </div>

      {/* Settings Dropdown */}
      {isSettingsOpen && (
        <div ref={settingsRef} className="absolute top-14 right-6 bg-white border border-gray-200 shadow-md rounded-lg z-20">
          <div className="p-4">
            <h3 className="text-sm font-bold mb-2">Highlight Settings</h3>
            <div className="flex items-center mb-2">
              <input
                type="checkbox"
                checked={highlightSettings.distorted}
                onChange={(e) => onHighlightSettingsChange({ ...highlightSettings, distorted: e.target.checked })}
                className="mr-2"
              />
              <label className="text-sm">Distorted</label>
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={highlightSettings.normal}
                onChange={(e) => onHighlightSettingsChange({ ...highlightSettings, normal: e.target.checked })}
                className="mr-2"
              />
              <label className="text-sm">Normal</label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}