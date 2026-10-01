// Project NPN (Narrative, Proof, Numbers) Multimodal Frontend Engine

let currentConversationId = null;
let currentCitations = [];

document.addEventListener('DOMContentLoaded', () => {
    initDropZone();
    loadDocumentList();
    initQueryForm();
});

// Drop Zone & Upload logic supporting PDF, Video, Audio, Images, CSV, ZIP
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
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    const allowedExtensions = ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mov', '.avi', '.mp3', '.wav', '.csv', '.zip'];
    const fileName = file.name.toLowerCase();
    const isAllowed = allowedExtensions.some(ext => fileName.endsWith(ext));

    if (!isAllowed) {
        alert('Unsupported format. Please upload PDF, Video, Audio, Image, CSV, or ZIP files.');
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
    progressStatusText.innerText = `Uploading ${file.name}...`;
    progressCard.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

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

        // Poll document status until ready or failed
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
                progressStatusText.innerText = 'Ingestion complete! All modalities indexed & ready.';
                setTimeout(() => {
                    document.getElementById('uploadProgressCard').classList.add('hidden');
                }, 2500);
                loadDocumentList();
            } else if (doc.status === 'failed') {
                clearInterval(interval);
                progressStatusText.innerText = `Ingestion failed: ${doc.error || 'Unknown error'}`;
                progressStatusText.style.color = 'var(--accent-rose)';
                loadDocumentList();
            }
        } catch (err) {
            console.error('Error polling document status:', err);
        }
    }, 800);
}

async function loadDocumentList() {
    const docsList = document.getElementById('documentsList');
    const docCountBadge = document.getElementById('docCountBadge');

    try {
        const res = await fetch('/api/documents');
        if (!res.ok) return;

        const docs = await res.json();
        docCountBadge.innerText = docs.length;

        if (docs.length === 0) {
            docsList.innerHTML = '<div class="empty-docs">No documents ingested yet</div>';
            return;
        }

        docsList.innerHTML = docs.map(d => {
            const ext = d.filename.split('.').pop().toLowerCase();
            let icon = '📄';
            if (['mp4', 'mov', 'avi'].includes(ext)) icon = '🎬';
            else if (['mp3', 'wav', 'm4a'].includes(ext)) icon = '🎙️';
            else if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) icon = '🖼️';
            else if (['csv', 'xlsx'].includes(ext)) icon = '📊';
            else if (['zip'].includes(ext)) icon = '📦';

            return `
                <div class="doc-item">
                    <span class="doc-name" title="${escapeHtml(d.filename)}">${icon} ${escapeHtml(d.filename)}</span>
                    <span class="status-badge ${d.status}">${d.status}</span>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Error loading documents:', err);
    }
}

// Query Submission & Chat Logic
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
    const welcomeCard = document.querySelector('.welcome-card');
    if (welcomeCard) welcomeCard.style.display = 'none';

    // Append User Message
    const userBubble = document.createElement('div');
    userBubble.className = 'message-bubble user';
    userBubble.innerHTML = `
        <div class="bubble-content">${escapeHtml(queryText)}</div>
    `;
    messagesContainer.appendChild(userBubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Append Loading Assistant Bubble
    const assistantBubble = document.createElement('div');
    assistantBubble.className = 'message-bubble assistant';
    assistantBubble.innerHTML = `
        <div class="bubble-content">
            <span class="loading-pulse">⚡ Searching hybrid vector space across text, tables, figures, video & audio...</span>
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
                        <div class="wave-bar active"></div><div class="wave-bar"></div><div class="wave-bar active"></div>
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
