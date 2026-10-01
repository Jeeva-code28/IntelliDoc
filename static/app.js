// Project NPN (Narrative, Proof, Numbers) Multimodal Frontend Engine
// Strict Conversation Scoping, Zero-Spillover, Prompt Navigator & History Archiving

let currentConversationId = null;
let currentCitations = [];
let trackedPrompts = [];
let deleteTargetId = null;
let activeHistoryId = null;
let allHistoryArchives = [];
let popoverHideTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    initDropZone();
    initQueryForm();
    initPromptNavigatorEvents();
});

async function initApp() {
    await loadHistoryCount();
    await loadConversationsList();
}

// ==========================================
// Conversation Management
// ==========================================

async function loadConversationsList() {
    const convListEl = document.getElementById('conversationsList');
    try {
        const res = await fetch('/api/conversations');
        if (!res.ok) return;

        const convs = await res.json();
        if (convs.length === 0) {
            await createNewChat();
            return;
        }

        convListEl.innerHTML = convs.map(c => {
            const isActive = c.id === currentConversationId;
            return `
                <div class="conversation-item ${isActive ? 'active' : ''}" onclick="selectConversation('${c.id}')" id="conv-item-${c.id}">
                    <div class="conversation-item-top">
                        <span class="conversation-item-title" title="${escapeHtml(c.title)}">${escapeHtml(c.title || 'New Conversation')}</span>
                        <div class="conv-item-actions">
                            <span class="conv-doc-chip">${c.document_count || 0} docs</span>
                            <button class="conv-delete-btn" onclick="openDeleteConfirmModal(event, '${c.id}', '${escapeHtml(c.title || 'Conversation')}')" title="Delete & Archive conversation">
                                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="3 6 5 6 21 6"></polyline>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="conversation-item-meta">
                        <span>${c.message_count || 0} messages</span>
                    </div>
                </div>
            `;
        }).join('');

        if (!currentConversationId && convs.length > 0) {
            await selectConversation(convs[0].id);
        } else if (currentConversationId && !convs.some(c => c.id === currentConversationId)) {
            // If current conversation was deleted, select first available
            if (convs.length > 0) {
                await selectConversation(convs[0].id);
            } else {
                await createNewChat();
            }
        }
    } catch (err) {
        console.error('Error loading conversations:', err);
    }
}

async function createNewChat() {
    try {
        const res = await fetch('/api/conversations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'New Conversation' })
        });
        if (!res.ok) return;

        const newConv = await res.json();
        currentConversationId = newConv.id;
        await loadConversationsList();
        await selectConversation(newConv.id);
    } catch (err) {
        console.error('Error creating new chat:', err);
    }
}

async function selectConversation(convId) {
    currentConversationId = convId;

    // Update active highlight in sidebar
    document.querySelectorAll('.conversation-item').forEach(el => el.classList.remove('active'));
    const activeEl = document.getElementById(`conv-item-${convId}`);
    if (activeEl) activeEl.classList.add('active');

    const titleEl = document.getElementById('activeConvTitle');
    const messagesContainer = document.getElementById('messagesContainer');
    const docCountBadge = document.getElementById('docCountBadge');

    try {
        const res = await fetch(`/api/conversations/${convId}`);
        if (!res.ok) return;

        const conv = await res.json();
        titleEl.innerText = conv.title || 'Conversation Workspace';

        // Render Conversation Documents
        renderConversationDocuments(conv.documents || []);
        docCountBadge.innerText = `${(conv.documents || []).length} files`;

        // Render Messages
        messagesContainer.innerHTML = '';
        if (!conv.messages || conv.messages.length === 0) {
            messagesContainer.innerHTML = `
                <div class="welcome-card" id="welcomeCard">
                    <div class="welcome-glow"></div>
                    <div class="welcome-icon">⚡</div>
                    <h3>Conversation: ${escapeHtml(conv.title || 'New Chat')}</h3>
                    <p>This conversation has its own isolated knowledge base. Upload documents into the left panel or ask grounded questions below.</p>
                    <div class="sample-queries">
                        <button class="sample-btn" onclick="useSampleQuery('What is the total revenue and profit breakdown in the uploaded documents?')">
                            📊 Financial Table Analysis
                        </button>
                        <button class="sample-btn" onclick="useSampleQuery('Summarize key quantitative metrics and findings from all files in this chat.')">
                            📑 Multi-Document Summary
                        </button>
                    </div>
                </div>
            `;
            buildPromptNavigator([]);
        } else {
            let promptIdx = 0;
            conv.messages.forEach(m => {
                const bubble = document.createElement('div');
                bubble.className = `message-bubble ${m.role}`;
                if (m.role === 'user') {
                    bubble.id = `prompt-bubble-${promptIdx}`;
                    bubble.innerHTML = `
                        <div class="bubble-tag-row">
                            <span class="prompt-index-chip">Prompt #${promptIdx + 1}</span>
                        </div>
                        <div class="bubble-content">${escapeHtml(m.content)}</div>
                    `;
                    promptIdx++;
                } else {
                    bubble.innerHTML = `
                        <div class="bubble-content formatted-answer">${formatAnswerMarkdown(m.content)}</div>
                    `;
                }
                messagesContainer.appendChild(bubble);
            });
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            buildPromptNavigator(conv.messages);
        }
    } catch (err) {
        console.error('Error fetching conversation details:', err);
    }
}

