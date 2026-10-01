import React, { useState } from 'react';
import { useChat } from '../../context/ChatContext';

export default function ChatWorkspace() {
  const { activeConversation, sendMessage, deleteConversation } = useChat();
  const [inputValue, setInputValue] = useState('');
  const [provider, setProvider] = useState('ollama');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim() && activeConversation) {
      sendMessage(inputValue, provider);
      setInputValue('');
    }
  };

  const handleDelete = () => {
    if (activeConversation && window.confirm("Delete this conversation?")) {
      deleteConversation(activeConversation.id);
    }
  };

  const messages = activeConversation?.messages || [];

  return (
    <main className="flex-1 flex flex-col min-w-0 bg-transparent border-r border-[var(--color-border)] relative">
      {/* Header Bar */}
      <header className="h-[70px] min-h-[70px] border-b border-[var(--color-border)] bg-[rgba(10,15,29,0.85)] backdrop-blur-md px-6 flex items-center justify-between z-10">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <h2 className="m-0 text-[16px] font-bold text-white font-['Outfit']">{activeConversation?.title || 'Active Conversation'}</h2>
            <span className="bg-[rgba(16,185,129,0.1)] text-[var(--color-accent-green)] border border-[rgba(16,185,129,0.3)] text-[10px] font-bold px-2 py-0.5 rounded-[4px]">Conversation-Isolated</span>
          </div>
          <p className="m-0 text-[12px] text-[var(--color-text-secondary)]">Grounded Multimodal Q&A with Fact Verification & Source Citations</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleDelete} className="flex items-center gap-1.5 px-3 py-1.5 bg-[rgba(239,68,68,0.1)] text-[var(--color-accent-rose)] border border-[rgba(239,68,68,0.3)] rounded-md text-[11px] font-semibold cursor-pointer hover:bg-[rgba(239,68,68,0.2)]">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
            <span>Delete Chat</span>
          </button>
          <select value={provider} onChange={e => setProvider(e.target.value)} className="bg-[rgba(17,24,39,0.7)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded-md px-3 py-1.5 text-[12px] font-medium outline-none cursor-pointer focus:border-[var(--color-border-highlight)]">
            <option value="ollama">Ollama (Llama-3.1 8B Instruct Local)</option>
            <option value="gemini">Gemini Flash (Google AI)</option>
            <option value="groq">Groq (Llama-3.3 70B)</option>
            <option value="openai">OpenAI (GPT-4o-mini)</option>
          </select>
        </div>
      </header>

      {/* Chat Body Layout */}
      <div className="flex-1 flex overflow-hidden relative">
        <div className="flex-1 overflow-y-auto p-6 scroll-smooth scrollbar-thin scrollbar-thumb-[rgba(255,255,255,0.1)] scrollbar-track-transparent">
          {messages.length === 0 ? (
            <div className="max-w-[700px] mx-auto mt-[10vh] bg-[rgba(17,24,39,0.7)] border border-[var(--color-border)] rounded-2xl p-8 relative overflow-hidden text-center">
              <div className="text-4xl mb-4">⚡</div>
              <h3 className="text-xl font-bold text-white mb-2 font-['Outfit']">Conversation-Scoped Multimodal Workspace</h3>
              <p className="text-[14px] text-[var(--color-text-secondary)] leading-relaxed mb-6">
                Each conversation maintains its own private knowledge base. Upload 1 or more documents, switch between conversations, or return anytime with zero knowledge spillover.
              </p>
              <div className="flex flex-col gap-2">
                <button onClick={() => setInputValue('What is the total revenue and profit breakdown in the uploaded documents?')} className="bg-[rgba(255,255,255,0.03)] border border-[var(--color-border)] hover:border-[var(--color-border-highlight)] hover:bg-[rgba(6,182,212,0.1)] text-[13px] text-white p-3 rounded-lg text-left transition-all">
                  📊 Financial Table Analysis
                </button>
                <button onClick={() => setInputValue('What executive remarks and decisions are recorded in the attached files?')} className="bg-[rgba(255,255,255,0.03)] border border-[var(--color-border)] hover:border-[var(--color-border-highlight)] hover:bg-[rgba(6,182,212,0.1)] text-[13px] text-white p-3 rounded-lg text-left transition-all">
                  🎙️ Executive Remarks & Audio
                </button>
                <button onClick={() => setInputValue('Summarize key quantitative metrics and findings from all files in this chat.')} className="bg-[rgba(255,255,255,0.03)] border border-[var(--color-border)] hover:border-[var(--color-border-highlight)] hover:bg-[rgba(6,182,212,0.1)] text-[13px] text-white p-3 rounded-lg text-left transition-all">
                  📑 Multi-Document Summary
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4 max-w-[900px] mx-auto pb-4">
              {messages.map((m, idx) => (
                <div key={idx} className={`p-4 rounded-xl ${m.role === 'user' ? 'bg-[rgba(255,255,255,0.05)] ml-auto max-w-[80%] border border-[var(--color-border)]' : 'bg-[rgba(6,182,212,0.05)] mr-auto max-w-[90%] border border-[rgba(6,182,212,0.2)]'}`}>
                  {m.role === 'user' && <div className="text-[10px] text-[var(--color-primary-cyan)] mb-1 font-bold uppercase tracking-wider">You</div>}
                  {m.role !== 'user' && <div className="text-[10px] text-[var(--color-primary-purple)] mb-1 font-bold uppercase tracking-wider">Assistant</div>}
                  <div className="text-white text-[14px] leading-relaxed whitespace-pre-wrap">{m.content}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Input Bar */}
      <div className="p-4 px-6 bg-[rgba(10,15,29,0.95)] backdrop-blur-md border-t border-[var(--color-border)] relative z-10">
        <form onSubmit={handleSubmit} className="relative max-w-[900px] mx-auto flex items-end bg-[rgba(17,24,39,0.8)] border border-[var(--color-border)] rounded-xl transition-all focus-within:border-[var(--color-border-highlight)] focus-within:shadow-[0_0_20px_rgba(6,182,212,0.15)] shadow-lg">
          <input 
            type="text" 
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask a question grounded in this conversation's documents..." 
            className="flex-1 bg-transparent border-none text-[14px] text-white p-4 pl-5 outline-none placeholder-[var(--color-text-muted)] min-h-[54px]" 
          />
          <button type="submit" disabled={!inputValue.trim()} className="m-2 ml-0 px-4 py-2 bg-gradient-to-br from-[var(--color-primary-cyan)] to-[var(--color-primary-purple)] text-white rounded-lg font-bold text-[13px] flex items-center gap-2 hover:opacity-90 transition-opacity min-h-[38px] disabled:opacity-50">
            <span>Ask</span>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </form>
      </div>
    </main>
  );
}
