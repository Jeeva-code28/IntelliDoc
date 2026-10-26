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
  const [isGenerating, setIsGenerating] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState([]);
  const [provider, setProvider] = useState('huggingface');
  const [queryError, setQueryError] = useState(null);
  const [uploadError, setUploadError] = useState(null);

  // Citation & Evidence Drawer state
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [activeCitationsList, setActiveCitationsList] = useState([]);

  // Document selection for querying
  const [selectedDocIds, setSelectedDocIds] = useState(new Set());

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

  // Keep selectedDocIds populated when activeConversation documents change
  useEffect(() => {
    if (activeConversation?.documents) {
      const allReadyIds = new Set(
        activeConversation.documents
          .filter(d => d.status === 'ready' || d.status === 'processing')
          .map(d => d.id)
      );
      setSelectedDocIds(allReadyIds);
    }
  }, [activeConversation?.documents?.length]);

  const loadConversations = async () => {
    try {
      const res = await fetch('/api/conversations');
      if (!res.ok) return;
      const data = await res.json();
      setConversations(data);

      if (data.length > 0 && !currentConversationId) {
        setCurrentConversationId(data[0].id);
      } else if (data.length === 0) {
        await createNewChat();
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
      return newConv.id;
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

  const sendMessage = async (content, selectedProvider = provider) => {
    if (!currentConversationId || !content.trim()) return;

    setQueryError(null);
    setIsGenerating(true);

    // Optimistically update UI
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString()
    };

    setActiveConversation(prev => ({
      ...prev,
      messages: [...(prev?.messages || []), userMessage]
    }));

    try {
      const requestPayload = {
        query: content,
        conversation_id: currentConversationId,
        llm_provider: selectedProvider,
        skip_verification: false
      };
      if (selectedDocIds && selectedDocIds.size > 0) {
        requestPayload.document_ids = Array.from(selectedDocIds);
      }

      const res = await fetch(`/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload)
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Query failed with status ${res.status}`);
      }

      const data = await res.json();

      const assistantMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.answer,
        status: data.status || 'answered',
        evidence_sufficient: data.evidence_sufficient !== false,
        citations: data.citations || [],
        verification: data.verification,
        latency_ms: data.latency_ms,
        retrieval_latency_ms: data.retrieval_latency_ms,
        intent: data.intent,
        created_at: new Date().toISOString()
      };

      // Update with response
      setActiveConversation(prev => ({
        ...prev,
        messages: [...(prev?.messages || []), assistantMessage]
      }));

      // Refresh conversation in sidebar list to update message count / title
      await loadConversations();
    } catch (err) {
      console.error('Error sending message:', err);
      setQueryError(err.message || 'Failed to generate answer. Please try again.');
      // Add error message to conversation
      setActiveConversation(prev => ({
        ...prev,
        messages: [
          ...(prev?.messages || []),
          {
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: `⚠️ **Unable to complete request**: ${err.message || 'Network or provider error.'}`,
            isError: true,
            created_at: new Date().toISOString()
          }
        ]
      }));
    } finally {
      setIsGenerating(false);
    }
  };

  const pollDocumentStatus = async (convId, maxAttempts = 30) => {
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

      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    await loadConversations();
  };

  const uploadFiles = async (files) => {
    if (!currentConversationId || !files || files.length === 0) return;

    setUploadError(null);
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
          setUploadError(`Failed to upload ${file.name}: ${errText}`);
        }
      }

      await loadActiveConversation(currentConversationId);
      await pollDocumentStatus(currentConversationId);
    } catch (err) {
      console.error('Error uploading files:', err);
      setUploadError(err.message || 'Error uploading files');
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

      setActiveConversation(prev => ({
        ...prev,
        documents: prev?.documents?.filter(d => d.id !== docId) || []
      }));
      await loadConversations();
    } catch (err) {
      console.error('Error deleting document:', err);
      setUploadError(err.message || 'Failed to delete document');
    }
  };

  const toggleDocSelection = (docId) => {
    setSelectedDocIds(prev => {
      const next = new Set(prev);
      if (next.has(docId)) {
        next.delete(docId);
      } else {
        next.add(docId);
      }
      return next;
    });
  };

  const selectAllDocs = () => {
    if (activeConversation?.documents) {
      setSelectedDocIds(new Set(activeConversation.documents.map(d => d.id)));
    }
  };

  const clearDocSelection = () => {
    setSelectedDocIds(new Set());
  };

  const openCitation = (citation, allCitations = []) => {
    setSelectedCitation(citation);
    setActiveCitationsList(allCitations.length > 0 ? allCitations : [citation]);
  };

  const closeCitation = () => {
    setSelectedCitation(null);
  };

  const value = {
    conversations,
    currentConversationId,
    activeConversation,
    loading,
    isGenerating,
    uploadingFiles,
    provider,
    setProvider,
    queryError,
    uploadError,
    selectedDocIds,
    toggleDocSelection,
    selectAllDocs,
    clearDocSelection,
    selectedCitation,
    activeCitationsList,
    openCitation,
    closeCitation,
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
