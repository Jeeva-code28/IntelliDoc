import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../../context/ChatContext';
import { MessageSquare, X, Paperclip, Send, Plus, Trash2, ChevronDown, File, Volume2, Square, Mic, AlertCircle, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import DOMPurify from 'dompurify';
import Tilt from 'react-parallax-tilt';
import TypingIndicator from './TypingIndicator';

const stripMarkdown = (text) => {
  if (!text) return '';
  return text
    .replace(/(\*\*|__)(.*?)\1/g, '$2')
    .replace(/(\*|_)(.*?)\1/g, '$2')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '')
    .replace(/`{3}[\s\S]*?`{3}/g, ' code block ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^#+\s+/gm, '')
    .replace(/>\s+/g, '')
    .replace(/[-*+]\s+/g, '')
    .replace(/\n+/g, ' ')
    .trim();
};

export default function ChatWindow({ defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [inputValue, setInputValue] = useState('');
  const [provider, setProvider] = useState('huggingface');
  const [showHistory, setShowHistory] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // Voice state
  const [speakingMessageIndex, setSpeakingMessageIndex] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [sttError, setSttError] = useState(null);
  const recognitionRef = useRef(null);
  const baseInputTextRef = useRef('');

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
    uploadFiles,
    deleteDocument
  } = useChat();

  const messages = activeConversation?.messages || [];
  const docs = activeConversation?.documents || [];

  // STT Initialization
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
        setSttError(null);
      };

      recognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }
        setInputValue(baseInputTextRef.current + transcript);
      };

      recognition.onerror = (event) => {
        console.error("STT Error:", event.error);
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          setSttError('not-allowed');
        }
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  // Cleanup TTS/STT on unmount or conversation change
  useEffect(() => {
    window.speechSynthesis?.cancel();
    setSpeakingMessageIndex(null);
    if (recognitionRef.current) {
      recognitionRef.current.abort();
      setIsListening(false);
    }

    return () => {
      window.speechSynthesis?.cancel();
      if (recognitionRef.current) recognitionRef.current.abort();
    };
  }, [currentConversationId]);

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

  const handleTTS = (text, index) => {
    window.speechSynthesis.cancel();
    if (speakingMessageIndex === index) {
      setSpeakingMessageIndex(null);
      return;
    }

    const cleanText = stripMarkdown(text);
    const utterance = new SpeechSynthesisUtterance(cleanText);

    // Pick a more human-like voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferredVoices = voices.filter(v =>
      v.name.includes('Google') ||
      v.name.includes('Natural') ||
      v.name.includes('Premium') ||
      v.name.includes('Samantha') ||
      v.name.includes('Daniel')
    );
    if (preferredVoices.length > 0) {
      utterance.voice = preferredVoices[0];
    }

    utterance.rate = 0.95; // Slightly slower for better understandability
    utterance.pitch = 1.0;

    utterance.onstart = () => setSpeakingMessageIndex(index);
    utterance.onend = () => setSpeakingMessageIndex(null);
    utterance.onerror = (e) => {
      console.error("TTS Error:", e);
      setSpeakingMessageIndex(null);
    };

    window.speechSynthesis.speak(utterance);
  };

  const toggleListen = () => {
    if (!recognitionRef.current) {
      alert("Voice input is not supported in this browser.");
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      setSttError(null);
      baseInputTextRef.current = inputValue + (inputValue.trim() ? ' ' : '');
      recognitionRef.current.start();
    }
  };

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
    p: ({ node, ...props }) => <p className="mb-2 leading-relaxed" {...props} />,
    a: ({ node, ...props }) => <a className="text-[var(--color-accent-indigo)] hover:underline" {...props} />,
    ul: ({ node, ...props }) => <ul className="list-disc pl-4 mb-2 space-y-1" {...props} />,
    ol: ({ node, ...props }) => <ol className="list-decimal pl-4 mb-2 space-y-1" {...props} />,
    li: ({ node, ...props }) => <li className="pl-1" {...props} />,
    h1: ({ node, ...props }) => <h1 className="text-xl font-semibold mt-4 mb-2" {...props} />,
    h2: ({ node, ...props }) => <h2 className="text-lg font-semibold mt-4 mb-2" {...props} />,
    h3: ({ node, ...props }) => <h3 className="text-md font-semibold mt-3 mb-2" {...props} />,
    pre: ({ node, ...props }) => <pre className="bg-[var(--color-bg-main)] p-3 rounded-lg overflow-x-auto my-3 text-[12px] font-mono border border-[var(--color-border)]" {...props} />,
    code: ({ node, inline, ...props }) =>
      inline
        ? <code className="bg-[var(--color-bg-main)] px-1.5 py-0.5 rounded text-[12px] font-mono text-[var(--color-text-secondary)] border border-[var(--color-border)]" {...props} />
        : <code {...props} />
  };

  return (
    <>
      <style>{`
        .chat-theme-override {
          --color-bg-main: #040710;
          --color-bg-surface: #0C1424;
          --color-bg-elevated: #122D59;
          --color-border: #2C6CA4;
          --color-border-highlight: #3C87D1;
          --color-accent-indigo: #EB5D22;
          --color-accent-indigo-hover: #CB4711;
          --color-text-primary: #F2F1F1;
          --color-text-secondary: #ADC0CF;
          --color-text-muted: #ADC0CF;
        }
      `}</style>
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={toggleWidget}
            className="chat-theme-override fixed bottom-6 right-6 w-14 h-14 bg-[var(--color-accent-indigo)] hover:bg-[var(--color-accent-indigo-hover)] rounded-2xl flex items-center justify-center text-[#F2F1F1] z-50 cursor-pointer border-none outline-none shadow-lg"
          >
            <MessageSquare size={24} />
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isOpen && (
          <>
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
              className="chat-theme-override fixed bottom-6 right-6 w-[1000px] h-[100vh] max-h-[900px] min-h-[500px] bg-[var(--color-bg-main)] border border-[var(--color-border)] rounded-2xl shadow-2xl flex flex-col z-50 overflow-hidden font-sans"
            >
              {/* Header */}
              <header className="flex flex-col bg-[var(--color-bg-surface)] border-b border-[var(--color-border)] p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[var(--color-accent-indigo)] flex items-center justify-center font-bold text-[#F2F1F1] text-xs tracking-wider">
                      NPN
                    </div>
                    <h3 className="font-semibold text-[#F2F1F1] text-sm m-0">Project NPN</h3>
                  </div>
                  <button onClick={toggleWidget} className="text-[var(--color-text-secondary)] hover:text-[#F2F1F1] transition-colors bg-transparent border-none cursor-pointer">
                    <X size={20} />
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <div className="relative" ref={historyDropdownRef}>
                    <button
                      onClick={() => setShowHistory(!showHistory)}
                      className="flex items-center gap-2 px-3 py-1.5 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg text-xs text-[#F2F1F1] hover:bg-[var(--color-border-highlight)] transition-colors cursor-pointer font-medium"
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
                                className={`flex items-center justify-between w-full text-left px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${c.id === currentConversationId ? 'bg-[var(--color-accent-indigo)]/10 text-[var(--color-accent-indigo)] font-medium' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)] hover:text-[#F2F1F1]'}`}
                              >
                                <span className="truncate">{c.title || 'Conversation'}</span>
                              </button>
                            ))
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  <button
                    onClick={createNewChat}
                    title="New Conversation"
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--color-accent-indigo)]/10 border border-[var(--color-accent-indigo)]/20 text-[var(--color-accent-indigo)] rounded-lg text-xs font-medium hover:bg-[var(--color-accent-indigo)]/20 transition-colors cursor-pointer"
                  >
                    <Plus size={14} />
                    <span>New Conversation</span>
                  </button>

                  <button
                    onClick={handleDelete}
                    title="Delete Chat"
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-[#F49866]/10 border border-[#CB4711]/20 text-[#CB4711] rounded-lg text-xs font-medium hover:bg-[#F49866]/20 transition-colors cursor-pointer"
                  >
                    <Trash2 size={14} />
                    <span>Delete Conversation</span>
                  </button>

                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="ml-auto bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-[var(--color-text-primary)] rounded-lg px-3 py-1.5 text-[11px] font-medium outline-none cursor-pointer focus:border-[var(--color-accent-indigo)]/50 transition-colors w-32 [&>option]:bg-[var(--color-bg-surface)] [&>option]:text-[#F2F1F1]"
                  >
                    <option value="huggingface">Hugging Face</option>
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
                      <span className="text-2xl text-[var(--color-accent-indigo)]">⚡</span>
                    </div>
                    <h4 className="text-[var(--color-text-primary)] font-semibold mb-2">How can I help you today?</h4>
                    <p className="text-[13px] text-[var(--color-text-secondary)] max-w-sm leading-relaxed">
                      Start typing a question below or attach documents to create a grounded knowledge base for this session.
                    </p>
                  </div>
                ) : (
                  messages.map((m, idx) => (
                    <div key={idx} className={`flex flex-col max-w-[85%] ${m.role === 'user' ? 'ml-auto items-end' : 'mr-auto items-start'}`}>
                      {m.role === 'user' ? (
                        <div className="text-[10px] text-[var(--color-text-muted)] mb-1.5 font-medium uppercase tracking-wider px-1">
                          You
                        </div>
                      ) : (
                        <div className="flex items-center justify-between w-full mb-1.5 px-1">
                          <div className="text-[10px] text-[var(--color-text-muted)] font-medium uppercase tracking-wider">
                            Project NPN
                          </div>
                          {window.speechSynthesis && (
                            <button
                              onClick={() => handleTTS(m.content, idx)}
                              className="text-[var(--color-text-muted)] hover:text-[var(--color-accent-indigo)] transition-colors cursor-pointer flex items-center justify-center w-5 h-5 rounded hover:bg-[var(--color-bg-elevated)]"
                              title={speakingMessageIndex === idx ? "Stop speaking" : "Read aloud"}
                            >
                              {speakingMessageIndex === idx ? <Square size={10} className="fill-current" /> : <Volume2 size={12} />}
                            </button>
                          )}
                        </div>
                      )}

                      <div className={`p-4 text-[14px] leading-relaxed ${m.role === 'user' ? 'bg-[var(--color-bg-surface)] border border-[var(--color-accent-indigo)]/30 rounded-2xl rounded-tr-sm text-[var(--color-text-primary)]' : 'bg-transparent text-[var(--color-text-primary)] w-full'}`}>
                        {m.role === 'user' ? (
                          m.content
                        ) : (
                          <div className="markdown-body text-[14px]">
                            <ReactMarkdown components={MarkdownComponents}>
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

                  {docs.length > 0 && (
                    <div className="flex flex-wrap gap-2 px-3 pt-2">
                      {docs.map((d, i) => (
                        <Tilt key={i} tiltMaxAngleX={10} tiltMaxAngleY={10} scale={1.05} transitionSpeed={2500} glareEnable={true} glareMaxOpacity={0.15}>
                          <div className="flex items-center gap-1.5 bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] border border-[var(--color-border)] px-2.5 py-1 rounded-lg text-[11px] max-w-[150px] shadow-sm group">
                            {d.status === 'processing' ? (
                              <Loader2 size={12} className="animate-spin text-[var(--color-text-muted)]" />
                            ) : (
                              <File size={12} className="text-[var(--color-text-muted)]" />
                            )}
                            <span className="truncate font-medium cursor-default" title={d.filename}>{d.filename}</span>
                            {(!isGenerating && messages.length === 0) && (
                              <button
                                type="button"
                                onClick={() => deleteDocument(d.id)}
                                className="ml-1 opacity-0 group-hover:opacity-100 text-[var(--color-text-muted)] hover:text-red-400 transition-all cursor-pointer bg-transparent border-none flex items-center justify-center p-0.5 rounded-full hover:bg-red-400/10"
                                title="Remove document"
                              >
                                <X size={12} />
                              </button>
                            )}
                          </div>
                        </Tilt>
                      ))}
                    </div>
                  )}

                  <div className="flex items-end gap-2 px-1 pb-1">
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

                    {/* STT Button */}
                    <div className="relative flex items-center">
                      <button
                        type="button"
                        onClick={toggleListen}
                        className={`p-2 rounded-xl transition-colors cursor-pointer mb-0.5 flex-shrink-0 ${isListening
                          ? 'bg-[#EB5D22]/20 text-[#EB5D22] hover:bg-[#EB5D22]/30'
                          : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]'
                          }`}
                        title={isListening ? "Stop listening" : "Voice input"}
                      >
                        {isListening ? <Square size={16} className="fill-current" /> : <Mic size={18} />}
                      </button>

                      {sttError === 'not-allowed' && (
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max bg-[#CB4711] text-[#F2F1F1] text-[10px] py-1 px-2 rounded flex items-center gap-1 shadow-lg z-50">
                          <AlertCircle size={10} />
                          Microphone access denied
                        </div>
                      )}
                    </div>

                    <textarea
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSubmit(e);
                        }
                      }}
                      placeholder={isListening ? "Listening..." : "Ask a question..."}
                      className="flex-1 bg-transparent border-none text-[14px] text-[var(--color-text-primary)] py-2.5 px-1 outline-none placeholder-[var(--color-text-muted)] resize-none min-h-[44px] max-h-[150px] scrollbar-thin scrollbar-thumb-[var(--color-border-highlight)]"
                      rows={1}
                    />

                    <button
                      type="submit"
                      disabled={!inputValue.trim()}
                      className="p-2.5 mb-0.5 bg-[var(--color-accent-indigo)] hover:bg-[var(--color-accent-indigo-hover)] text-[#F2F1F1] rounded-xl flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
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
