import type {
  ApiConversation,
  ApiMessage,
  ChatResponse,
  DashboardMetrics,
  DocumentItem,
  SourceItem,
  User
} from "./types";

const DEFAULT_API_URL = import.meta.env.PROD
  ? "https://knowledgehub-ai-rag-system.onrender.com"
  : "http://127.0.0.1:8000";

const API_URL = (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/$/, "");

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("kh_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...authHeaders(),
      ...(options.headers as Record<string, string> | undefined)
    }
  });

  if (!response.ok) {
    const fallback = `Request failed with ${response.status}`;
    try {
      const data = await response.json();
      throw new Error(data.detail ?? data.message ?? fallback);
    } catch (error) {
      if (error instanceof Error && error.message !== fallback) throw error;
      throw new Error(fallback);
    }
  }

  return response.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  return request<{ access_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function register(email: string, password: string, fullName: string) {
  return request<{ message: string; user_id: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName })
  });
}

export async function getMe() {
  return request<User>("/me");
}

export async function getDocuments(query = "") {
  const path = query.trim()
    ? `/documents/search?q=${encodeURIComponent(query.trim())}`
    : "/documents";
  return request<DocumentItem[]>(path);
}

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return request<{ message: string; document_id: string }>("/documents/upload", {
    method: "POST",
    body: formData
  });
}

export async function deleteDocument(documentId: string) {
  return request<{ message: string; document_id: string }>(`/documents/${documentId}`, {
    method: "DELETE"
  });
}

export async function getDashboardMetrics() {
  return request<DashboardMetrics>("/dashboard/metrics");
}

export async function getConversations() {
  return request<ApiConversation[]>("/chat/conversations");
}

export async function getMessages(conversationId: string) {
  return request<ApiMessage[]>(`/chat/conversations/${conversationId}/messages`);
}

export async function askQuestion(question: string, conversationId: string | null | undefined, sessionId: string | null | undefined) {
  return request<ChatResponse>("/chat/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      conversation_id: conversationId ?? null,
      session_id: sessionId ?? null
    })
  });
}

export async function createChatSession() {
  return request<{ session_id: string }>("/chat/session", {
    method: "POST"
  });
}

export async function deleteChatSession(sessionId: string) {
  return request<{ message: string; session_id: string }>(`/chat/session/${sessionId}` as string, {
    method: "DELETE"
  });
}

// Upload a PDF that will be associated with the temporary chat session.
// Requires backend support for session_id scoping.
export async function uploadChatDocument(file: File, sessionId: string) {
  const formData = new FormData();
  formData.append("file", file);
  return request<{ message: string; document_id: string }>(`/documents/upload?session_id=${encodeURIComponent(sessionId)}`, {
    method: "POST",
    body: formData
  });
}


export async function semanticSearch(query: string) {
  return request<SourceItem[]>(`/search?query=${encodeURIComponent(query)}`);
}

export function websocketUrl() {
  const configured = import.meta.env.VITE_WS_URL;
  const token = localStorage.getItem("kh_token");
  const suffix = token ? `?token=${encodeURIComponent(token)}` : "";
  
  if (configured && token) {
    return `${configured}${configured.includes("?") ? "&" : "?"}${suffix.slice(1)}`;
  }
  if (configured) return configured;
  
  // In production, use the Render backend; in dev, use relative URL
  let baseUrl = API_URL;
  if (import.meta.env.PROD && !import.meta.env.VITE_WS_URL) {
    baseUrl = "https://knowledgehub-ai-rag-system.onrender.com";
  } else if (!import.meta.env.PROD && !import.meta.env.VITE_WS_URL) {
    baseUrl = window.location.origin;
  }
  
  const protocol = baseUrl.startsWith("https") ? "wss:" : "ws:";
  const host = baseUrl.replace(/^https?:\/\//, "");
  return `${protocol}//${host}/ws/chat${suffix}`;
}
