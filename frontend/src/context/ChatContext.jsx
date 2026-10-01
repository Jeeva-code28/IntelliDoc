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
  const [uploadingFiles, setUploadingFiles] = useState([]);

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

  const pollDocumentStatus = async (convId, maxAttempts = 20) => {
    if (!convId) return;

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      try {
        const res = await fetch(`/api/conversations/${convId}`);
        if (!res.ok) break;
        const data = await res.json();
        setActiveConversation(data);

        const docs = data.documents || [];
        const stillProcessing = docs.some((d) => d.status === 'processing');
        if (!stillProcessing) break;
      } catch (err) {
        console.error('Error polling document status:', err);
        break;
      }

      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
  };

  const uploadFiles = async (files) => {
    if (!currentConversationId || !files || files.length === 0) return;

    const fileArray = Array.from(files);
    setUploadingFiles((prev) => [...prev, ...fileArray.map((file) => file.name)]);

    try {
      for (const file of fileArray) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('conversation_id', currentConversationId);

        const res = await fetch(`/api/documents/upload`, {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const errText = await res.text();
          console.error(`Failed to upload ${file.name}:`, errText);
          alert(`Failed to upload ${file.name}: ${errText}`);
        }
      }

      await loadActiveConversation(currentConversationId);
      await pollDocumentStatus(currentConversationId);
    } catch (err) {
      console.error('Error uploading files:', err);
      alert('Error uploading files: ' + err.message);
    } finally {
      setUploadingFiles((prev) => prev.filter((name) => !fileArray.some((file) => file.name === name)));
    }
  };

  const deleteDocument = async (docId) => {
    if (!docId) return;
    try {
      const res = await fetch(`/api/documents/${docId}`, {
        method: 'DELETE'
      });
      if (!res.ok) throw new Error('Failed to delete document');
      
      // Update local state to remove the document
      setActiveConversation(prev => ({
        ...prev,
        documents: prev?.documents?.filter(d => d.id !== docId) || []
      }));
    } catch (err) {
      console.error('Error deleting document:', err);
    }
  };

  const value = {
    conversations,
    currentConversationId,
    activeConversation,
    loading,
    uploadingFiles,
    setCurrentConversationId,
    createNewChat,
    sendMessage,
    deleteConversation,
    uploadFiles,
    deleteDocument
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}