function renderConversationDocuments(docs) {
    const docsList = document.getElementById('documentsList');
    if (!docs || docs.length === 0) {
        docsList.innerHTML = '<div class="empty-docs">No documents in this conversation. Drag files above to build its knowledge base.</div>';
        return;
    }

    docsList.innerHTML = docs.map(d => {
        const ext = d.filename.split('.').pop().toLowerCase();
        let icon = '📄';
        if (['mp4', 'mov', 'avi', 'webm', 'mkv'].includes(ext)) icon = '🎬';
        else if (['mp3', 'wav', 'm4a', 'ogg', 'flac'].includes(ext)) icon = '🎙️';
        else if (['png', 'jpg', 'jpeg', 'webp', 'svg', 'bmp'].includes(ext)) icon = '🖼️';
        else if (['csv', 'xlsx', 'tsv'].includes(ext)) icon = '📊';
        else if (['zip', 'tar', 'gz'].includes(ext)) icon = '📦';
        else if (['txt', 'md', 'markdown', 'log', 'json'].includes(ext)) icon = '📝';

        return `
            <div class="doc-item">
                <span class="doc-name" title="${escapeHtml(d.filename)}">${icon} ${escapeHtml(d.filename)}</span>
                <span class="status-badge ${d.status}">${d.status}</span>
            </div>
        `;
    }).join('');
}

async function refreshActiveDocuments() {
    if (!currentConversationId) return;
    try {
        const res = await fetch(`/api/conversations/${currentConversationId}/documents`);
        if (!res.ok) return;
        const docs = await res.json();
        renderConversationDocuments(docs);
        document.getElementById('docCountBadge').innerText = `${docs.length} files`;
        await loadConversationsList();
    } catch (err) {
        console.error('Error refreshing active documents:', err);
    }
}

// ==========================================
// Conversation Prompt Slider & Timeline Navigator
// ==========================================

function buildPromptNavigator(messages) {
    const nav = document.getElementById('promptNavigator');
    const ticksWrapper = document.getElementById('navTicksWrapper');
    const popoverList = document.getElementById('popoverPromptsList');
    const popoverCount = document.getElementById('popoverPromptCount');

    trackedPrompts = [];
    let idx = 0;

    (messages || []).forEach(m => {
        if (m.role === 'user') {
            trackedPrompts.push({
                index: idx,
                text: m.content,
                timestamp: m.created_at || '',
                elementId: `prompt-bubble-${idx}`
            });
            idx++;
        }
    });

    popoverCount.innerText = trackedPrompts.length;

    if (trackedPrompts.length === 0) {
        ticksWrapper.innerHTML = '<div class="nav-empty-hint">No prompts</div>';
        popoverList.innerHTML = '<div class="popover-empty">Ask a question to see prompts here</div>';
        return;
    }

    // 1. Render Multi-line Tick Indicators on Timeline Rail
    ticksWrapper.innerHTML = trackedPrompts.map((p, i) => {
        const titleSnippet = escapeHtml(p.text.length > 50 ? p.text.substring(0, 50) + '...' : p.text);
        return `
            <div 
                class="nav-tick ${i === 0 ? 'active' : ''}" 
                id="nav-tick-${i}" 
                onclick="smoothScrollToPrompt(${i})"
                title="Prompt #${i + 1}: ${titleSnippet}"
            >
                <span class="tick-line"></span>
                <span class="tick-badge">#${i + 1}</span>
            </div>
        `;
    }).join('');

    // 2. Render Hover Popover Cards (Scrollable Prompt Preview Deck)
    popoverList.innerHTML = trackedPrompts.map((p, i) => {
        return `
            <div class="popover-prompt-card" onclick="smoothScrollToPrompt(${i})" id="popover-card-${i}">
                <div class="popover-prompt-top">
                    <span class="popover-prompt-num">#${i + 1}</span>
                    <span class="popover-prompt-jump">Jump ➔</span>
                </div>
                <div class="popover-prompt-text">${escapeHtml(p.text)}</div>
            </div>
        `;
    }).join('');

    updateScrubberPosition();
}

