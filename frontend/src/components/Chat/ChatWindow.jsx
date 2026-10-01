import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../../context/ChatContext';
import { MessageSquare, X, Paperclip, Send, Plus, Trash2, ChevronDown, File } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import DOMPurify from 'dompurify';
import Tilt from 'react-parallax-tilt';
import TypingIndicator from './TypingIndicator';

export default function ChatWindow() {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [provider, setProvider] = useState('ollama');
  const [showHistory, setShowHistory] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const historyDropdownRef = useRef(null);

  const { 
    conversations, 
    currentConversationId, 
    setCurrentConversationId, 
    createNewChat, 
    activeConversation, 
    sendMessage, 
    deleteConversation,
    uploadFiles
  } = useChat();

  const messages = activeConversation?.messages || [];
  const docs = activeConversation?.documents || [];

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  // Click outside history dropdown to close it
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (historyDropdownRef.current && !historyDropdownRef.current.contains(event.target)) {
        setShowHistory(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (inputValue.trim()) {
      const userMessage = inputValue;
      setInputValue('');
      setIsGenerating(true);
      await sendMessage(userMessage, provider);
      setIsGenerating(false);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(e.target.files);
    }
    e.target.value = null; 
  };

  const handleDelete = () => {
    if (currentConversationId && window.confirm("Delete this conversation?")) {
      deleteConversation(currentConversationId);
    }
  };

  const toggleWidget = () => setIsOpen(!isOpen);

  // Markdown rendering components for clean typography
  const MarkdownComponents = {
    p: ({node, ...props}) => <p className="mb-2 leading-relaxed" {...props} />,
    a: ({node, ...props}) => <a className="text-[var(--color-accent-indigo)] hover:underline" {...props} />,
    ul: ({node, ...props}) => <ul className="list-disc pl-4 mb-2 space-y-1" {...props} />,
    ol: ({node, ...props}) => <ol className="list-decimal pl-4 mb-2 space-y-1" {...props} />,
    li: ({node, ...props}) => <li className="pl-1" {...props} />,
    h1: ({node, ...props}) => <h1 className="text-xl font-semibold mt-4 mb-2" {...props} />,
    h2: ({node, ...props}) => <h2 className="text-lg font-semibold mt-4 mb-2" {...props} />,
    h3: ({node, ...props}) => <h3 className="text-md font-semibold mt-3 mb-2" {...props} />,
    pre: ({node, ...props}) => <pre className="bg-[var(--color-bg-main)] p-3 rounded-lg overflow-x-auto my-3 text-[12px] font-mono border border-[var(--color-border)]" {...props} />,
    code: ({node, inline, ...props}) => 
      inline 
        ? <code className="bg-[var(--color-bg-main)] px-1.5 py-0.5 rounded text-[12px] font-mono text-[var(--color-text-secondary)] border border-[var(--color-border)]" {...props} />
        : <code {...props} />
  };

  return (
    <>
      {/* Floating Action Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button 
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={toggleWidget}
            className="fixed bottom-6 right-6 w-14 h-14 bg-[var(--color-accent-indigo)] hover:bg-[var(--color-accent-indigo-hover)] rounded-2xl flex items-center justify-center text-white z-50 cursor-pointer border-none outline-none shadow-lg"
          >
            <MessageSquare size={24} />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat Window Panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Blurred Background Overlay */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
              onClick={toggleWidget}
            />
            
            <motion.div 
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.95 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="fixed bottom-6 right-6 w-[1000px] h-[100vh] max-h-[900px] min-h-[500px] bg-[var(--color-bg-main)] border border-[var(--color-border)] rounded-2xl shadow-2xl flex flex-col z-50 overflow-hidden font-sans"
            >
              {/* Header */}
              <header className="flex flex-col bg-[var(--color-bg-surface)] border-b border-[var(--color-border)] p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[var(--color-accent-indigo)] flex items-center justify-center font-bold text-white text-xs tracking-wider">
                      NPN
                    </div>
                    <h3 className="font-semibold text-white text-sm m-0">Project NPN</h3>
                  </div>
                  <button onClick={toggleWidget} className="text-[var(--color-text-secondary)] hover:text-white transition-colors bg-transparent border-none cursor-pointer">
                    <X size={20} />
                  </button>
                </div>
                
                {/* Top Navigation Controls */}
                <div className="flex items-center gap-2">
                  {/* History Dropdown */}
                  <div className="relative" ref={historyDropdownRef}>
                    <button 
                      onClick={() => setShowHistory(!showHistory)}
                      className="flex items-center gap-2 px-3 py-1.5 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg text-xs text-white hover:bg-[var(--color-border-highlight)] transition-colors cursor-pointer font-medium"
                    >
                      <span>History</span>
                    </button>
                    
                    <AnimatePresence>
                      {showHistory && (
                        <motion.div 
                          initial={{ opacity: 0, y: -5 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -5 }}
                          className="absolute top-full left-0 mt-2 w-64 max-h-64 overflow-y-auto bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-xl shadow-xl z-50 p-1.5 flex flex-col gap-1 scrollbar-thin scrollbar-thumb-[var(--color-border-highlight)] scrollbar-track-transparent"
                        >
                          {conversations.length === 0 ? (
                            <div className="p-3 text-xs text-[var(--color-text-muted)] text-center">No history found</div>
                          ) : (
                            conversations.map(c => (
                              <button 
                                key={c.id}
                                onClick={() => {
                                  setCurrentConversationId(c.id);
                                  setShowHistory(false);
                                }}
                                className={`flex items-center justify-between w-full text-left px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${c.id === currentConversationId ? 'bg-[var(--color-accent-indigo)]/10 text-[var(--color-accent-indigo)] font-medium' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)] hover:text-white'}`}
                              >
                                <span className="truncate">{c.title || 'Conversation'}</span>
                              </button>
                            ))
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  {/* New Chat Button */}
                  <button 
                    onClick={createNewChat}
                    title="New Conversation"
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--color-accent-indigo)]/10 border border-[var(--color-accent-indigo)]/20 text-[var(--color-accent-indigo)] rounded-lg text-xs font-medium hover:bg-[var(--color-accent-indigo)]/20 transition-colors cursor-pointer"
                  >
                    <Plus size={14} />
                    <span>New Conversation</span>
                  </button>

                  {/* Delete Button */}
                  <button 
                    onClick={handleDelete}
                    title="Delete Chat"
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 border border-red-500/20 text-red-500 rounded-lg text-xs font-medium hover:bg-red-500/20 transition-colors cursor-pointer"
                  >
                    <Trash2 size={14} />
                    <span>Delete Conversation</span>
                  </button>

                  {/* Model Switcher */}
                  <select 
                    value={provider} 
                    onChange={(e) => setProvider(e.target.value)}
                    className="ml-auto bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg px-3 py-1.5 text-[11px] font-medium outline-none cursor-pointer focus:border-[var(--color-accent-indigo)]/50 transition-colors w-32 [&>option]:bg-[var(--color-bg-surface)] [&>option]:text-white"
                  >
                    <option value="ollama">Ollama (Llama-3.1)</option>
                    <option value="gemini">Gemini Flash</option>
                    <option value="groq">Groq (Llama-3.3)</option>
                    <option value="openai">OpenAI (GPT-4o-m)</option>
                  </select>
                </div>
              </header>

              {/* Messages Body */}
              <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 scroll-smooth scrollbar-thin scrollbar-thumb-[var(--color-border-highlight)] scrollbar-track-transparent">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center px-4">
                    <div className="w-16 h-16 bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-2xl flex items-center justify-center mb-6 shadow-sm">
                      <span className="text-2xl text-[var(--color-text-muted)]">⚡</span>
                    </div>
                    <h4 className="text-[var(--color-text-primary)] font-semibold mb-2">How can I help you today?</h4>
                    <p className="text-[13px] text-[var(--color-text-secondary)] max-w-sm leading-relaxed">
                      Start typing a question below or attach documents to create a grounded knowledge base for this session.
                    </p>
                  </div>
                ) : (
                  messages.map((m, idx) => (
                    <div key={idx} className={`flex flex-col max-w-[85%] ${m.role === 'user' ? 'ml-auto items-end' : 'mr-auto items-start'}`}>
                      <div className="text-[10px] text-[var(--color-text-muted)] mb-1.5 font-medium uppercase tracking-wider px-1">
                        {m.role === 'user' ? 'You' : 'Project NPN'}
                      </div>
                      <div className={`p-4 text-[14px] leading-relaxed ${m.role === 'user' ? 'bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-2xl rounded-tr-sm text-[var(--color-text-primary)]' : 'bg-transparent text-[var(--color-text-primary)]'}`}>
                        {m.role === 'user' ? (
                          m.content
                        ) : (
                          <div className="markdown-body text-[14px]">
                            <ReactMarkdown 
                              components={MarkdownComponents}
                            >
                              {DOMPurify.sanitize(m.content)}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                
                {isGenerating && (
                  <div className="mr-auto items-start">
                    <div className="text-[10px] text-[var(--color-text-muted)] mb-1.5 font-medium uppercase tracking-wider px-1">
                      Project NPN
                    </div>
                    <TypingIndicator />
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Footer Area */}
              <div className="p-4 bg-[var(--color-bg-main)] border-t border-[var(--color-border)]">
                <form onSubmit={handleSubmit} className="flex flex-col gap-2 bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-2xl focus-within:border-[var(--color-border-highlight)] transition-colors p-2 shadow-sm">
                  

                  {/* Document Indicator Badges */}
                  {docs.length > 0 && (
                    <div className="flex flex-wrap gap-2 px-3 pt-2">
                      {docs.map((d, i) => (
                        <Tilt key={i} tiltMaxAngleX={10} tiltMaxAngleY={10} scale={1.05} transitionSpeed={2500} glareEnable={true} glareMaxOpacity={0.15}>
                          <div className="flex items-center gap-1.5 bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] border border-[var(--color-border)] px-2.5 py-1 rounded-lg text-[11px] max-w-[150px] cursor-pointer shadow-sm" title={d.filename}>
                            <File size={12} className="text-[var(--color-text-muted)]" />
                            <span className="truncate font-medium">{d.filename}</span>
                          </div>
                        </Tilt>
                      ))}
                    </div>
                  )}

                  {/* Main Input Row */}
                  <div className="flex items-end gap-3 px-1 pb-1">
                    {/* Upload Button */}
                    <button 
                      type="button" 
                      onClick={() => fileInputRef.current?.click()}
                      className="p-2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)] rounded-xl transition-colors cursor-pointer mb-0.5"
                      title="Attach files"
                    >
                      <Paperclip size={18} />
                    </button>
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      onChange={handleFileChange}
                      accept=".pdf,.png,.jpg,.jpeg,.webp,.mp4,.mov,.avi,.mp3,.wav,.csv,.tsv,.zip,.txt,.md,.markdown,.log,.json" 
                      multiple 
                      className="hidden" 
                    />

                    {/* Text Input */}
                    <textarea 
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSubmit(e);
                        }
                      }}
                      placeholder="Ask a question..." 
                      className="flex-1 bg-transparent border-none text-[14px] text-[var(--color-text-primary)] py-2.5 outline-none placeholder-[var(--color-text-muted)] resize-none min-h-[44px] max-h-[150px] scrollbar-thin scrollbar-thumb-[var(--color-border-highlight)]"
                      rows={1}
                    />

                    {/* Send Button */}
                    <button 
                      type="submit" 
                      disabled={!inputValue.trim()} 
                      className="p-2.5 mb-0.5 bg-[var(--color-accent-indigo)] hover:bg-[var(--color-accent-indigo-hover)] text-white rounded-xl flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                    >
                      <Send size={16} />
                    </button>
                  </div>
                </form>
                <div className="text-center mt-3 text-[10px] text-[var(--color-text-muted)] font-medium">
                  Project NPN • Grounded Multimodal AI
                </div>
              </div>

            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
