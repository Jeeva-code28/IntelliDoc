import React, { useEffect } from 'react';
import { useChat } from '../../context/ChatContext';
import { X, FileText, ChevronLeft, ChevronRight, Hash, Layers, ShieldCheck, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function CitationDrawer() {
  const { selectedCitation, activeCitationsList, openCitation, closeCitation } = useChat();

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        closeCitation();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [closeCitation]);

  if (!selectedCitation) return null;

  const currentIndex = activeCitationsList.findIndex(
    (c) => c.chunk_id === selectedCitation.chunk_id
  );

  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex >= 0 && currentIndex < activeCitationsList.length - 1;

  const handlePrev = () => {
    if (hasPrev) {
      openCitation(activeCitationsList[currentIndex - 1], activeCitationsList);
    }
  };

  const handleNext = () => {
    if (hasNext) {
      openCitation(activeCitationsList[currentIndex + 1], activeCitationsList);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-end">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={closeCitation}
          className="absolute inset-0 bg-black/60 backdrop-blur-xs"
        />

        {/* Sliding Side Panel */}
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 28, stiffness: 300 }}
          className="relative w-full max-w-lg h-full bg-[#171717] border-l border-[#2B2B2B] flex flex-col shadow-2xl z-10"
        >
          {/* Header */}
          <div className="p-5 border-b border-[#2B2B2B] bg-[#101010] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-[rgba(241,90,36,0.15)] border border-[rgba(241,90,36,0.3)] flex items-center justify-center text-[#F15A24] font-bold text-xs">
                S{currentIndex >= 0 ? currentIndex + 1 : 1}
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#F5F1EC] m-0">Verified Source Evidence</h3>
                <span className="text-xs text-[#A3A3A3]">Grounding proof for generated claim</span>
              </div>
            </div>

            <button
              onClick={closeCitation}
              aria-label="Close evidence panel"
              className="p-1.5 rounded-lg text-[#A3A3A3] hover:text-[#F5F1EC] hover:bg-[#202020] transition-colors cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          {/* Navigation Controls between citations */}
          {activeCitationsList.length > 1 && (
            <div className="px-5 py-2.5 bg-[#202020] border-b border-[#2B2B2B] flex items-center justify-between text-xs text-[#A3A3A3]">
              <span>
                Citation <strong className="text-[#F5F1EC]">{currentIndex + 1}</strong> of <strong className="text-[#F5F1EC]">{activeCitationsList.length}</strong>
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={handlePrev}
                  disabled={!hasPrev}
                  className="p-1 rounded bg-[#171717] border border-[#2B2B2B] text-[#F5F1EC] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#242424] cursor-pointer flex items-center gap-1"
                >
                  <ChevronLeft size={14} />
                  <span>Prev</span>
                </button>
                <button
                  onClick={handleNext}
                  disabled={!hasNext}
                  className="p-1 rounded bg-[#171717] border border-[#2B2B2B] text-[#F5F1EC] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#242424] cursor-pointer flex items-center gap-1"
                >
                  <span>Next</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Metadata Badges */}
          <div className="p-5 border-b border-[#2B2B2B] flex flex-wrap gap-2.5 bg-[#171717]">
            <div className="flex items-center gap-1.5 px-3 py-1 bg-[#202020] border border-[#2B2B2B] rounded-md text-xs text-[#F5F1EC]">
              <FileText size={13} className="text-[#F15A24]" />
              <span className="font-medium truncate max-w-[240px]" title={selectedCitation.document_name || selectedCitation.filename}>
                {(selectedCitation.document_name || selectedCitation.filename || '').replace(/^[0-9a-fA-F-]{36}_/, '')}
              </span>
            </div>

            <div className="flex items-center gap-1 px-2.5 py-1 bg-[#202020] border border-[#2B2B2B] rounded-md text-xs text-[#E5B567]">
              <Hash size={12} className="text-[#E5B567]" />
              <span>Page {selectedCitation.page_number || 1}</span>
            </div>

            {selectedCitation.content_type && (
              <div className="flex items-center gap-1 px-2.5 py-1 bg-[#202020] border border-[#2B2B2B] rounded-md text-xs text-[#A3A3A3] capitalize">
                <Layers size={12} className="text-[#72B47C]" />
                <span>{selectedCitation.content_type}</span>
              </div>
            )}

            {selectedCitation.score !== undefined && (
              <div className="flex items-center gap-1 px-2.5 py-1 bg-[rgba(241,90,36,0.1)] border border-[rgba(241,90,36,0.25)] rounded-md text-xs text-[#F15A24] font-medium">
                <ShieldCheck size={12} />
                <span>Score: {Number(selectedCitation.score).toFixed(2)}</span>
              </div>
            )}
          </div>

          {/* Source Text / Excerpt Body */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {selectedCitation.section && (
              <div>
                <span className="text-[11px] font-bold text-[#A3A3A3] uppercase tracking-wider block mb-1">
                  Document Section
                </span>
                <p className="text-xs font-semibold text-[#F5F1EC] bg-[#202020] p-2.5 rounded-lg border border-[#2B2B2B]">
                  {selectedCitation.section_heading || selectedCitation.section}
                </p>
              </div>
            )}

            <div>
              <span className="text-[11px] font-bold text-[#A3A3A3] uppercase tracking-wider block mb-2">
                Extracted Supporting Passage
              </span>
              <div className="bg-[#101010] border border-[#2B2B2B] rounded-xl p-4 text-[13px] leading-relaxed text-[#F5F1EC] whitespace-pre-wrap font-sans font-normal">
                {(selectedCitation.excerpt || selectedCitation.snippet || 'No excerpt available.').replace(/^Page\s*\d+\s*\|\s*Section:[^\n]+\n+/, '')}
              </div>
            </div>

            {/* Asset preview if applicable */}
            {selectedCitation.asset_path && (
              <div>
                <span className="text-[11px] font-bold text-[#A3A3A3] uppercase tracking-wider block mb-2">
                  Extracted Media Preview
                </span>
                <div className="rounded-xl overflow-hidden border border-[#2B2B2B] bg-[#101010]">
                  <img
                    src={`/assets/${selectedCitation.asset_path.replace(/\\/g, '/').split('/').pop()}`}
                    alt="Source visual evidence"
                    className="w-full max-h-60 object-contain"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-[#2B2B2B] bg-[#101010] flex items-center justify-between text-xs text-[#A3A3A3]">
            <span>Chunk ID: {selectedCitation.chunk_id?.slice(0, 12)}...</span>
            <button
              onClick={closeCitation}
              className="px-4 py-1.5 bg-[#202020] hover:bg-[#2B2B2B] text-[#F5F1EC] rounded-lg transition-colors cursor-pointer font-medium"
            >
              Done
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
