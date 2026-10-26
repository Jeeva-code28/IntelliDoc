import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  ArrowRight,
  ShieldCheck,
  Search,
  Layers,
  Lock,
  Cpu,
  ChevronRight,
  CheckCircle2,
  Table,
  FileSearch,
  Sparkles
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen w-full bg-[#090909] text-[#F5F1EC] flex flex-col font-sans selection:bg-[#F15A24] selection:text-white">
      {/* Navigation Header */}
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
                Document Intelligence
              </span>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-[#A3A3A3]">
            <a href="#features" className="hover:text-[#F5F1EC] transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-[#F5F1EC] transition-colors">How It Works</a>
            <button
              onClick={() => navigate('/learn-more')}
              className="hover:text-[#F5F1EC] transition-colors cursor-pointer bg-transparent border-none text-sm font-medium text-[#A3A3A3]"
            >
              Architecture
            </button>
          </nav>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/workspace')}
              className="flex items-center gap-2 px-5 py-2.5 bg-[#F15A24] hover:bg-[#FF6A35] text-[#F5F1EC] text-sm font-semibold rounded-xl shadow-[0_2px_10px_rgba(241,90,36,0.3)] transition-all cursor-pointer hover:-translate-y-0.5 active:translate-y-0"
            >
              <span>Open IntelliDoc</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-20 pb-16 lg:pt-28 lg:pb-24 overflow-hidden border-b border-[#2B2B2B]">
        {/* Subtle Charcoal & Orange Radial Ambient Glows (NO BLUE) */}
        <div className="pointer-events-none absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-[radial-gradient(ellipse_at_center,_rgba(241,90,36,0.08)_0%,_transparent_70%)] blur-3xl -z-10" />

        <div className="max-w-5xl mx-auto px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#171717] border border-[#2B2B2B] text-xs font-medium text-[#A3A3A3] mb-8"
          >
            <span className="w-2 h-2 rounded-full bg-[#F15A24] animate-pulse" />
            <span>IntelliDoc 2.0 • Local-First Grounded RAG</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-[#F5F1EC] font-heading mb-6 leading-[1.08]"
          >
            Your documents. <br />
            Your answers. <span className="text-[#F15A24]">Your evidence.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-base sm:text-lg text-[#A3A3A3] max-w-2xl mx-auto mb-10 leading-relaxed font-normal"
          >
            Upload your documents, ask questions in natural language, and explore answers grounded in your source material with verified line-level citations.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
          >
            <button
              onClick={() => navigate('/workspace')}
              className="w-full sm:w-auto px-8 py-3.5 bg-[#F15A24] hover:bg-[#FF6A35] text-[#F5F1EC] font-bold text-sm rounded-xl shadow-[0_4px_16px_rgba(241,90,36,0.35)] transition-all cursor-pointer hover:-translate-y-0.5 active:translate-y-0 flex items-center justify-center gap-2"
            >
              <span>Open IntelliDoc</span>
              <ArrowRight size={18} />
            </button>

            <button
              onClick={() => navigate('/learn-more')}
              className="w-full sm:w-auto px-8 py-3.5 bg-[#171717] hover:bg-[#202020] text-[#F5F1EC] font-semibold text-sm rounded-xl border border-[#2B2B2B] hover:border-[#3D3D3D] transition-all cursor-pointer flex items-center justify-center gap-2"
            >
              <span>How It Works</span>
              <ChevronRight size={18} className="text-[#A3A3A3]" />
            </button>
          </motion.div>

          {/* Authentic Product Preview Frame */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.4 }}
            className="rounded-2xl border border-[#2B2B2B] bg-[#101010] p-2 shadow-2xl shadow-black/80 max-w-4xl mx-auto overflow-hidden text-left"
          >
            {/* Window Controls */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#2B2B2B] bg-[#171717] rounded-t-xl">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#2B2B2B]" />
                <div className="w-3 h-3 rounded-full bg-[#2B2B2B]" />
                <div className="w-3 h-3 rounded-full bg-[#2B2B2B]" />
                <span className="text-xs font-mono text-[#737373] ml-2">IntelliDoc — Workspace Demo</span>
              </div>
              <span className="text-[11px] text-[#72B47C] font-semibold flex items-center gap-1">
                <CheckCircle2 size={12} /> Local Engine Active
              </span>
            </div>

            {/* Simulated 3-Column Preview */}
            <div className="grid grid-cols-1 md:grid-cols-4 bg-[#090909] min-h-[320px]">
              {/* Sidebar Preview */}
              <div className="hidden md:flex flex-col p-4 border-r border-[#2B2B2B] bg-[#101010] gap-2">
                <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider mb-1">Conversations</span>
                <div className="p-2.5 bg-[#171717] border border-[rgba(241,90,36,0.3)] rounded-lg text-xs text-[#F5F1EC] font-medium">
                  Annual Report 2025
                </div>
                <div className="p-2.5 bg-transparent border border-transparent rounded-lg text-xs text-[#737373]">
                  Q3 Financial Summary
                </div>
                <div className="p-2.5 bg-transparent border border-transparent rounded-lg text-xs text-[#737373]">
                  Technical Specs PDF
                </div>
              </div>

              {/* Chat Area Preview */}
              <div className="col-span-2 p-5 flex flex-col justify-between border-r border-[#2B2B2B] gap-4">
                <div className="flex flex-col gap-3">
                  <div className="self-end bg-[#202020] border border-[#2B2B2B] text-[#F5F1EC] text-xs p-3 rounded-xl rounded-tr-xs max-w-[85%]">
                    What was the total net revenue and profit growth reported in FY2025?
                  </div>
                  <div className="self-start bg-[#171717] border border-[#2B2B2B] text-[#F5F1EC] text-xs p-3.5 rounded-xl rounded-tl-xs max-w-[95%] space-y-2">
                    <p className="leading-relaxed">
                      Total net revenue for FY2025 grew by <strong>18.4% YoY</strong>, reaching <strong>$1.42 billion</strong> compared to $1.20 billion in FY2024. Operating margin expanded by 240 basis points.
                    </p>
                    <div className="flex items-center gap-2 pt-1 border-t border-[#242424]">
                      <span className="px-2 py-0.5 bg-[rgba(241,90,36,0.15)] text-[#F15A24] font-bold text-[10px] rounded border border-[rgba(241,90,36,0.3)]">
                        S1 p.14 Financial Tables
                      </span>
                      <span className="px-2 py-0.5 bg-[#202020] text-[#A3A3A3] text-[10px] rounded border border-[#2B2B2B]">
                        S2 p.22 Executive Summary
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-2.5 bg-[#171717] border border-[#2B2B2B] rounded-xl flex items-center justify-between text-xs text-[#737373]">
                  <span>Ask a grounded question...</span>
                  <div className="w-6 h-6 rounded-lg bg-[#F15A24] flex items-center justify-center text-white">
                    <ArrowRight size={12} />
                  </div>
                </div>
              </div>

              {/* Document Library Preview */}
              <div className="hidden md:flex flex-col p-4 bg-[#101010] gap-3">
                <span className="text-[10px] font-bold text-[#737373] uppercase tracking-wider">Document Library</span>
                <div className="p-2.5 bg-[#171717] border border-[#2B2B2B] rounded-lg flex items-center gap-2">
                  <FileText size={16} className="text-[#F15A24]" />
                  <div className="min-w-0">
                    <span className="text-xs font-semibold text-[#F5F1EC] truncate block">annual-report-2025.pdf</span>
                    <span className="text-[10px] text-[#72B47C] font-medium">Ready • 94 pages</span>
                  </div>
                </div>
                <div className="p-2.5 bg-[#171717] border border-[#2B2B2B] rounded-lg flex items-center gap-2">
                  <Table size={16} className="text-[#E5B567]" />
                  <div className="min-w-0">
                    <span className="text-xs font-semibold text-[#F5F1EC] truncate block">balance-sheet.csv</span>
                    <span className="text-[10px] text-[#72B47C] font-medium">Ready • 48 rows</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-[#090909] border-b border-[#2B2B2B]">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-[#F15A24] uppercase tracking-widest mb-3">
              Core Capabilities
            </h2>
            <h3 className="text-3xl sm:text-4xl font-extrabold text-[#F5F1EC] font-heading mb-4">
              Engineered for Precision & Proof
            </h3>
            <p className="text-sm text-[#A3A3A3] leading-relaxed">
              IntelliDoc bypasses generic probabilistic chat hallucinations with exact brute-force cosine search, BM25 keyword matching, and line-level citation proof.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="p-6 rounded-2xl bg-[#171717] border border-[#2B2B2B] hover:border-[#3D3D3D] transition-all flex flex-col gap-4">
              <div className="w-10 h-10 rounded-xl bg-[rgba(241,90,36,0.12)] border border-[rgba(241,90,36,0.25)] flex items-center justify-center text-[#F15A24]">
                <FileSearch size={20} />
              </div>
              <h4 className="text-lg font-bold text-[#F5F1EC] font-heading m-0">
                Grounded Citations & Proof
              </h4>
              <p className="text-xs text-[#A3A3A3] leading-relaxed">
                Every answer references verified source passages with exact page numbers, table titles, and document snippets. Inspect the original excerpt with one click.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-6 rounded-2xl bg-[#171717] border border-[#2B2B2B] hover:border-[#3D3D3D] transition-all flex flex-col gap-4">
              <div className="w-10 h-10 rounded-xl bg-[rgba(241,90,36,0.12)] border border-[rgba(241,90,36,0.25)] flex items-center justify-center text-[#F15A24]">
                <Layers size={20} />
              </div>
              <h4 className="text-lg font-bold text-[#F5F1EC] font-heading m-0">
                Hybrid Cosine + BM25 Fusion
              </h4>
              <p className="text-xs text-[#A3A3A3] leading-relaxed">
                Combines NumPy float32 brute-force dense vector search with sparse BM25 indexing via Reciprocal Rank Fusion (k=60), capturing both exact figures and semantic intent.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-6 rounded-2xl bg-[#171717] border border-[#2B2B2B] hover:border-[#3D3D3D] transition-all flex flex-col gap-4">
              <div className="w-10 h-10 rounded-xl bg-[rgba(241,90,36,0.12)] border border-[rgba(241,90,36,0.25)] flex items-center justify-center text-[#F15A24]">
                <Lock size={20} />
              </div>
              <h4 className="text-lg font-bold text-[#F5F1EC] font-heading m-0">
                Zero-Spillover Partitioning
              </h4>
              <p className="text-xs text-[#A3A3A3] leading-relaxed">
                Each conversation operates in a strictly isolated memory partition. Questions in Chat A can never leak or retrieve documents indexed in Chat B.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 bg-[#101010] border-b border-[#2B2B2B]">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-xs font-bold text-[#F15A24] uppercase tracking-widest mb-3">
              Workflow
            </h2>
            <h3 className="text-3xl sm:text-4xl font-extrabold text-[#F5F1EC] font-heading mb-4">
              From Document to Verified Insight
            </h3>
            <p className="text-sm text-[#A3A3A3]">
              Four seamless steps to extract answers with cryptographic-level certainty.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                step: '01',
                title: 'Upload Documents',
                desc: 'Drag and drop PDFs, tabular CSVs, or text files directly into your active conversation.'
              },
              {
                step: '02',
                title: 'Process & Embed',
                desc: 'PyMuPDF font profiling, triage filters, and BAAI/bge-small-en-v1.5 embeddings index your file.'
              },
              {
                step: '03',
                title: 'Ask Questions',
                desc: 'Inquire in plain language or use voice dictation. Dual-threshold gates filter unevidenced queries.'
              },
              {
                step: '04',
                title: 'Inspect Evidence',
                desc: 'Review grounded answers and open the source drawer to inspect original page coordinates.'
              }
            ].map((item, idx) => (
              <div key={idx} className="p-6 bg-[#171717] border border-[#2B2B2B] rounded-2xl flex flex-col gap-3">
                <span className="text-2xl font-black text-[#F15A24] font-heading">{item.step}</span>
                <h4 className="text-base font-bold text-[#F5F1EC] font-heading m-0">{item.title}</h4>
                <p className="text-xs text-[#A3A3A3] leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Primary Conversion CTA Banner */}
      <section className="py-20 bg-[#090909]">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <div className="p-10 lg:p-14 rounded-3xl bg-[#171717] border border-[#2B2B2B] flex flex-col items-center gap-6 relative overflow-hidden shadow-2xl">
            <div className="w-14 h-14 rounded-2xl bg-[#F15A24] flex items-center justify-center text-white shadow-[0_4px_20px_rgba(241,90,36,0.4)]">
              <Sparkles size={28} />
            </div>

            <h3 className="text-3xl sm:text-4xl font-extrabold text-[#F5F1EC] font-heading max-w-lg leading-tight">
              Ready to interrogate your documents with confidence?
            </h3>

            <p className="text-sm text-[#A3A3A3] max-w-md">
              Start a new session in IntelliDoc. Upload your files and experience deterministic, evidence-grounded answers.
            </p>

            <button
              onClick={() => navigate('/workspace')}
              className="px-8 py-3.5 bg-[#F15A24] hover:bg-[#FF6A35] text-[#F5F1EC] font-bold text-sm rounded-xl shadow-[0_4px_16px_rgba(241,90,36,0.35)] transition-all cursor-pointer hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2"
            >
              <span>Open IntelliDoc Workspace</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto py-8 bg-[#090909] border-t border-[#2B2B2B] text-xs text-[#737373]">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-[#F15A24] flex items-center justify-center text-white font-bold text-[10px]">
              ID
            </div>
            <span className="font-semibold text-[#A3A3A3]">IntelliDoc 2.0</span>
            <span>• High-Performance Document Intelligence</span>
          </div>

          <div className="flex items-center gap-6">
            <button
              onClick={() => navigate('/learn-more')}
              className="hover:text-[#F5F1EC] transition-colors cursor-pointer bg-transparent border-none text-xs text-[#737373]"
            >
              Architecture & Benchmarks
            </button>
            <button
              onClick={() => navigate('/workspace')}
              className="text-[#F15A24] hover:underline cursor-pointer bg-transparent border-none text-xs font-semibold"
            >
              Launch App →
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
