import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../../context/ChatContext';
import {
  Send,
  Paperclip,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Copy,
  Check,
  Trash2,
  Menu,
  Files,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Sparkles,
  FileText
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import DOMPurify from 'dompurify';

const cleanDocName = (name) => {
  if (!name) return 'Document';
  return name.replace(/^[0-9a-fA-F-]{36}_/, '');
};

const formatMessageContent = (content) => {
  if (!content) return '';
  let cleaned = content.replace(/^Based on the ingested document analysis:\s*/i, '');
  cleaned = cleaned.replace(/\[SOURCE\s*\[?S\d+\]?[^\]]*\]:?\s*Document:\s*[^\s|]+\s*\|\s*/gi, '');
  return cleaned;
};

export default function ChatWorkspace({ onToggleSidebar, onToggleKnowledgeBase }) {
  const {
    activeConversation,
    sendMessage,
    deleteConversation,
    isGenerating,
    uploadFiles,
    openCitation,
    selectedDocIds,
    provider
  } = useChat();

  const [inputValue, setInputValue] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const [speakingIdx, setSpeakingIdx] = useState(null);

  // STT Voice State
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);
  const baseInputRef = useRef('');

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const messages = activeConversation?.messages || [];
  const docs = activeConversation?.documents || [];
  const readyDocs = docs.filter(d => d.status === 'ready');

  // STT Initialization
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => setIsListening(true);
      recognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }
        setInputValue(baseInputRef.current + transcript);
      };
      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);
      recognitionRef.current = recognition;
    }
  }, []);

  // Cleanup TTS/STT on unmount or conversation change
  useEffect(() => {
    window.speechSynthesis?.cancel();
    setSpeakingIdx(null);
    if (recognitionRef.current) recognitionRef.current.abort();
  }, [activeConversation?.id]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isGenerating]);

  // Auto-resize textarea
  const handleTextareaChange = (e) => {
    setInputValue(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || isGenerating) return;

    const messageText = inputValue;
    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    sendMessage(messageText);
  };

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser.');
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      baseInputRef.current = inputValue + (inputValue.trim() ? ' ' : '');
      recognitionRef.current.start();
    }
  };

  const handleTTS = (text, idx) => {
    window.speechSynthesis.cancel();
    if (speakingIdx === idx) {
      setSpeakingIdx(null);
      return;
    }

    const cleanText = text
      .replace(/\[S\d+\]/g, '')
      .replace(/[#*`_~]/g, '')
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.onend = () => setSpeakingIdx(null);
    utterance.onerror = () => setSpeakingIdx(null);

    setSpeakingIdx(idx);
    window.speechSynthesis.speak(utterance);
  };

  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleFileAttach = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFiles(e.target.files);
    }
    e.target.value = null;
  };

  return (
    <main className="flex-1 flex flex-col min-w-0 bg-[#090909] relative h-full overflow-hidden">
      {/* Top Workspace Header */}
      <header className="h-16 min-h-[4rem] border-b border-[#2B2B2B] bg-[#101010] px-4 lg:px-6 flex items-center justify-between z-10">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-2 text-[#A3A3A3] hover:text-[#F5F1EC] hover:bg-[#202020] rounded-lg cursor-pointer"
            aria-label="Open conversation sidebar"
          >
            <Menu size={18} />
          </button>

          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-[#F5F1EC] truncate font-heading m-0">
                {activeConversation?.title || 'Active Workspace'}
              </h2>
              <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 bg-[rgba(114,180,124,0.12)] border border-[rgba(114,180,124,0.3)] text-[#72B47C] text-[10px] font-semibold rounded-md">
                Isolated
              </span>
            </div>
            <span className="text-[11px] text-[#A3A3A3] truncate">
              {readyDocs.length} {readyDocs.length === 1 ? 'ready document' : 'ready documents'} • Model: {provider}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Mobile Document Drawer Trigger */}
          <button
            onClick={onToggleKnowledgeBase}
            className="lg:hidden flex items-center gap-1.5 px-3 py-1.5 bg-[#171717] border border-[#2B2B2B] text-[#F5F1EC] rounded-lg text-xs font-medium hover:bg-[#202020] cursor-pointer"
            title="Documents"
          >
            <Files size={14} className="text-[#F15A24]" />
            <span>Files ({docs.length})</span>
          </button>

          <button
            onClick={() => {
              if (activeConversation && window.confirm('Delete this conversation?')) {
                deleteConversation(activeConversation.id);
              }
            }}
            className="p-2 text-[#737373] hover:text-[#E57373] hover:bg-[#202020] rounded-lg transition-colors cursor-pointer"
            title="Delete conversation"
            aria-label="Delete conversation"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </header>

      {/* Main Conversation Stream */}
      <div className="flex-1 overflow-y-auto p-4 lg:p-6 scrollbar-thin">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto mt-12 bg-[#171717] border border-[#2B2B2B] rounded-2xl p-6 lg:p-8 text-center shadow-xl">
            <div className="w-12 h-12 rounded-2xl bg-[rgba(241,90,36,0.15)] border border-[rgba(241,90,36,0.3)] flex items-center justify-center mx-auto mb-4 text-[#F15A24]">
              <Sparkles size={24} />
            </div>

            <h3 className="text-xl font-bold text-[#F5F1EC] mb-2 font-heading">
              Grounded Document Intelligence
            </h3>
            <p className="text-xs text-[#A3A3A3] leading-relaxed mb-6 max-w-lg mx-auto">
              Ask natural-language questions to extract verified evidence from your documents. Every answer is grounded in exact source citations with zero cross-conversation bleed.
            </p>

            {docs.length === 0 ? (
              <div className="p-4 bg-[#202020] border border-dashed border-[#2B2B2B] rounded-xl text-xs text-[#A3A3A3] mb-4">
                Attach a PDF, financial report, or technical document on the right to start querying.
              </div>
            ) : (
              <div className="flex flex-col gap-2 text-left">
                <span className="text-[11px] font-bold text-[#737373] uppercase tracking-wider mb-1">
                  Suggested Questions
                </span>
                <button
                  onClick={() => setInputValue('Summarize the primary purpose, key findings, and conclusions of the attached documents.')}
                  className="p-3 bg-[#101010] hover:bg-[#202020] border border-[#2B2B2B] hover:border-[#F15A24] rounded-xl text-xs text-[#F5F1EC] transition-all cursor-pointer text-left"
                >
                  📑 Summarize primary findings, methodology, and conclusions
                </button>
                <button
                  onClick={() => setInputValue('What quantitative tables, revenue metrics, or performance figures are reported?')}
                  className="p-3 bg-[#101010] hover:bg-[#202020] border border-[#2B2B2B] hover:border-[#F15A24] rounded-xl text-xs text-[#F5F1EC] transition-all cursor-pointer text-left"
                >
                  📊 Extract quantitative metrics, tables, and financial performance
                </button>
                <button
                  onClick={() => setInputValue('List the critical risks, compliance obligations, or open questions stated in the material.')}
                  className="p-3 bg-[#101010] hover:bg-[#202020] border border-[#2B2B2B] hover:border-[#F15A24] rounded-xl text-xs text-[#F5F1EC] transition-all cursor-pointer text-left"
                >
                  ⚠️ Highlight stated risks, obligations, and critical factors
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="max-w-3xl mx-auto flex flex-col gap-5 pb-6">
            {messages.map((m, idx) => {
              const isUser = m.role === 'user';
              const citations = m.citations || [];
              const verification = m.verification;

              return (
                <div
                  key={m.id || idx}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`rounded-2xl p-4 lg:p-5 max-w-[90%] border shadow-md ${
                      isUser
                        ? 'bg-[#202020] border-[#2B2B2B] text-[#F5F1EC] rounded-tr-xs'
                        : 'bg-[#171717] border-[#2B2B2B] text-[#F5F1EC] rounded-tl-xs'
                    }`}
                  >
                    {/* Role Header */}
                    <div className="flex items-center justify-between gap-4 mb-2 text-[11px] text-[#A3A3A3] pb-1.5 border-b border-[#242424]">
                      <span className="font-semibold uppercase tracking-wider text-[10px] text-[#A3A3A3]">
                        {isUser ? 'You' : 'IntelliDoc'}
                      </span>

                      {!isUser && (
                        <div className="flex items-center gap-2">
                          {m.latency_ms && (
                            <span className="flex items-center gap-1 text-[10px] text-[#737373]">
                              <Clock size={11} />
                              {Math.round(m.latency_ms)}ms
                            </span>
                          )}

                          <button
                            onClick={() => handleCopy(m.content, m.id || idx)}
                            className="p-1 hover:text-[#F5F1EC] rounded cursor-pointer"
                            title="Copy response"
                            aria-label="Copy response"
                          >
                            {copiedId === (m.id || idx) ? (
                              <Check size={12} className="text-[#72B47C]" />
                            ) : (
                              <Copy size={12} />
                            )}
                          </button>

                          <button
                            onClick={() => handleTTS(m.content, idx)}
                            className="p-1 hover:text-[#F15A24] rounded cursor-pointer"
                            title="Read answer aloud"
                            aria-label="Read answer aloud"
                          >
                            {speakingIdx === idx ? (
                              <VolumeX size={13} className="text-[#F15A24]" />
                            ) : (
                              <Volume2 size={13} />
                            )}
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Markdown Message Content */}
                    <div className="prose-intellidoc text-sm leading-relaxed whitespace-pre-wrap break-words">
                      <ReactMarkdown
                        components={{
                          a: ({ node, ...props }) => (
                            <a
                              className="text-[#F15A24] hover:underline"
                              target="_blank"
                              rel="noreferrer"
                              {...props}
                            />
                          ),
                          code: ({ node, inline, ...props }) =>
                            inline ? (
                              <code
                                className="bg-[#202020] text-[#F5F1EC] px-1.5 py-0.5 rounded text-xs border border-[#2B2B2B]"
                                {...props}
                              />
                            ) : (
                              <pre className="bg-[#101010] p-3 rounded-lg overflow-x-auto text-xs my-2 border border-[#2B2B2B]">
                                <code {...props} />
                              </pre>
                            )
                        }}
                      >
                        {formatMessageContent(m.content)}
                      </ReactMarkdown>
                    </div>

                    {/* Grounded Citation Badges */}
                    {citations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-[#242424] flex flex-col gap-2">
                        <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-wider">
                          Grounding Sources ({citations.length})
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {citations.map((c, cIdx) => (
                            <button
                              key={c.chunk_id || cIdx}
                              onClick={() => openCitation(c, citations)}
                              className="flex items-center gap-1.5 px-2.5 py-1 bg-[#202020] hover:bg-[#2B2B2B] border border-[#2B2B2B] hover:border-[#F15A24] rounded-lg text-xs text-[#F5F1EC] cursor-pointer transition-all"
                              title={`View evidence excerpt from ${cleanDocName(c.document_name || c.filename)}`}
                            >
                              <span className="px-1 py-0.2 bg-[rgba(241,90,36,0.15)] text-[#F15A24] rounded font-bold text-[10px]">
                                S{cIdx + 1}
                              </span>
                              <span className="truncate max-w-[160px] text-[11px] font-medium">
                                {cleanDocName(c.document_name || c.filename)}
                              </span>
                              <span className="text-[10px] text-[#A3A3A3]">
                                p.{c.page_number}
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Fact-Checking Verification Badge */}
                    {verification && (
                      <div className="mt-3 pt-2 border-t border-[#242424] flex items-center gap-2 text-xs">
                        {verification.status === 'supported' && (
                          <span className="flex items-center gap-1 text-[#72B47C] font-medium">
                            <ShieldCheck size={13} />
                            Verified Evidence-Grounded
                          </span>
                        )}
                        {verification.status === 'partial' && (
                          <span className="flex items-center gap-1 text-[#E5B567] font-medium">
                            <AlertTriangle size={13} />
                            Partially Supported by Document Context
                          </span>
                        )}
                        {verification.status === 'unsupported' && (
                          <span className="flex items-center gap-1 text-[#E57373] font-medium">
                            <AlertTriangle size={13} />
                            General Knowledge Response (No Document Evidence)
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* In-Flight Generation Indicator */}
            {isGenerating && (
              <div className="flex items-center gap-3 p-3 bg-[#171717] border border-[#2B2B2B] rounded-2xl w-fit">
                <div className="w-2 h-2 rounded-full bg-[#F15A24] animate-ping" />
                <span className="text-xs text-[#A3A3A3] font-medium">
                  Retrieving passages & synthesizing evidence...
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Persistent Bottom Message Composer */}
      <div className="p-3 lg:p-4 bg-[#101010] border-t border-[#2B2B2B]">
        <div className="max-w-3xl mx-auto flex flex-col gap-2">
          {readyDocs.length === 0 && docs.length > 0 && (
            <div className="text-[11px] text-[#E5B567] flex items-center gap-1.5 px-2">
              <Clock size={12} className="animate-spin text-[#F15A24]" />
              <span>Documents are processing. You can send questions once indexing finishes.</span>
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="flex items-end gap-2 bg-[#171717] border border-[#2B2B2B] focus-within:border-[#F15A24] rounded-2xl p-2 transition-all shadow-lg"
          >
            {/* Attachment Button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-2 text-[#A3A3A3] hover:text-[#F5F1EC] hover:bg-[#202020] rounded-xl transition-colors cursor-pointer"
              title="Upload document"
              aria-label="Upload document"
            >
              <Paperclip size={18} />
            </button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileAttach}
              accept=".pdf,.txt,.csv,.tsv,.json,.md,.markdown"
              multiple
              className="hidden"
            />

            {/* STT Microphone Button */}
            <button
              type="button"
              onClick={toggleVoiceInput}
              className={`p-2 rounded-xl transition-colors cursor-pointer ${
                isListening
                  ? 'bg-[rgba(241,90,36,0.2)] text-[#F15A24] animate-pulse'
                  : 'text-[#A3A3A3] hover:text-[#F5F1EC] hover:bg-[#202020]'
              }`}
              title={isListening ? 'Stop recording voice' : 'Voice question input'}
              aria-label={isListening ? 'Stop recording voice' : 'Voice question input'}
            >
              {isListening ? <MicOff size={18} /> : <Mic size={18} />}
            </button>

            {/* Multiline Textarea */}
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question grounded in your documents... (Shift+Enter for new line)"
              rows={1}
              className="flex-1 bg-transparent border-none text-sm text-[#F5F1EC] placeholder-[#737373] outline-none resize-none py-2 px-1 max-h-40 min-h-[2.5rem] leading-relaxed"
            />

            {/* Send Button */}
            <button
              type="submit"
              disabled={!inputValue.trim() || isGenerating}
              className="p-2.5 bg-[#F15A24] hover:bg-[#FF6A35] disabled:opacity-40 disabled:cursor-not-allowed text-[#F5F1EC] rounded-xl transition-all cursor-pointer shadow-[0_2px_8px_rgba(241,90,36,0.25)]"
              aria-label="Send question"
            >
              <Send size={16} />
            </button>
          </form>

          <div className="flex items-center justify-between text-[11px] text-[#737373] px-2">
            <span>Enter to send • Shift+Enter for newline</span>
            <span>IntelliDoc 2.0 • Grounded RAG</span>
          </div>
        </div>
      </div>
    </main>
  );
}