function initPromptNavigatorEvents() {
    const nav = document.getElementById('promptNavigator');
    const popover = document.getElementById('promptHoverPopover');
    const messagesContainer = document.getElementById('messagesContainer');

    // Hover events on navigator rail & popover
    nav.addEventListener('mouseenter', () => {
        if (popoverHideTimeout) clearTimeout(popoverHideTimeout);
        if (trackedPrompts.length > 0) {
            popover.classList.remove('hidden');
        }
    });

    nav.addEventListener('mouseleave', () => {
        popoverHideTimeout = setTimeout(() => {
            popover.classList.add('hidden');
        }, 220);
    });

    popover.addEventListener('mouseenter', () => {
        if (popoverHideTimeout) clearTimeout(popoverHideTimeout);
        popover.classList.remove('hidden');
    });

    popover.addEventListener('mouseleave', () => {
        popoverHideTimeout = setTimeout(() => {
            popover.classList.add('hidden');
        }, 220);
    });

    // Real-time scroll observation
    messagesContainer.addEventListener('scroll', () => {
        updateScrubberPosition();
        highlightActivePromptOnScroll();
    });
}

function updateScrubberPosition() {
    const messagesContainer = document.getElementById('messagesContainer');
    const scrubberThumb = document.getElementById('navScrubberThumb');
    if (!messagesContainer || !scrubberThumb) return;

    const scrollHeight = messagesContainer.scrollHeight - messagesContainer.clientHeight;
    if (scrollHeight <= 0) {
        scrubberThumb.style.top = '0%';
        return;
    }

    const scrollPct = (messagesContainer.scrollTop / scrollHeight) * 100;
    const boundedPct = Math.min(Math.max(scrollPct, 0), 92);
    scrubberThumb.style.top = `${boundedPct}%`;
}

function highlightActivePromptOnScroll() {
    if (trackedPrompts.length === 0) return;
    const messagesContainer = document.getElementById('messagesContainer');
    const containerTop = messagesContainer.getBoundingClientRect().top;

    let activeIdx = 0;
    let minDiff = Infinity;

    trackedPrompts.forEach(p => {
        const el = document.getElementById(p.elementId);
        if (el) {
            const rect = el.getBoundingClientRect();
            const diff = Math.abs(rect.top - containerTop);
            if (rect.top <= containerTop + 150 && diff < minDiff) {
                minDiff = diff;
                activeIdx = p.index;
            }
        }
    });

    // Update active tick and popover card
    document.querySelectorAll('.nav-tick').forEach(t => t.classList.remove('active'));
    const activeTick = document.getElementById(`nav-tick-${activeIdx}`);
    if (activeTick) activeTick.classList.add('active');

    document.querySelectorAll('.popover-prompt-card').forEach(c => c.classList.remove('active'));
    const activeCard = document.getElementById(`popover-card-${activeIdx}`);
    if (activeCard) activeCard.classList.add('active');
}

