import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { SourceCard } from './SourceCard';

interface SourceCarouselProps {
  sources: any[];
  onViewSource: (source: any) => void;
}

export function SourceCarousel({ sources, onViewSource }: SourceCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : sources.length - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < sources.length - 1 ? prev + 1 : 0));
  };

  return (
    <div className="space-y-4">
      {/* Current Card */}
      <SourceCard
        source={sources[currentIndex]}
        onViewSource={onViewSource}
      />

      {/* Carousel Navigation - Moved to Bottom */}
      <div className="flex items-center justify-between">
        <button
          onClick={handlePrev}
          className="p-2 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
          aria-label="Previous source"
        >
          <ChevronLeft className="w-5 h-5 text-gray-700" />
        </button>

        <div className="flex gap-2">
          {sources.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentIndex(index)}
              className={`w-2 h-2 rounded-full transition-all ${
                index === currentIndex
                  ? 'bg-[#3D5AFE] w-6'
                  : 'bg-gray-300'
              }`}
              aria-label={`Go to source ${index + 1}`}
            />
          ))}
        </div>

        <button
          onClick={handleNext}
          className="p-2 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
          aria-label="Next source"
        >
          <ChevronRight className="w-5 h-5 text-gray-700" />
        </button>
      </div>
    </div>
  );
}