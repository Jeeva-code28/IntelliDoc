import React from 'react';
import ConversationsSidebar from '../components/Sidebar/ConversationsSidebar';
import KnowledgeBase from '../components/KnowledgeBase/KnowledgeBase';
import ChatWorkspace from '../components/Chat/ChatWorkspace';

export default function ChatPage() {
  return (
    <div className="app-container flex h-screen w-screen overflow-hidden">
      <ConversationsSidebar />
      <ChatWorkspace />
      <KnowledgeBase />
    </div>
  );
}
