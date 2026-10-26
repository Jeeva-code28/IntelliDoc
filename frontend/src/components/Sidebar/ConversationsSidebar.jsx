import React from 'react';
import { useChat } from '../../context/ChatContext';
import { Plus, MessageSquare, Trash2, Shield, Lock, FileText, Cpu, X } from 'lucide-react';

export default function ConversationsSidebar({ isOpen, onClose }) {
  const {
    conversations,
    currentConversationId,
    setCurrentConversationId,
    createNewChat,
    deleteConversation,
    provider,
    setProvider
  } = useChat();

  const handleSelectConv = (id) => {
    setCurrentConversationId(id);
    if (onClose) onClose();
  };

  const handleDelete = (e, id) => {
    e.stopPropagation();
    if (window.confirm('Delete this conversation and its active memory partitions?')) {
      deleteConversation(id);
    }
  };

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
        className={`fixed lg:static top-0 bottom-0 left-0 z-40 w-72 min-w-[18rem] bg-[#101010] border-r border-[#2B2B2B] flex flex-col p-4 gap-4 transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#2B2B2B]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#F15A24] flex items-center justify-center font-bold text-white shadow-[0_2px_12px_rgba(241,90,36,0.3)]">
              <FileText size={20} className="text-[#F5F1EC]" />
            </div>
            <div className="flex flex-col">
              <span className="text-[#F5F1EC] font-bold text-base tracking-tight font-heading">
                Intelli<span className="text-[#F15A24]">Doc</span>
              </span>
              <span className="text-[#A3A3A3] text-[11px] tracking-wide font-medium">
                Document Intelligence
              </span>
            </div>
          </div>

          {/* Close button for mobile */}
          <button
            onClick={onClose}
            className="lg:hidden p-1.5 text-[#A3A3A3] hover:text-[#F5F1EC] hover:bg-[#202020] rounded-lg cursor-pointer"
            aria-label="Close navigation sidebar"
          >
            <X size={18} />
          </button>
        </div>

        {/* New Chat Primary Action */}
        <button
          onClick={async () => {
            await createNewChat();
            if (onClose) onClose();
          }}
          className="flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-[#F15A24] hover:bg-[#FF6A35] text-[#F5F1EC] font-semibold text-xs rounded-xl shadow-[0_2px_8px_rgba(241,90,36,0.25)] transition-all cursor-pointer hover:-translate-y-0.5 active:translate-y-0"
        >
          <Plus size={16} />
          <span>New Conversation</span>
        </button>

        {/* LLM Provider Selection */}
        <div className="flex flex-col gap-1.5 bg-[#171717] border border-[#2B2B2B] p-2.5 rounded-xl">
          <label className="text-[11px] font-bold text-[#A3A3A3] uppercase tracking-wider flex items-center gap-1.5">
            <Cpu size={12} className="text-[#F15A24]" />
            <span>Inference Model</span>
          </label>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="bg-[#202020] border border-[#2B2B2B] text-[#F5F1EC] text-xs rounded-lg px-2.5 py-1.5 outline-none cursor-pointer focus:border-[#F15A24] transition-colors"
          >
            <option value="huggingface">Hugging Face (DeepSeek-V4)</option>
            <option value="ollama">Ollama (Llama-3.1 8B Local)</option>
            <option value="gemini">Gemini Flash (Google AI)</option>
            <option value="groq">Groq (Llama-3.3 70B)</option>
            <option value="openai">OpenAI (GPT-4o-mini)</option>
          </select>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-1.5 scrollbar-thin">
          <div className="text-[10px] font-bold text-[#737373] uppercase tracking-widest px-1 mb-1">
            Recent Conversations
          </div>

          {conversations.length === 0 ? (
            <div className="p-4 text-xs text-[#737373] text-center border border-dashed border-[#2B2B2B] rounded-xl">
              No conversations yet. Start a new chat above.
            </div>
          ) : (
            conversations.map((c) => {
              const isActive = c.id === currentConversationId;
              return (
                <div
                  key={c.id}
                  onClick={() => handleSelectConv(c.id)}
                  className={`group relative p-3 rounded-xl cursor-pointer transition-all border text-left flex flex-col gap-1 ${
                    isActive
                      ? 'bg-[rgba(241,90,36,0.1)] border-[rgba(241,90,36,0.4)] shadow-[0_2px_8px_rgba(0,0,0,0.4)]'
                      : 'bg-[#171717] border-[#2B2B2B] hover:bg-[#202020] hover:border-[#3D3D3D]'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`text-xs font-semibold truncate ${
                        isActive ? 'text-[#F5F1EC]' : 'text-[#A3A3A3] group-hover:text-[#F5F1EC]'
                      }`}
                      title={c.title || 'Untitled Conversation'}
                    >
                      {c.title || 'New Conversation'}
                    </span>

                    <button
                      onClick={(e) => handleDelete(e, c.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-[#737373] hover:text-[#E57373] hover:bg-[#242424] rounded transition-all cursor-pointer"
                      title="Delete conversation"
                      aria-label="Delete conversation"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>

                  <div className="flex items-center gap-2 text-[10px] text-[#737373]">
                    <span>{c.message_count || 0} msgs</span>
                    <span>•</span>
                    <span className="px-1.5 py-0.2 bg-[#202020] text-[#A3A3A3] rounded font-medium">
                      {c.document_count || 0} docs
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Security & Partitioning Footer */}
        <div className="pt-3 border-t border-[#2B2B2B] flex flex-col gap-2 mt-auto text-[11px]">
          <div className="flex items-center gap-2 px-3 py-2 bg-[#171717] border border-[#2B2B2B] rounded-lg text-[#72B47C] font-medium">
            <Shield size={14} className="text-[#72B47C] flex-shrink-0" />
            <span>Zero Spillover Isolation</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 bg-[#171717] border border-[#2B2B2B] rounded-lg text-[#A3A3A3] font-medium">
            <Lock size={14} className="text-[#E5B567] flex-shrink-0" />
            <span>100% Local-First Storage</span>
          </div>
        </div>
      </aside>
    </>
  );
}