function smoothScrollToPrompt(index) {
    const prompt = trackedPrompts[index];
    if (!prompt) return;

    const targetEl = document.getElementById(prompt.elementId);
    if (!targetEl) return;

    // Smooth scroll directly to prompt bubble
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Flash highlight pulse on landing
    targetEl.classList.remove('highlight-landing-pulse');
    void targetEl.offsetWidth; // Trigger reflow
    targetEl.classList.add('highlight-landing-pulse');

    // Update active states
    document.querySelectorAll('.nav-tick').forEach(t => t.classList.remove('active'));
    const activeTick = document.getElementById(`nav-tick-${index}`);
    if (activeTick) activeTick.classList.add('active');

    document.querySelectorAll('.popover-prompt-card').forEach(c => c.classList.remove('active'));
    const activeCard = document.getElementById(`popover-card-${index}`);
    if (activeCard) {
        activeCard.classList.add('active');
        activeCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function jumpToPromptPosition(pos) {
    const messagesContainer = document.getElementById('messagesContainer');
    if (!messagesContainer) return;

    if (trackedPrompts.length === 0) {
        if (pos === 'top') messagesContainer.scrollTo({ top: 0, behavior: 'smooth' });
        else if (pos === 'bottom') messagesContainer.scrollTo({ top: messagesContainer.scrollHeight, behavior: 'smooth' });
        return;
    }

    if (pos === 'top') {
        smoothScrollToPrompt(0);
    } else if (pos === 'bottom') {
        smoothScrollToPrompt(trackedPrompts.length - 1);
    } else if (pos === 'mid') {
        const midIdx = Math.floor(trackedPrompts.length / 2);
        smoothScrollToPrompt(midIdx);
    }
}

// ==========================================
// Conversation Deletion & Confirmation Modal
// ==========================================

function confirmDeleteCurrentConversation() {
    if (!currentConversationId) return;
    const title = document.getElementById('activeConvTitle').innerText || 'Active Conversation';
    openDeleteConfirmModal(null, currentConversationId, title);
}

function openDeleteConfirmModal(event, convId, convTitle) {
    if (event) event.stopPropagation();
    deleteTargetId = convId;

    document.getElementById('deleteTargetConvTitle').innerText = `"${convTitle}"`;
    document.getElementById('deleteConfirmModalOverlay').classList.remove('hidden');
}

function closeDeleteConfirmModal() {
    document.getElementById('deleteConfirmModalOverlay').classList.add('hidden');
    deleteTargetId = null;
}

async function executeConversationDeletion() {
    if (!deleteTargetId) return;

    const convId = deleteTargetId;
    closeDeleteConfirmModal();

    try {
        const res = await fetch(`/api/conversations/${convId}`, {
            method: 'DELETE'
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Failed to delete conversation');
        }

        const data = await res.json();
        showToast('Conversation deleted & archived to History.');

        await loadHistoryCount();

        // If the active conversation was deleted, reset currentConversationId
        if (currentConversationId === convId) {
            currentConversationId = null;
        }

        await loadConversationsList();
    } catch (err) {
        alert(`Error deleting conversation: ${err.message}`);
    }
}

// ==========================================
// History & Archives Feature
// ==========================================

async function loadHistoryCount() {
    try {
        const res = await fetch('/api/history');
        if (!res.ok) return;
        const archives = await res.json();
        allHistoryArchives = archives;
        document.getElementById('historyCountBadge').innerText = archives.length;
    } catch (err) {
        console.error('Error fetching history count:', err);
    }
}

async function openHistoryModal() {
    const modal = document.getElementById('historyModalOverlay');
    modal.classList.remove('hidden');
    await renderHistoryArchivesList();
}

function closeHistoryModal() {
    document.getElementById('historyModalOverlay').classList.add('hidden');
}

async function renderHistoryArchivesList() {
    const listContainer = document.getElementById('historyArchivesList');
    listContainer.innerHTML = '<div class="loading-pulse">Loading archived history files...</div>';

    try {
        const res = await fetch('/api/history');
        if (!res.ok) throw new Error('Failed to load history');

        allHistoryArchives = await res.json();
        document.getElementById('historyCountBadge').innerText = allHistoryArchives.length;
        filterHistoryArchives();
    } catch (err) {
        listContainer.innerHTML = `<div class="error-text">Failed to load history archives: ${escapeHtml(err.message)}</div>`;
    }
}

function filterHistoryArchives() {
    const listContainer = document.getElementById('historyArchivesList');
    const searchInput = document.getElementById('historySearchInput');
    const term = (searchInput ? searchInput.value : '').toLowerCase().trim();

    const filtered = allHistoryArchives.filter(h => {
        return h.title.toLowerCase().includes(term) || (h.transcript_summary || '').toLowerCase().includes(term);
    });

    if (filtered.length === 0) {
        listContainer.innerHTML = `
            <div class="empty-history-state">
                <div class="empty-icon">📂</div>
                <h4>${term ? 'No matching archives found' : 'No History Archives Yet'}</h4>
                <p>${term ? 'Try searching with a different keyword.' : 'When you delete conversations, their complete prompts, replies, and citations are automatically preserved here.'}</p>
            </div>
        `;
        return;
    }

    listContainer.innerHTML = filtered.map(h => {
        const deletedDate = h.deleted_at ? new Date(h.deleted_at).toLocaleString() : 'Recently';
        return `
            <div class="history-archive-card">
                <div class="history-card-header">
                    <div class="history-card-title-row">
                        <span class="history-archive-icon">📜</span>
                        <h4 class="history-card-title" title="${escapeHtml(h.title)}">${escapeHtml(h.title)}</h4>
                    </div>
                    <span class="history-date-badge">${escapeHtml(deletedDate)}</span>
                </div>

                <div class="history-summary-text">
                    ${escapeHtml(h.transcript_summary || 'Archived conversation transcript')}
                </div>

                <div class="history-card-stats">
                    <span class="stat-pill">💬 ${h.message_count || 0} messages</span>
                    <span class="stat-pill">📁 ${h.document_count || 0} documents</span>
                </div>

                <div class="history-card-actions">
                    <button class="history-action-btn primary" onclick="viewArchivedTranscript('${h.id}')">
                        <span>👁️ View Transcript & Citations</span>
                    </button>
                    <button class="history-action-btn" onclick="downloadHistoryFile('${h.id}', 'md')">
                        <span>📥 Markdown</span>
                    </button>
                    <button class="history-action-btn" onclick="downloadHistoryFile('${h.id}', 'json')">
                        <span>📥 JSON</span>
                    </button>
                    <button class="history-action-btn danger" onclick="deleteSingleHistoryArchive('${h.id}')" title="Permanently delete this archive file">
                        <span>🗑️</span>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

async function viewArchivedTranscript(historyId) {
    activeHistoryId = historyId;
    const modal = document.getElementById('historyViewerModalOverlay');
    const titleEl = document.getElementById('transcriptViewerTitle');
    const bodyEl = document.getElementById('transcriptViewerBody');

    bodyEl.innerHTML = '<div class="loading-pulse">Loading archived transcript and source citations...</div>';
    modal.classList.remove('hidden');

    try {
        const res = await fetch(`/api/history/${historyId}`);
        if (!res.ok) throw new Error('Failed to load archive details');

        const detail = await res.json();
        titleEl.innerText = `Archived: ${detail.title || 'Conversation'}`;

        const docCount = detail.document_count || 0;
        const msgCount = detail.message_count || 0;
        const deletedDate = detail.deleted_at ? new Date(detail.deleted_at).toLocaleString() : 'N/A';

        let html = `
            <div class="transcript-meta-banner">
                <div class="meta-row"><strong>Title:</strong> <span>${escapeHtml(detail.title)}</span></div>
                <div class="meta-row"><strong>Archived Date:</strong> <span>${escapeHtml(deletedDate)}</span></div>
                <div class="meta-row"><strong>Total Messages:</strong> <span>${msgCount}</span> | <strong>Attached Documents:</strong> <span>${docCount}</span></div>
            </div>
        `;

        if (detail.json_data && detail.json_data.messages && detail.json_data.messages.length > 0) {
            html += '<div class="transcript-messages-stream">';
            let promptIdx = 1;

            detail.json_data.messages.forEach(m => {
                if (m.role === 'user') {
                    html += `
                        <div class="transcript-bubble user">
                            <div class="transcript-bubble-header">
                                <span class="transcript-role-pill">👤 User Prompt #${promptIdx}</span>
                                <span class="transcript-time">${escapeHtml(m.created_at || '')}</span>
                            </div>
                            <div class="transcript-bubble-content">${escapeHtml(m.content)}</div>
                        </div>
                    `;
                    promptIdx++;
                } else {
                    let citationsHtml = '';
                    if (m.sources && m.sources.length > 0) {
                        citationsHtml = `
                            <div class="transcript-citations-section">
                                <div class="transcript-citations-title">📌 Source Proofs & Citations (${m.sources.length}):</div>
                                <div class="transcript-citations-grid">
                                    ${m.sources.map(s => `
                                        <div class="transcript-citation-card ${escapeHtml((s.content_type || 'text').toLowerCase())}">
                                            <div class="tc-header">
                                                <span class="tc-tag">${escapeHtml(s.source_tag || '[SOURCE]')}</span>
                                                <span class="tc-filename">${escapeHtml(s.filename || 'Document')}</span>
                                                <span class="tc-page">p.${s.page_number || 1}</span>
                                            </div>
                                            <div class="tc-snippet">${escapeHtml(s.snippet || '')}</div>
                                            ${s.temporal_start !== null && s.temporal_start !== undefined ? `<div class="tc-time">⏱️ ${s.temporal_start}s - ${s.temporal_end}s</div>` : ''}
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `;
                    }

                    html += `
                        <div class="transcript-bubble assistant">
                            <div class="transcript-bubble-header">
                                <span class="transcript-role-pill assistant">🤖 Assistant Reply</span>
                                <span class="transcript-time">${escapeHtml(m.created_at || '')}</span>
                            </div>
                            <div class="transcript-bubble-content">${formatAnswerMarkdown(m.content)}</div>
                            ${citationsHtml}
                        </div>
                    `;
                }
            });
            html += '</div>';
        } else if (detail.markdown_content) {
            html += `
                <div class="transcript-markdown-view">
                    <pre class="raw-markdown-block">${escapeHtml(detail.markdown_content)}</pre>
                </div>
            `;
        } else {
            html += '<div class="empty-docs">No message content in this archive.</div>';
        }

        bodyEl.innerHTML = html;
    } catch (err) {
        bodyEl.innerHTML = `<div class="error-text">Error loading transcript: ${escapeHtml(err.message)}</div>`;
    }
}

function closeHistoryViewerModal() {
    document.getElementById('historyViewerModalOverlay').classList.add('hidden');
    activeHistoryId = null;
}

function downloadActiveHistoryFile(format) {
    if (!activeHistoryId) return;
    downloadHistoryFile(activeHistoryId, format);
}

function downloadHistoryFile(historyId, format) {
    const url = `/api/history/${historyId}/download?format=${format}`;
    const link = document.createElement('a');
    link.href = url;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

async function deleteSingleHistoryArchive(historyId) {
    if (!confirm('Are you sure you want to permanently delete this history archive file?')) return;

    try {
        const res = await fetch(`/api/history/${historyId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Delete failed');
        await loadHistoryCount();
        await renderHistoryArchivesList();
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
}

async function clearAllHistory() {
    if (!confirm('Are you sure you want to clear ALL history archive files? This cannot be undone.')) return;

    try {
        const res = await fetch('/api/history', { method: 'DELETE' });
        if (!res.ok) throw new Error('Clear all failed');
        await loadHistoryCount();
        await renderHistoryArchivesList();
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
}

// ==========================================
// Toast Notification
// ==========================================

function showToast(message) {
    let toast = document.getElementById('appToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'appToast';
        toast.className = 'app-toast';
        document.body.appendChild(toast);
    }
    toast.innerText = message;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// ==========================================
// Drop Zone & File Upload
// ==========================================

function initDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--primary-cyan)';
        dropZone.style.background = 'rgba(6, 182, 212, 0.08)';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'rgba(6, 182, 212, 0.3)';
        dropZone.style.background = 'rgba(15, 23, 42, 0.6)';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'rgba(6, 182, 212, 0.3)';
        dropZone.style.background = 'rgba(15, 23, 42, 0.6)';
        if (e.dataTransfer.files.length > 0) {
            for (let i = 0; i < e.dataTransfer.files.length; i++) {
                handleFileUpload(e.dataTransfer.files[i]);
            }
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length > 0) {
            for (let i = 0; i < fileInput.files.length; i++) {
                handleFileUpload(fileInput.files[i]);
            }
        }
    });
}

async function handleFileUpload(file) {
    const allowedExtensions = ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mov', '.avi', '.mp3', '.wav', '.csv', '.tsv', '.zip', '.txt', '.md', '.markdown', '.log', '.json'];
    const fileName = file.name.toLowerCase();
    const isAllowed = allowedExtensions.some(ext => fileName.endsWith(ext));

    if (!isAllowed) {
        alert('Unsupported format. Please upload PDF, TXT, CSV, Video, Audio, Image, or ZIP files.');
        return;
    }

    const progressCard = document.getElementById('uploadProgressCard');
    const progressFilename = document.getElementById('progressFilename');
    const progressPercent = document.getElementById('progressPercent');
    const progressBarFill = document.getElementById('progressBarFill');
    const progressStatusText = document.getElementById('progressStatusText');

    progressFilename.innerText = file.name;
    progressPercent.innerText = '0%';
    progressBarFill.style.width = '0%';
    progressStatusText.innerText = `Uploading ${file.name} to active conversation...`;
    progressCard.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);
    if (currentConversationId) {
        formData.append('conversation_id', currentConversationId);
    }

    try {
        const response = await fetch('/api/documents/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Upload failed: ${response.statusText}`);
        }

        const data = await response.json();
        const docId = data.id || data.document_id;
        pollDocumentProgress(docId);
    } catch (err) {
        progressStatusText.innerText = `Error: ${err.message}`;
        progressStatusText.style.color = 'var(--accent-rose)';
    }
}

function pollDocumentProgress(docId) {
    const progressPercent = document.getElementById('progressPercent');
    const progressBarFill = document.getElementById('progressBarFill');
    const progressStatusText = document.getElementById('progressStatusText');

    const interval = setInterval(async () => {
        try {
            const res = await fetch(`/api/documents/${docId}`);
            if (!res.ok) return;

            const doc = await res.json();
            const pct = Math.round(doc.progress * 100);
            progressPercent.innerText = `${pct}%`;
            progressBarFill.style.width = `${pct}%`;

            if (doc.status === 'processing') {
                progressStatusText.innerText = 'Indexing multimodal contents, extracting keyframes, audio & tables...';
            } else if (doc.status === 'ready') {
                clearInterval(interval);
                progressStatusText.innerText = 'Ingestion complete! Added to this conversation.';
                setTimeout(() => {
                    document.getElementById('uploadProgressCard').classList.add('hidden');
                }, 2000);
                await refreshActiveDocuments();
            } else if (doc.status === 'failed') {
                clearInterval(interval);
                progressStatusText.innerText = `Ingestion failed: ${doc.error || 'Unknown error'}`;
                progressStatusText.style.color = 'var(--accent-rose)';
                await refreshActiveDocuments();
            }
        } catch (err) {
            console.error('Error polling document status:', err);
        }
    }, 700);
}

// ==========================================
// Query Submission & Chat Logic
// ==========================================

function initQueryForm() {
    const form = document.getElementById('queryForm');
    const input = document.getElementById('queryInput');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const queryText = input.value.trim();
        if (!queryText) return;

        input.value = '';
        await submitQuery(queryText);
    });
}

