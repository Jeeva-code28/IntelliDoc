import React, { createContext, useState, useEffect, useContext } from 'react';

const ChatContext = createContext();

export function useChat() {
  return useContext(ChatContext);
}

export function ChatProvider({ children }) {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [activeConversation, setActiveConversation] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch all conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Fetch active conversation details when ID changes
  useEffect(() => {
    if (currentConversationId) {
      loadActiveConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const res = await fetch('/api/conversations');
      if (!res.ok) return;
      const data = await res.json();
      setConversations(data);
      
      if (data.length > 0 && !currentConversationId) {
        setCurrentConversationId(data[0].id);
      } else if (data.length === 0) {
        createNewChat();
      }
    } catch (err) {
      console.error('Error loading conversations:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadActiveConversation = async (id) => {
    try {
      const res = await fetch(`/api/conversations/${id}`);
      if (!res.ok) return;
      const data = await res.json();
      setActiveConversation(data);
    } catch (err) {
      console.error('Error fetching conversation details:', err);
    }
  };

  const createNewChat = async () => {
    try {
      const res = await fetch('/api/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Conversation' })
      });
      if (!res.ok) return;
      const newConv = await res.json();
      setCurrentConversationId(newConv.id);
      await loadConversations();
    } catch (err) {
      console.error('Error creating new chat:', err);
    }
  };

  const deleteConversation = async (id) => {
    try {
      const res = await fetch(`/api/conversations/${id}`, { method: 'DELETE' });
      if (res.ok) {
        if (currentConversationId === id) {
          await createNewChat();
        } else {
          await loadConversations();
        }
      }
    } catch (err) {
      console.error('Error deleting conversation:', err);
    }
  };

  const sendMessage = async (content, provider) => {
    if (!currentConversationId || !content.trim()) return;

    // Optimistically update UI
    const newMessage = { role: 'user', content };
    setActiveConversation(prev => ({
      ...prev,
      messages: [...(prev?.messages || []), newMessage]
    }));

    try {
      const res = await fetch(`/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: content, 
          conversation_id: currentConversationId,
          llm_provider: provider 
        })
      });
      
      if (!res.ok) throw new Error('Query failed');
      const data = await res.json();
      
      // Update with response
      setActiveConversation(prev => ({
        ...prev,
        messages: [...(prev?.messages || []), { role: 'assistant', content: data.answer }]
      }));
    } catch (err) {
      console.error('Error sending message:', err);
    }
  };

  const uploadFiles = async (files) => {
    if (!currentConversationId || !files || files.length === 0) return;
    
    try {
      const uploadPromises = Array.from(files).map(file => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('conversation_id', currentConversationId);
        
        return fetch(`/api/documents/upload`, {
          method: 'POST',
          body: formData
        });
      });

      await Promise.all(uploadPromises);
      loadActiveConversation(currentConversationId); // Refresh to show new docs
    } catch (err) {
      console.error('Error uploading files:', err);
    }
  };

  const value = {
    conversations,
    currentConversationId,
    activeConversation,
    loading,
    setCurrentConversationId,
    createNewChat,
    deleteConversation,
    sendMessage,
    uploadFiles
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}
