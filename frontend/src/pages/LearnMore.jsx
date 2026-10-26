import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
  Cpu,
  Layers,
  Database,
  Lock,
  Sparkles,
  Zap,
  Activity,
  CheckCircle2
} from 'lucide-react';

export default function LearnMore() {
  const navigate = useNavigate();

  const stages = [
    {
      num: '01',
      name: 'Instant Ingestion & Font Profiling',
      desc: 'PyMuPDF profiles font sizes across document spans to automatically deduce headings, table structures, and reading order.'
    },
    {
      num: '02',
      name: 'Table Triage & Spatial Extraction',
      desc: 'Table triage filters detect table bounding boxes in under 8ms and preserve Markdown grid structure for LLM comprehension.'
    },
    {
      num: '03',
      name: 'Dual-Text Representation',
      desc: 'Separates linearized text (optimized for embedding search & BM25 indexing) from structured context_text (optimized for LLM readability).'
    },
    {
      num: '04',
      name: 'Batch BGE Vector Embedding',
      desc: 'Encodes passages locally with BAAI/bge-small-en-v1.5 and normalizes vectors to unit L2 spheres for exact cosine multiplication.'
    },
    {
      num: '05',
      name: 'NumPy Exact Brute-Force Cosine',
      desc: 'Matrix multiplication (matrix @ query_vec.T) over float32 BLOB arrays delivers sub-10ms search latency without approximation loss.'
    },
    {
      num: '06',
      name: 'Custom BM25 + RRF Fusion',
      desc: 'Fuses dense vector results with sparse term frequency scores using Reciprocal Rank Fusion (k=60) and intent-specific weight boosts.'
    },
    {
      num: '07',
      name: 'Relevance Gate & Refusal Guarantee',
      desc: 'Strict confidence floor filters out queries lacking verifiable document evidence, preventing hallucinations before generation.'
    }
  ];

  return (
    <div className="min-h-screen w-full bg-[#090909] text-[#F5F1EC] font-sans">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-[#090909]/90 backdrop-blur-md border-b border-[#2B2B2B]">
        <div className="max-w-7xl mx-auto px-6 h-18 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-10 h-10 rounded-xl bg-[#F15A24] flex items-center justify-center font-bold text-white shadow-[0_2px_12px_rgba(241,90,36,0.35)]">
              <FileText size={22} className="text-[#F5F1EC]" />
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-bold tracking-tight text-[#F5F1EC] font-heading">
                Intelli<span className="text-[#F15A24]">Doc</span>
              </span>
              <span className="text-[10px] uppercase tracking-widest text-[#A3A3A3] font-semibold -mt-1">
                Architecture & Standards
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-1.5 text-xs text-[#A3A3A3] hover:text-[#F5F1EC] transition-colors cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back to Home</span>
            </button>

            <button
              onClick={() => navigate('/workspace')}
              className="flex items-center gap-2 px-4 py-2 bg-[#F15A24] hover:bg-[#FF6A35] text-[#F5F1EC] text-xs font-semibold rounded-xl transition-all cursor-pointer shadow-[0_2px_8px_rgba(241,90,36,0.25)]"
            >
              <span>Open Workspace</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-14 lg:py-20">
        {/* Intro */}
        <div className="max-w-3xl mb-16">
          <span className="text-xs font-bold text-[#F15A24] uppercase tracking-widest block mb-2">
            Engineering Blueprint
          </span>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-[#F5F1EC] font-heading mb-4 leading-tight">
            Deterministic Document Intelligence
          </h1>
          <p className="text-sm text-[#A3A3A3] leading-relaxed">
            IntelliDoc was built from the ground up without heavy LLM orchestration frameworks like LangChain or LlamaIndex. Every stage is measurable, deterministic, and executed locally with raw NumPy, SQLite WAL, and exact citation tracking.
          </p>
        </div>

        {/* Benchmarks Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
          {[
            { metric: '<10ms', label: 'Vector Search Latency', note: 'NumPy exact matrix multiplication' },
            { metric: '~14.5s', label: 'PDF Ingestion (94 pgs)', note: '7-stage profiling & table triage' },
            { metric: '1.5 KB', label: 'Vector BLOB Storage', note: 'Raw float32 binary vs 22 KB JSON' },
            { metric: '100%', label: 'Conversation Isolation', note: 'Strict zero cross-document bleed' }
          ].map((b, idx) => (
            <div key={idx} className="p-5 bg-[#171717] border border-[#2B2B2B] rounded-2xl flex flex-col gap-1">
              <span className="text-3xl font-extrabold text-[#F15A24] font-heading">{b.metric}</span>
              <span className="text-xs font-bold text-[#F5F1EC] mt-1">{b.label}</span>
              <span className="text-[11px] text-[#A3A3A3]">{b.note}</span>
            </div>
          ))}
        </div>

        {/* 7-Stage Pipeline Breakdown */}
        <section className="mb-20">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-[#F5F1EC] font-heading mb-2">
              7-Stage Ingestion & Retrieval Pipeline
            </h2>
            <p className="text-xs text-[#A3A3A3]">
              How IntelliDoc converts raw unstructured documents into verifiable mathematical knowledge.
            </p>
          </div>

          <div className="flex flex-col gap-4">
            {stages.map((st) => (
              <div
                key={st.num}
                className="p-5 bg-[#171717] border border-[#2B2B2B] hover:border-[#3D3D3D] rounded-2xl flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-6 transition-all"
              >
                <div className="w-10 h-10 rounded-xl bg-[rgba(241,90,36,0.12)] border border-[rgba(241,90,36,0.25)] flex items-center justify-center font-bold text-[#F15A24] text-sm font-heading flex-shrink-0">
                  {st.num}
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-bold text-[#F5F1EC] font-heading mb-1">{st.name}</h3>
                  <p className="text-xs text-[#A3A3A3] leading-relaxed m-0">{st.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Security & Isolation */}
        <section className="p-8 lg:p-10 bg-[#171717] border border-[#2B2B2B] rounded-3xl mb-16">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-[rgba(114,180,124,0.15)] text-[#72B47C] flex items-center justify-center">
              <ShieldCheck size={22} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[#F5F1EC] font-heading m-0">Zero Cross-Conversation Bleed Guarantee</h2>
              <span className="text-xs text-[#A3A3A3]">Mathematical & programmatic isolation</span>
            </div>
          </div>

          <p className="text-xs text-[#A3A3A3] leading-relaxed mb-6">
            In standard cloud RAG systems, user documents often share global indices or vector namespaces. IntelliDoc assigns an immutable <code className="text-[#F15A24] bg-[#202020] px-1.5 py-0.5 rounded text-[11px]">conversation_id</code> to every document, chunk, and vector BLOB. All search operations (dense cosine, BM25 sparse, and RRF) are partitioned at query-time.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-4 bg-[#202020] rounded-xl border border-[#2B2B2B]">
              <span className="font-bold text-[#F5F1EC] block mb-1">SQLite WAL DB</span>
              <span className="text-[#A3A3A3]">High concurrency without locking overhead</span>
            </div>
            <div className="p-4 bg-[#202020] rounded-xl border border-[#2B2B2B]">
              <span className="font-bold text-[#F5F1EC] block mb-1">Raw BLOB Vectors</span>
              <span className="text-[#A3A3A3]">Zero JSON parsing penalty during search</span>
            </div>
            <div className="p-4 bg-[#202020] rounded-xl border border-[#2B2B2B]">
              <span className="font-bold text-[#F5F1EC] block mb-1">Strict Refusal</span>
              <span className="text-[#A3A3A3]">Unevidenced queries rejected at the gate</span>
            </div>
          </div>
        </section>

        {/* CTA */}
        <div className="text-center">
          <button
            onClick={() => navigate('/workspace')}
            className="px-8 py-3.5 bg-[#F15A24] hover:bg-[#FF6A35] text-[#F5F1EC] font-bold text-sm rounded-xl shadow-[0_4px_16px_rgba(241,90,36,0.35)] transition-all cursor-pointer hover:-translate-y-0.5 active:translate-y-0 inline-flex items-center gap-2"
          >
            <span>Launch IntelliDoc Workspace</span>
            <ArrowRight size={18} />
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-8 bg-[#090909] border-t border-[#2B2B2B] text-xs text-[#737373] text-center">
        IntelliDoc 2.0 • Deterministic Document Intelligence
      </footer>
    </div>
  );
}
