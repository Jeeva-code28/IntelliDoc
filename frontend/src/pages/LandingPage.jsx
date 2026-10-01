import React from 'react';
import ChatWindow from '../components/Chat/ChatWindow';
import Hero3DBackground from '../components/Landing/Hero3DBackground';
import { motion } from 'framer-motion';

export default function LandingPage() {
  return (
    <div className="min-h-screen w-full bg-[var(--color-bg-main)] text-[var(--color-text-primary)] relative overflow-hidden">
      {/* 3D Background */}
      <Hero3DBackground />

      {/* Hero Content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center z-10 pointer-events-none">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="flex flex-col items-center"
        >
          <div className="w-16 h-16 rounded-2xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] flex items-center justify-center font-bold text-[var(--color-text-primary)] text-2xl tracking-wider shadow-sm mb-8 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-[var(--color-accent-indigo)]/20 to-transparent" />
            NPN
          </div>
          <h1 className="text-4xl md:text-5xl font-['Inter'] font-bold mb-4 tracking-tight">Project NPN</h1>
          <p className="text-[var(--color-text-secondary)] text-lg md:text-xl max-w-2xl mb-8 leading-relaxed font-light">
            High-performance, local-first multimodal RAG for financial and technical intelligence across PDF, Video, Audio, Images, and Data.
          </p>
          <p className="text-[var(--color-text-muted)] text-sm tracking-wide">
            Click the widget in the bottom right to start a conversation.
          </p>
        </motion.div>
      </div>

      {/* Floating Chatbot Widget */}
      <div className="z-20 relative pointer-events-auto">
        <ChatWindow />
      </div>
    </div>
  );
}
