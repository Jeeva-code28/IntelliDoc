import React, { useState } from 'react';
import ConversationsSidebar from '../components/Sidebar/ConversationsSidebar';
import ChatWorkspace from '../components/Chat/ChatWorkspace';
import KnowledgeBase from '../components/KnowledgeBase/KnowledgeBase';
import CitationDrawer from '../components/Modals/CitationDrawer';

export default function WorkspacePage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [knowledgeBaseOpen, setKnowledgeBaseOpen] = useState(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#090909] text-[#F5F1EC] select-none">
      {/* Left Navigation & Conversations */}
      <ConversationsSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Chat Workspace */}
      <ChatWorkspace
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onToggleKnowledgeBase={() => setKnowledgeBaseOpen(!knowledgeBaseOpen)}
      />

      {/* Right Document Library & Ingestion */}
      <KnowledgeBase
        isOpen={knowledgeBaseOpen}
        onClose={() => setKnowledgeBaseOpen(false)}
      />

      {/* On-Demand Verified Source Evidence Panel */}
      <CitationDrawer />
    </div>
  );
}
