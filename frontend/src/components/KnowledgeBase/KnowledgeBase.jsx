import React, { useRef } from 'react';
import { useChat } from '../../context/ChatContext';

export default function KnowledgeBase() {
  const { activeConversation, uploadFiles } = useChat();
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => e.preventDefault();
  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      uploadFiles(e.dataTransfer.files);
    }
  };
  const handleFileClick = () => fileInputRef.current?.click();
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(e.target.files);
    }
  };

  const docs = activeConversation?.documents || [];

  return (
    <aside className="w-[280px] min-w-[280px] bg-[rgba(10,15,29,0.95)] backdrop-blur-md flex flex-col p-4 gap-4 z-12">
      <div className="flex flex-col gap-1 pb-3 border-b border-[var(--color-border)]">
        <div className="flex items-center justify-between">
          <span className="text-[13px] font-bold text-[var(--color-text-primary)] uppercase tracking-wider">Active Knowledge Base</span>
          <span className="bg-[rgba(6,182,212,0.1)] text-[var(--color-primary-cyan)] border border-[rgba(6,182,212,0.3)] text-[10px] font-bold px-2 py-0.5 rounded-[4px]">{docs.length} files</span>
        </div>
        <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">Documents strictly scoped to current conversation</p>
      </div>

      <div className="flex flex-col gap-3">
        <div 
          onClick={handleFileClick}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          className="border-2 border-dashed border-[var(--color-border)] rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-all hover:border-[var(--color-border-highlight)] hover:bg-[rgba(255,255,255,0.02)] group"
        >
          <svg className="w-8 h-8 text-[var(--color-text-muted)] mb-3 transition-colors group-hover:text-[var(--color-primary-cyan)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          <p className="text-[13px] font-semibold text-[var(--color-text-primary)] mb-1">Upload to this Chat</p>
          <span className="text-[10px] text-[var(--color-text-secondary)]">PDF, TXT, CSV, Video, Audio, ZIP</span>
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange}
            accept=".pdf,.png,.jpg,.jpeg,.webp,.mp4,.mov,.avi,.mp3,.wav,.csv,.tsv,.zip,.txt,.md,.markdown,.log,.json" 
            multiple 
            className="hidden" 
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-2 scrollbar-thin scrollbar-thumb-[rgba(255,255,255,0.1)] scrollbar-track-transparent">
        {docs.length === 0 ? (
          <div className="text-[12px] text-[var(--color-text-muted)] text-center p-4 border border-dashed border-[var(--color-border)] rounded-lg">
            No documents in this conversation. Drag files above to build its knowledge base.
          </div>
        ) : (
          docs.map((d, i) => (
            <div key={i} className="flex flex-col gap-1 p-2 bg-[rgba(255,255,255,0.03)] border border-[var(--color-border)] rounded-lg">
              <span className="text-[13px] text-white truncate" title={d.filename}>📄 {d.filename}</span>
              <span className="text-[10px] text-[var(--color-text-secondary)]">{d.status}</span>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
