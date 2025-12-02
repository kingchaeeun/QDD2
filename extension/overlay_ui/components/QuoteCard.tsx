interface QuoteCardProps {
  quote: {
    id: number;
    text: string;
    speaker: string;
  };
}

export function QuoteCard({ quote }: QuoteCardProps) {
  return (
    <div className="bg-[#F1F3F4] rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer">
      <p className="mb-2">
        "{quote.text}"
      </p>
      <p className="text-gray-600">
        Speaker: {quote.speaker}
      </p>
    </div>
  );
}