function useSampleQuery(text) {
    document.getElementById('queryInput').value = text;
    submitQuery(text);
}

async function submitQuery(queryText) {
    const messagesContainer = document.getElementById('messagesContainer');
    const providerSelect = document.getElementById('llmProviderSelect');

    // Hide welcome card if visible
    const welcomeCard = document.getElementById('welcomeCard');
    if (welcomeCard) welcomeCard.style.display = 'none';

    // Append User Message
    const promptIdx = trackedPrompts.length;
    const userBubble = document.createElement('div');
    userBubble.className = 'message-bubble user';
    userBubble.id = `prompt-bubble-${promptIdx}`;
    userBubble.innerHTML = `
        <div class="bubble-tag-row">
            <span class="prompt-index-chip">Prompt #${promptIdx + 1}</span>
        </div>
        <div class="bubble-content">${escapeHtml(queryText)}</div>
    `;
    messagesContainer.appendChild(userBubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Append Loading Assistant Bubble
    const assistantBubble = document.createElement('div');
    assistantBubble.className = 'message-bubble assistant';
    assistantBubble.innerHTML = `
        <div class="bubble-content">
            <span class="loading-pulse">⚡ Searching conversation vector partition & executing grounded QA...</span>
        </div>
    `;
    messagesContainer.appendChild(assistantBubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        const payload = {
            query: queryText,
            conversation_id: currentConversationId,
            llm_provider: providerSelect.value
        };

        const res = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            throw new Error(`Query failed: ${res.statusText}`);
        }

        const data = await res.json();
        currentConversationId = data.conversation_id;
        currentCitations = data.citations || [];

        renderAssistantResponse(assistantBubble, data);
        await loadConversationsList();

        // Refresh conversation messages for navigator
        const convRes = await fetch(`/api/conversations/${currentConversationId}`);
        if (convRes.ok) {
            const conv = await convRes.json();
            buildPromptNavigator(conv.messages || []);
        }
    } catch (err) {
        assistantBubble.querySelector('.bubble-content').innerText = `Error: ${err.message}`;
    }
}

