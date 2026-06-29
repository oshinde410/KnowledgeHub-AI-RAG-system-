export type User = {
  id: string;
  email: string;
  role: string;
};

export type DocumentItem = {
  id: string;
  file_name: string;
  file_path?: string;
  file_type: string;
  file_size: number;
  status: string;
  uploaded_by?: string;
};

export type SourceItem = {
  document_name: string;
  document_id: string;
  score: number;
  text: string;
};

export type ChatResponse = {
  conversation_id: string;
  answer: string;
  sources: SourceItem[];
};

export type ChatMessage = {
  id: string;
  role: "USER" | "ASSISTANT";
  content: string;
  sources?: SourceItem[];
  createdAt: string;
};

export type LocalConversation = {
  id: string;
  title: string;
  updatedAt: string;
  messages: ChatMessage[];
};

export type DashboardMetrics = {
  total_documents: number;
  indexed_documents: number;
  failed_documents: number;
  total_chunks: number;
  total_conversations: number;
  processing_jobs: number;
  average_generation_ms: number;
  average_retrieval_ms: number;
};

export type ApiConversation = {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ApiMessage = {
  id: string;
  conversation_id: string;
  role: "USER" | "ASSISTANT";
  content: string;
  retrieved_sources?: SourceItem[];
  created_at: string;
};
