import { X, ExternalLink } from 'lucide-react';
import { motion } from 'motion/react';

interface SourceModalProps {
  source: any;
  onClose: () => void;
}

export function SourceModal({ source, onClose }: SourceModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white rounded-2xl shadow-2xl w-[360px] h-[500px] flex flex-col"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-gray-800">Original Source Preview</h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="mb-4">
            <span className="text-gray-600">Source:</span>
            <a
              href={source.sourceLink}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[#3D5AFE] underline mt-1 hover:text-blue-700 transition-colors"
            >
              <span className="break-all">{source.sourceLink}</span>
              <ExternalLink className="w-4 h-4 flex-shrink-0" />
            </a>
          </div>

          <div className="space-y-4">
            <p className="text-gray-700">
              In a recent press conference, officials discussed the ongoing negotiations
              regarding international trade agreements.
            </p>
            <p className="text-gray-700 bg-yellow-100 p-3 rounded-lg">
              {source.originalText}
            </p>
            <p className="text-gray-700">
              The statement was made in the context of broader diplomatic discussions
              involving multiple nations and addressing various economic concerns.
              Analysts have noted that the phrasing used in media reports may differ
              significantly from the original remarks.
            </p>
            <p className="text-gray-700">
              Further context suggests that the negotiations involved complex technical
              details that were simplified for public consumption. The full transcript
              of the remarks provides additional nuance not captured in brief excerpts.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-gray-200">
          <button
            onClick={() => window.open(source.sourceLink, '_blank')}
            className="w-full py-3 bg-[#3D5AFE] text-white rounded-xl hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
          >
            <span>Open Full Page</span>
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    </div>
  );
}