function renderAssistantResponse(bubble, data) {
    let vBadge = '';
    if (data.verification) {
        const v = data.verification;
        const icon = v.status === 'supported' ? '🛡️ Verified' : (v.status === 'partial' ? '⚠️ Partial Evidence' : '❌ Unsupported');
        vBadge = `
            <div class="verification-badge ${v.status}">
                <span>${icon}</span>
                <span class="verification-reason">${escapeHtml(v.reasoning)}</span>
            </div>
        `;
    }

    const citationsHtml = (data.citations && data.citations.length > 0) ? `
        <div class="citations-wrapper">
            <div class="citations-header">Proof Citations & Multimodal Sources (${data.citations.length})</div>
            <div class="citations-grid">
                ${data.citations.map((c, i) => {
                    const type = c.content_type.toLowerCase();
                    let icon = '📄';
                    if (type === 'table') icon = '📊';
                    else if (type === 'video') icon = '🎬';
                    else if (type === 'audio') icon = '🎙️';
                    else if (type === 'figure' || type === 'image') icon = '🖼️';
                    else if (type.includes('attachment')) icon = '📎';

                    let timeBadge = '';
                    if (c.temporal_start !== null && c.temporal_start !== undefined) {
                        timeBadge = `<span class="time-pill">${c.temporal_start}s-${c.temporal_end}s</span>`;
                    }

                    return `
                        <button class="citation-chip ${type}" onclick="openCitationModal(${i})">
                            <span class="citation-type-tag">${icon} ${c.content_type.toUpperCase()}</span>
                            <span class="citation-page">p.${c.page_number}</span>
                            ${timeBadge}
                            <span class="citation-section">${escapeHtml(c.section || '')}</span>
                        </button>
                    `;
                }).join('')}
            </div>
        </div>
    ` : '';

    bubble.innerHTML = `
        ${vBadge}
        <div class="bubble-content formatted-answer">${formatAnswerMarkdown(data.answer)}</div>
        <div class="message-meta">
            <span>Retrieval: <strong class="latency-badge">${data.retrieval_latency_ms.toFixed(1)}ms</strong></span>
            <span>Total: <strong>${data.latency_ms.toFixed(0)}ms</strong></span>
            <span>Sources: <strong>${(data.citations || []).length}</strong></span>
        </div>
        ${citationsHtml}
    `;

    document.getElementById('messagesContainer').scrollTop = document.getElementById('messagesContainer').scrollHeight;
}

