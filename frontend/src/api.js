/**
 * API client for RAG chatbot backend
 */

const API_BASE = '/api';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// Folder Management
// ============================================================================

export async function addFolder(path) {
  return fetchAPI('/folders/add', {
    method: 'POST',
    body: JSON.stringify({ path }),
  });
}

export async function removeFolder(path) {
  return fetchAPI('/folders/remove', {
    method: 'DELETE',
    body: JSON.stringify({ path }),
  });
}

export async function listFolders() {
  return fetchAPI('/folders/list');
}

export async function listFolderFiles(path) {
  return fetchAPI('/folders/files', {
    method: 'POST',
    body: JSON.stringify({ path }),
  });
}

// ============================================================================
// Document Processing
// ============================================================================

export async function startProcessing() {
  return fetchAPI('/process/start', {
    method: 'POST',
  });
}

export async function getProcessingStatus() {
  return fetchAPI('/process/status');
}

/**
 * Connect to processing WebSocket for real-time updates
 */
export function connectProcessingStream(onMessage, onError) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${window.location.host}/api/process/stream`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError?.(error);
  };

  ws.onclose = () => {
    console.log('WebSocket closed');
  };

  return ws;
}

// ============================================================================
// Conversations
// ============================================================================

export async function createConversation(title = null) {
  return fetchAPI('/conversations/create', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export async function listConversations() {
  return fetchAPI('/conversations/list');
}

export async function getConversation(conversationId) {
  return fetchAPI(`/conversations/${conversationId}`);
}

export async function deleteConversation(conversationId) {
  return fetchAPI(`/conversations/${conversationId}`, {
    method: 'DELETE',
  });
}

// ============================================================================
// Query
// ============================================================================

export async function submitQuery(conversationId, question) {
  return fetchAPI('/query', {
    method: 'POST',
    body: JSON.stringify({
      conversation_id: conversationId,
      question,
    }),
  });
}

// ============================================================================
// Health Check
// ============================================================================

export async function checkHealth() {
  return fetchAPI('/health');
}

// ============================================================================
// Admin
// ============================================================================

export async function clearAllData() {
  return fetchAPI('/admin/clear-all-data', {
    method: 'POST',
  });
}

// ============================================================================
// Files
// ============================================================================

export async function openFolder(path) {
  return fetchAPI('/files/open-folder', {
    method: 'POST',
    body: JSON.stringify({ path }),
  });
}
