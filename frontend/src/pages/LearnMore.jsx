import React, { useEffect, useRef, useState } from "react";
import ChatWindow from "../components/Chat/ChatWindow";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

function useFadeOnScroll() {
  const ref = useRef(null);
  const [style, setStyle] = useState({
    opacity: 0,
    transform: "translateY(32px)",
    transition: "opacity 0.7s ease, transform 0.7s ease",
  });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setStyle({ opacity: 1, transform: "translateY(0px)", transition: "opacity 0.7s ease, transform 0.7s ease" });
        } else {
          setStyle({ opacity: 0, transform: "translateY(32px)", transition: "opacity 0.5s ease, transform 0.5s ease" });
        }
      },
      { threshold: 0.15 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, style };
}

const palette = {
  ink: "#040710",
  navy: "#0C1424",
  blueDark: "#122D59",
  blue: "#2C6CA4",
  blueBright: "#3C87D1",
  orange: "#EB5D22",
  orangeDark: "#CB4711",
  peach: "#F49866",
  white: "#F2F1F1",
  muted: "#ADC0CF",
};

export default function LearnMore() {
  const features = [
    ["01", "Upload Documents", "Add your documents and prepare them for intelligent search."],
    ["02", "AI Understanding", "DocuChat processes the content so you can interact with it naturally."],
    ["03", "Ask Questions", "Ask questions and get relevant answers without manually searching every page."],
  ];

  const s1 = useFadeOnScroll();
  const s2 = useFadeOnScroll();
  const s3 = useFadeOnScroll();
  const s4 = useFadeOnScroll();
  const navigate = useNavigate();
  const [chatKey, setChatKey] = useState(0);

  const fullText = "DocuChat is an AI-powered document chatbot designed to make information easier to access. Instead of searching through long documents manually, ask questions in natural language and interact with the content directly.";
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    let i = 0;
    const intervalId = setInterval(() => {
      setDisplayedText(fullText.slice(0, i));
      i++;
      if (i > fullText.length) {
        clearInterval(intervalId);
      }
    }, 15);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="min-h-screen overflow-x-hidden relative" style={{ backgroundColor: palette.ink, color: palette.white }}>
      <div className="pointer-events-none absolute -left-40 top-20 h-96 w-96 rounded-full opacity-20 blur-3xl" style={{ backgroundColor: palette.blue }} />
      <div className="pointer-events-none absolute right-0 top-80 h-96 w-96 rounded-full opacity-15 blur-3xl" style={{ backgroundColor: palette.orange }} />

      <header className="relative z-20">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-10">
          <a href="#" className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-xl"
              style={{ backgroundColor: palette.orange }}
            >
              <svg
                viewBox="0 0 24 24"
                className="h-6 w-6"
                fill="none"
                stroke={palette.white}
                strokeWidth="2"
              >
                <path d="M6 3h8l4 4v14H6z" />
                <path d="M14 3v5h5" />
                <path d="M9 13h6M9 17h6" />
              </svg>
            </div>

            <span className="text-lg font-bold tracking-tight">
              Docu<span style={{ color: palette.orange }}>Chat</span>
            </span>
          </a>

          <button
            type="button"
            onClick={() => navigate("/")}
            className="text-sm font-semibold transition hover:text-[#EB5D22] cursor-pointer"
            style={{ color: palette.white }}
          >
            Home
          </button>
        </nav>
      </header>

      <main className="relative z-10">
        <section ref={s1.ref} style={s1.style} className="mx-auto max-w-5xl px-6 pb-16 pt-16 text-center lg:pt-16">
          <h1 className="text-4xl font-black tracking-tight sm:text-5xl lg:text-6xl">
            <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1, duration: 0.8 }}>Understand </motion.span>
            <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4, duration: 0.8 }}>your </motion.span>
            <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7, duration: 0.8 }}>documents </motion.span>
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1, duration: 0.8 }}
              className="mt-2 block"
              style={{ color: palette.orange }}
            >
              through conversation.
            </motion.span>
          </h1>
          <p className="mx-auto mt-7 max-w-3xl text-base leading-8 sm:text-lg min-h-[96px]" style={{ color: palette.muted }}>
            {displayedText}
          </p>
        </section>

        <section ref={s2.ref} style={s2.style} className="mx-auto max-w-6xl px-6 pb-16 lg:px-10">
          <div className="rounded-3xl border p-7 sm:p-10" style={{ borderColor: `${palette.blue}70`, backgroundColor: `${palette.navy}E6` }}>
            <div className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
              <div>
                <p className="mb-3 text-sm font-bold uppercase tracking-widest" style={{ color: palette.orange }}>About the Project</p>
                <h2 className="text-3xl font-bold sm:text-4xl">Your documents, made easier to explore.</h2>
                <p className="mt-5 leading-8" style={{ color: palette.muted }}>
                  Large documents can contain valuable information, but finding a specific answer can take time. DocuChat provides a conversational interface that allows users to interact with their documents and quickly find relevant information.
                </p>
                <p className="mt-4 leading-8" style={{ color: palette.muted }}>
                  The project combines document processing, AI-based question answering, and a simple chat interface to create a more natural way of working with documents.
                </p>
              </div>

              <div className="rounded-2xl border p-6" style={{ borderColor: `${palette.blueBright}60`, backgroundColor: palette.ink }}>
                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl" style={{ backgroundColor: palette.orange }}>
                    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke={palette.white} strokeWidth="2">
                      <path d="M6 3h8l4 4v14H6z" /><path d="M14 3v5h5" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-bold">Document Chatbot</p>
                    <p className="text-sm" style={{ color: palette.muted }}>AI-powered document interaction</p>
                  </div>
                </div>
                <div className="space-y-3">
                  {["Natural language questions", "Faster document exploration", "AI-generated answers", "Simple conversational interface"].map((item) => (
                    <div key={item} className="flex items-center gap-3 rounded-xl border px-4 py-3" style={{ borderColor: `${palette.blue}50`, backgroundColor: palette.navy }}>
                      <span className="flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold" style={{ backgroundColor: palette.blue }}>✓</span>
                      <span className="text-sm">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section ref={s3.ref} style={s3.style} className="mx-auto max-w-6xl px-6 pb-16 lg:px-10">
          <div className="mb-8">
            <p className="text-sm font-bold uppercase tracking-widest" style={{ color: palette.orange }}>How It Works</p>
            <h2 className="mt-2 text-3xl font-bold sm:text-4xl">Simple. Intelligent. Conversational.</h2>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {features.map(([number, title, description]) => (
              <div key={number} className="rounded-2xl border p-6 transition duration-300 hover:-translate-y-1" style={{ borderColor: `${palette.blue}60`, backgroundColor: palette.navy }}>
                <span className="text-sm font-black" style={{ color: palette.orange }}>{number}</span>
                <h3 className="mt-4 text-xl font-bold">{title}</h3>
                <p className="mt-3 text-sm leading-7" style={{ color: palette.muted }}>{description}</p>
              </div>
            ))}
          </div>
        </section>

        <section ref={s4.ref} style={s4.style} className="mx-auto max-w-4xl px-6 pb-24 text-center">
          <div className="rounded-3xl border px-6 py-12 sm:px-10" style={{ borderColor: `${palette.blueBright}70`, backgroundColor: palette.navy }}>
            <h2 className="text-3xl font-black sm:text-4xl">Ready to explore your documents?</h2>
            <p className="mx-auto mt-4 max-w-2xl leading-7" style={{ color: palette.muted }}>
              Start a conversation with your document and find the information you need faster.
            </p>
            <button
              type="button"
              onClick={() => setChatKey(k => k + 1)}
              className="mt-8 inline-flex items-center gap-3 rounded-xl px-7 py-4 font-bold transition duration-300 hover:-translate-y-1 hover:shadow-lg"
              style={{ backgroundColor: palette.orange }}
            >
              Go to Chatbot
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14" /><path d="m13 6 6 6-6 6" />
              </svg>
            </button>
          </div>
        </section>
      </main>

      <footer className="border-t px-6 py-6 text-center text-sm" style={{ borderColor: `${palette.blue}40`, color: palette.muted }}>
        © {new Date().getFullYear()} DocuChat. All rights reserved.
      </footer>

      {/* Floating ChatWindow — opens when Go to Chatbot is clicked */}
      {chatKey > 0 && <ChatWindow key={chatKey} defaultOpen={true} />}
    </div>
  );
}
