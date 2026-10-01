import React from 'react';
import { useChat } from '../../context/ChatContext';

export default function ConversationsSidebar() {
  const { conversations, currentConversationId, setCurrentConversationId, createNewChat } = useChat();

  return (
    <aside className="w-[270px] min-w-[270px] bg-[rgba(10,15,29,0.95)] backdrop-blur-md border-r border-[var(--color-border)] flex flex-col p-4 gap-4 z-12">
      <div className="flex items-center gap-3 pb-4 border-b border-[var(--color-border)]">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--color-primary-cyan)] to-[var(--color-primary-purple)] flex items-center justify-center font-bold text-white text-lg tracking-wider shadow-[0_0_15px_rgba(6,182,212,0.4)]">
          NPN
        </div>
        <div className="flex flex-col">
          <h1 className="text-[var(--color-text-primary)] font-['Outfit'] text-[17px] font-bold tracking-wide m-0">Project NPN</h1>
          <span className="text-[var(--color-text-secondary)] text-[11px] uppercase tracking-widest mt-0.5">Multi-Doc QA</span>
        </div>
      </div>

      <button onClick={createNewChat} className="flex items-center justify-center gap-2 w-full p-3 bg-gradient-to-br from-[rgba(6,182,212,0.2)] to-[rgba(139,92,246,0.2)] border border-[rgba(6,182,212,0.4)] rounded-xl text-white font-['Outfit'] text-[13px] font-semibold cursor-pointer transition-all hover:bg-gradient-to-br hover:from-[rgba(6,182,212,0.35)] hover:to-[rgba(139,92,246,0.35)] hover:shadow-[0_4px_16px_rgba(6,182,212,0.25)] hover:-translate-y-[1px]">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        <span>New Conversation</span>
      </button>

      <button className="flex items-center justify-between gap-2 w-full p-2.5 bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] rounded-lg text-[var(--color-text-secondary)] font-['Inter'] text-[12px] font-medium cursor-pointer transition-all hover:bg-[rgba(255,255,255,0.08)] hover:text-white">
        <div className="flex items-center gap-2">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          <span>History & Archives</span>
        </div>
      </button>

      <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-2 relative scrollbar-thin scrollbar-thumb-[rgba(255,255,255,0.1)] scrollbar-track-transparent">
        <div className="text-[10px] font-bold text-[var(--color-text-muted)] uppercase tracking-widest pl-1 mb-1 mt-2">Recent Conversations</div>
        <div className="flex flex-col gap-2">
          {conversations.map(c => (
            <div 
              key={c.id} 
              onClick={() => setCurrentConversationId(c.id)}
              className={`p-3 rounded-xl cursor-pointer transition-all border ${c.id === currentConversationId ? 'bg-[rgba(6,182,212,0.1)] border-[rgba(6,182,212,0.3)] shadow-[0_4px_12px_rgba(0,0,0,0.2)] scale-[1.02]' : 'bg-[rgba(255,255,255,0.02)] border-transparent hover:bg-[rgba(255,255,255,0.04)] hover:border-[rgba(255,255,255,0.08)]'}`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className={`text-[13px] font-semibold truncate flex-1 font-['Outfit'] ${c.id === currentConversationId ? 'text-white' : 'text-[var(--color-text-primary)]'}`}>{c.title || 'New Conversation'}</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-[var(--color-text-muted)]">
                <span>{c.message_count || 0} messages</span>
                <span className="w-1 h-1 bg-[rgba(255,255,255,0.2)] rounded-full"></span>
                <span className="bg-[rgba(255,255,255,0.06)] text-[var(--color-text-secondary)] px-1.5 py-0.5 rounded-[4px] font-medium">{c.document_count || 0} docs</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="pt-4 border-t border-[var(--color-border)] flex flex-col gap-2 mt-auto">
        <div className="flex items-center gap-2 px-3 py-2 bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.2)] rounded-lg text-[11px] font-medium text-[var(--color-accent-green)]">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent-green)] shadow-[0_0_8px_var(--color-accent-green)] animate-pulse"></span>
          <span>Zero Spillover Partitioning</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 bg-[rgba(139,92,246,0.1)] border border-[rgba(139,92,246,0.2)] rounded-lg text-[11px] font-medium text-[var(--color-primary-purple)]">
          <span className="font-['JetBrains_Mono'] text-[9px] font-bold bg-[rgba(139,92,246,0.2)] px-1 py-0.5 rounded">BLOB</span>
          <span>100% Local-First Privacy</span>
        </div>
      </div>
    </aside>
  );
}
