import React from 'react';
import ChatWindow from '../components/Chat/ChatWindow';
import Hero3DBackground from '../components/Landing/Hero3DBackground';
import DocumentChatbotHero from '../components/Landing/DocumentChatbotHero';
import { motion } from 'framer-motion';

export default function LandingPage() {
  return (
    <div className="min-h-screen w-full bg-[var(--color-bg-main)] text-[var(--color-text-primary)] relative overflow-hidden">
      {/* 3D Background */}
      <DocumentChatbotHero />



      {/* Floating Chatbot Widget */}
      <div className="z-20 relative pointer-events-auto">
        <ChatWindow />
      </div>
    </div>
  );
}
