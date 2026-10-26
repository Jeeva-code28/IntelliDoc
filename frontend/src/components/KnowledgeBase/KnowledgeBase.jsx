import React, { useRef } from 'react';
import { useChat } from '../../context/ChatContext';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Clock, Trash2, CheckSquare, Square, X, RefreshCw } from 'lucide-react';

export default function KnowledgeBase({ isOpen, onClose }) {
  const {
    activeConversation,
    uploadFiles,
    deleteDocument,
    uploadingFiles,
    uploadError,
    selectedDocIds,
    toggleDocSelection,
    selectAllDocs,
    clearDocSelection
  } = useChat();

  const fileInputRef = useRef(null);

  const handleDragOver = (e) => e.preventDefault();
  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFiles(e.dataTransfer.files);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(e.target.files);
    }
    e.target.value = null;
  };

  const docs = activeConversation?.documents || [];
  const readyDocs = docs.filter(d => d.status === 'ready');
  const allSelected = docs.length > 0 && docs.every(d => selectedDocIds.has(d.id));

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/60 z-30 lg:hidden backdrop-blur-xs"
        />
      )}

      <aside
        className={`fixed lg:static top-0 bottom-0 right-0 z-40 w-80 min-w-[20rem] bg-[#101010] border-l border-[#2B2B2B] flex flex-col p-4 gap-4 transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#2B2B2B]">
          <div className="flex flex-col">
            <span className="text-xs font-bold text-[#F5F1EC] uppercase tracking-wider">
              Document Library
            </span>
            <span className="text-[11px] text-[#A3A3A3]">
              {docs.length} {docs.length === 1 ? 'file' : 'files'} in this conversation
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 bg-[rgba(241,90,36,0.12)] border border-[rgba(241,90,36,0.28)] text-[#F15A24] text-[10px] font-bold rounded-md">
              {readyDocs.length} Ready
            </span>

            {/* Mobile close button */}
            <button
              onClick={onClose}
              className="lg:hidden p-1.5 text-[#A3A3A3] hover:text-[#F5F1EC] hover:bg-[#202020] rounded-lg cursor-pointer"
              aria-label="Close document library"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Upload Error Banner */}
        {uploadError && (
          <div className="p-3 bg-[rgba(229,115,115,0.1)] border border-[rgba(229,115,115,0.3)] rounded-xl text-xs text-[#E57373] flex items-start gap-2">
            <AlertCircle size={15} className="flex-shrink-0 mt-0.5" />
            <span className="leading-snug">{uploadError}</span>
          </div>
        )}

        {/* Drag and Drop Upload Zone */}
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          className="border-2 border-dashed border-[#2B2B2B] hover:border-[#F15A24] bg-[#171717] hover:bg-[#202020] rounded-xl p-5 flex flex-col items-center justify-center text-center cursor-pointer transition-all group"
        >
          <div className="w-10 h-10 rounded-full bg-[#242424] group-hover:bg-[rgba(241,90,36,0.15)] flex items-center justify-center mb-3 transition-colors">
            <UploadCloud size={20} className="text-[#A3A3A3] group-hover:text-[#F15A24] transition-colors" />
          </div>
          <p className="text-xs font-semibold text-[#F5F1EC] mb-1">
            Click to upload or drag files
          </p>
          <span className="text-[10px] text-[#A3A3A3] leading-tight">
            PDF, TXT, CSV, JSON, MD (up to 500 MB)
          </span>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.txt,.csv,.tsv,.json,.md,.markdown,.log"
            multiple
            className="hidden"
          />
        </div>

        {/* Active Ingestion Progress */}
        {uploadingFiles.length > 0 && (
          <div className="p-3 bg-[#171717] border border-[#2B2B2B] rounded-xl flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs text-[#E5B567]">
              <span className="flex items-center gap-1.5 font-medium">
                <RefreshCw size={13} className="animate-spin text-[#F15A24]" />
                Ingesting files...
              </span>
              <span className="text-[10px] text-[#A3A3A3]">{uploadingFiles.length} queued</span>
            </div>
            {uploadingFiles.map((fn, idx) => (
              <div key={idx} className="text-[11px] text-[#A3A3A3] truncate pl-5">
                • {fn}
              </div>
            ))}
          </div>
        )}

        {/* Document Selection Controls */}
        {docs.length > 0 && (
          <div className="flex items-center justify-between text-xs text-[#A3A3A3] px-1">
            <button
              onClick={allSelected ? clearDocSelection : selectAllDocs}
              className="flex items-center gap-1.5 text-xs text-[#A3A3A3] hover:text-[#F5F1EC] cursor-pointer"
            >
              {allSelected ? <CheckSquare size={13} className="text-[#F15A24]" /> : <Square size={13} />}
              <span>{allSelected ? 'Deselect All' : 'Select All'}</span>
            </button>
            <span className="text-[11px] text-[#737373]">
              {selectedDocIds.size} of {docs.length} active
            </span>
          </div>
        )}

        {/* Document List */}
        <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-2 scrollbar-thin">
          {docs.length === 0 ? (
            <div className="text-xs text-[#737373] text-center p-6 border border-dashed border-[#2B2B2B] rounded-xl leading-relaxed">
              No documents attached to this conversation. Upload a PDF or file above to ground your answers.
            </div>
          ) : (
            docs.map((d) => {
              const isSelected = selectedDocIds.has(d.id);
              const isReady = d.status === 'ready';
              const isProcessing = d.status === 'processing';
              const isFailed = d.status === 'failed';

              return (
                <div
                  key={d.id}
                  className={`p-3 rounded-xl border flex flex-col gap-2 transition-all ${
                    isSelected
                      ? 'bg-[#171717] border-[#2B2B2B]'
                      : 'bg-[#101010] border-[#1F1F1F] opacity-75'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2 min-w-0">
                      <button
                        onClick={() => toggleDocSelection(d.id)}
                        className="mt-0.5 text-[#A3A3A3] hover:text-[#F15A24] cursor-pointer"
                        title={isSelected ? 'Exclude from queries' : 'Include in queries'}
                      >
                        {isSelected ? (
                          <CheckSquare size={15} className="text-[#F15A24]" />
                        ) : (
                          <Square size={15} />
                        )}
                      </button>

                      <div className="min-w-0">
                        <span
                          className="text-xs font-semibold text-[#F5F1EC] block truncate"
                          title={d.filename}
                        >
                          {d.filename}
                        </span>
                        <div className="flex items-center gap-2 mt-1">
                          {isReady && (
                            <span className="flex items-center gap-1 text-[10px] text-[#72B47C] font-medium">
                              <CheckCircle2 size={11} />
                              Ready for QA
                            </span>
                          )}
                          {isProcessing && (
                            <span className="flex items-center gap-1 text-[10px] text-[#E5B567] font-medium">
                              <RefreshCw size={11} className="animate-spin text-[#F15A24]" />
                              Extracting & Embedding...
                            </span>
                          )}
                          {isFailed && (
                            <span className="flex items-center gap-1 text-[10px] text-[#E57373] font-medium">
                              <AlertCircle size={11} />
                              Processing Failed
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        if (window.confirm(`Delete ${d.filename}?`)) {
                          deleteDocument(d.id);
                        }
                      }}
                      className="p-1 text-[#737373] hover:text-[#E57373] hover:bg-[#202020] rounded cursor-pointer transition-colors"
                      title="Delete document"
                      aria-label="Delete document"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>

                  {d.error && (
                    <div className="text-[10px] text-[#E57373] bg-[rgba(229,115,115,0.08)] p-2 rounded border border-[rgba(229,115,115,0.2)]">
                      {d.error}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </aside>
    </>
  );
}