function openCitationModal(index) {
    const c = currentCitations[index];
    if (!c) return;

    const modalOverlay = document.getElementById('citationModalOverlay');
    const badge = document.getElementById('modalModalityBadge');
    const title = document.getElementById('modalCitationTitle');
    const body = document.getElementById('modalCitationBody');

    const type = c.content_type.toLowerCase();
    badge.innerText = `[${c.content_type.toUpperCase()}]`;
    badge.className = `modal-modality-badge ${type}`;
    title.innerText = `Source Proof: ${c.filename} (Page ${c.page_number})`;

    let mediaElement = '';
    if (type === 'video') {
        mediaElement = `
            <div class="media-preview-box">
                <h4>🎬 Video Timeline Segment (${c.temporal_start}s - ${c.temporal_end}s)</h4>
                <div class="video-container">
                    ${c.asset_path ? `<img src="${getAssetUrl(c.asset_path)}" class="media-frame-preview" alt="Video Keyframe">` : ''}
                    <div class="media-controls-mock">
                        <button class="playback-btn" onclick="alert('Seeking playback to ${c.temporal_start}s')">▶ Play from ${c.temporal_start}s</button>
                        <span class="timestamp-readout">Time Range: ${c.temporal_start}s - ${c.temporal_end}s</span>
                    </div>
                </div>
            </div>
        `;
    } else if (type === 'audio') {
        mediaElement = `
            <div class="media-preview-box">
                <h4>🎙️ Audio Recording Excerpt (${c.temporal_start}s - ${c.temporal_end}s)</h4>
                <div class="audio-container">
                    <div class="audio-wave-visual">
                        <div class="wave-bar"></div><div class="wave-bar active"></div><div class="wave-bar"></div>
                        <div class="wave-bar active"></div><div class="wave-bar"></div><div class="wave-bar"></div>
                    </div>
                    <div class="media-controls-mock">
                        <button class="playback-btn" onclick="alert('Playing audio from ${c.temporal_start}s')">🔊 Listen (${c.temporal_start}s)</button>
                        <span class="timestamp-readout">Transcript Window: ${c.temporal_start}s - ${c.temporal_end}s</span>
                    </div>
                </div>
            </div>
        `;
    } else if (type === 'figure' || type === 'image') {
        mediaElement = `
            <div class="media-preview-box">
                <h4>🖼️ Visual Chart & Diagram Asset</h4>
                ${c.asset_path ? `<img src="${getAssetUrl(c.asset_path)}" class="media-image-preview" alt="Figure Preview">` : ''}
            </div>
        `;
    }

    let bboxInfo = '';
    if (c.bbox) {
        bboxInfo = `
            <div class="meta-row">
                <strong>Spatial Bounding Box:</strong>
                <code>[${c.bbox.map(n => typeof n === 'number' ? n.toFixed(1) : n).join(', ')}]</code>
            </div>
        `;
    }

    body.innerHTML = `
        <div class="citation-meta-panel">
            <div class="meta-row"><strong>Document File:</strong> <span>${escapeHtml(c.filename)}</span></div>
            <div class="meta-row"><strong>Modality:</strong> <span class="modality-tag">${c.content_type.toUpperCase()}</span></div>
            <div class="meta-row"><strong>Page / Section:</strong> <span>Page ${c.page_number} ${c.section ? `• ${escapeHtml(c.section)}` : ''}</span></div>
            <div class="meta-row"><strong>Cosine Similarity:</strong> <span class="score-badge">${c.score.toFixed(4)}</span></div>
            ${bboxInfo}
        </div>
        ${mediaElement}
        <div class="context-snippet-box">
            <h4>Extracted Context & Evidence</h4>
            <pre class="snippet-content">${escapeHtml(c.snippet)}</pre>
        </div>
    `;

    modalOverlay.classList.remove('hidden');
}

function getAssetUrl(assetPath) {
    if (!assetPath) return '';
    const norm = assetPath.replace(/\\/g, '/');
    if (norm.includes('assets/')) {
        return '/assets/' + norm.split('assets/')[1];
    }
    return '/assets/' + norm;
}

function closeCitationModal() {
    document.getElementById('citationModalOverlay').classList.add('hidden');
}

function formatAnswerMarkdown(text) {
    if (!text) return '';
    let escaped = escapeHtml(text);
    // highlight source citations [S1], [S2]
    escaped = escaped.replace(/\[S(\d+)\]/g, '<span class="source-citation-badge">[S$1]</span>');
    // bold
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // newlines
    escaped = escaped.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
    return escaped;
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
