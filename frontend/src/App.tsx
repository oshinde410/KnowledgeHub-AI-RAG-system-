import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  askQuestion,
  deleteDocument,
  getDashboardMetrics,
  getDocuments,
  getMe,
  login,
  register,
  semanticSearch,
  websocketUrl,
  createChatSession,
  deleteChatSession,
  uploadChatDocument
} from "./api";
import type { ChatMessage, DashboardMetrics, DocumentItem, SourceItem, User } from "./types";

function uid() {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
}

function formatBytes(bytes = 0) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function prettyStatus(status?: string) {
  return (status || "UNKNOWN").replaceAll("_", " ").toLowerCase();
}

type LocalChat = { id: string; title: string; messages: ChatMessage[] };

export default function App() {

  const [token, setToken] = useState(localStorage.getItem("kh_token") ?? "");
  const [user, setUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authError, setAuthError] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [activeTab, setActiveTab] = useState<"documents" | "chat">("chat");

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [documentQuery, setDocumentQuery] = useState("");
  const [uploadState, setUploadState] = useState("");
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SourceItem[]>([]);
  const [searchBusy, setSearchBusy] = useState(false);

  // ChatGPT-like session (per page) + per-chat conversation list (in-memory only)
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatConversations, setChatConversations] = useState<LocalChat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const activeChat = chatConversations.find((c) => c.id === activeChatId) ?? null;

  const [question, setQuestion] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const streaming = true; // Always stream in chat UI.


  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const chatFileInputRef = useRef<HTMLInputElement | null>(null);

  const [chatDocumentNames, setChatDocumentNames] = useState<string[]>([]);

  const totalChunks = useMemo(() => {
    return metrics?.total_chunks ?? documents.filter((doc) => doc.status === "INDEXED").length * 5;
  }, [documents, metrics]);

  useEffect(() => {
    if (!token) return;
    getMe()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("kh_token");
        setToken("");
      });
  }, [token]);

  useEffect(() => {
    if (!token) return;
    void refreshDocuments();
    void refreshMetrics();
  }, [token]);

  // Create backend session for temporary docs/chats and hard-delete on exit.
  useEffect(() => {
    if (!token) return;

    let mounted = true;

    (async () => {
      try {
        const res = await createChatSession();
        if (!mounted) return;
        setSessionId(res.session_id);
      } catch {
        // ignore
      }

      // Initialize with one chat and auto-select it (only first time per page load).
      const initialId = uid();
      setChatConversations([{ id: initialId, title: "New chat", messages: [] }]);
      setActiveChatId(initialId);
    })();

    const handleBeforeUnload = () => {
      if (!sessionId) return;
      void deleteChatSession(sessionId);
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      mounted = false;
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Keep selection stable after initial load; don't auto-pick when user switches chats.


  async function refreshDocuments(query = documentQuery) {
    setIsLoadingDocs(true);
    try {
      setDocuments(await getDocuments(query));
    } finally {
      setIsLoadingDocs(false);
    }
  }

  async function refreshMetrics() {
    try {
      setMetrics(await getDashboardMetrics());
    } catch {
      setMetrics(null);
    }
  }

  function ensureActiveChat() {
    if (activeChatId) return;
    const newId = uid();
    setChatConversations([{ id: newId, title: "New chat", messages: [] }]);
    setActiveChatId(newId);
  }

  function upsertLocalChat(chatId: string, updater: (prev: LocalChat) => LocalChat) {
    setChatConversations((current) => current.map((c) => (c.id === chatId ? updater(c) : c)));
  }

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || chatBusy) return;

    ensureActiveChat();
    setQuestion("");
    setChatBusy(true);

    const currentChatId = activeChatId ?? chatConversations[0]?.id ?? null;
    if (!currentChatId) return;

    // const userMessage: ChatMessage = {
    //   id: uid(),
    //   role: "USER",
    //   content: trimmed,
    //   createdAt: new Date().toISOString()
    // };

    // upsertLocalChat(currentChatId, (prev) => ({
    //   ...prev,
    //   title: prev.title === "New chat" ? trimmed.slice(0, 42) : prev.title,
    //   messages: [...prev.messages, userMessage]
    // }));

    const userMessage: ChatMessage = {
      id: uid(),
      role: "USER",
      content: trimmed,
      createdAt: new Date().toISOString()
    };

    const assistantMessageId = uid();

    upsertLocalChat(currentChatId, (prev) => ({
      ...prev,
      title: prev.title === "New chat" ? trimmed.slice(0, 42) : prev.title,
      messages: [
        ...prev.messages,
        userMessage,
        {
          id: assistantMessageId,
          role: "ASSISTANT",
          content: "",
          sources: [],
          createdAt: new Date().toISOString()
        }
      ]
    }));

    try {
      const result = streaming
        ? await askWithWebSocket(trimmed, currentChatId, assistantMessageId)
        : await askQuestion(trimmed, currentChatId, sessionId);

      if (!streaming) {
        upsertLocalChat(currentChatId, (prev) => ({
          ...prev,
          messages: [
            ...prev.messages,
            {
              id: uid(),
              role: "ASSISTANT",
              content: (result as any).answer,
              sources: (result as any).sources,
              createdAt: new Date().toISOString()
            }
          ]
        }));
      }

      void refreshMetrics();
    } catch (error) {
      upsertLocalChat(currentChatId, (prev) => ({
        ...prev,
        messages: [
          ...prev.messages,
          {
            id: uid(),
            role: "ASSISTANT",
            content: error instanceof Error ? error.message : "The assistant could not answer.",
            sources: [],
            createdAt: new Date().toISOString()
          }
        ]
      }));
    } finally {
      setChatBusy(false);
    }
  }

  async function askWithWebSocket(trimmed: string, chatId: string, assistantMessageId: string) {
    return new Promise<void>((resolve, reject) => {
      const socket = new WebSocket(websocketUrl());
      let answer = "";
      let sources: SourceItem[] = [];

      socket.onopen = () =>
        socket.send(
          JSON.stringify({
            question: trimmed,
            conversation_id: chatId,
            session_id: sessionId
          })
        );

      socket.onerror = () => reject(new Error("WebSocket connection failed."));

      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === "token") {
          answer += payload.content ?? "";

          upsertLocalChat(chatId, (prev) => {
            return {
              ...prev,
              messages: prev.messages.map((m) =>
                m.id === assistantMessageId
                  ? { ...m, content: answer, sources }
                  : m
              )
            };
          });
        }

        if (payload.type === "error") reject(new Error(payload.message));

        if (payload.type === "done") {
          answer = payload.answer ?? answer;
          sources = payload.sources ?? [];

          upsertLocalChat(chatId, (prev) => ({
            ...prev,
            messages: prev.messages.map((m) =>
              m.id === assistantMessageId
                ? { ...m, content: answer, sources }
                : m
            )
          }));
          socket.close();
          resolve();
        }
      };
    });
  }

  async function handleDeleteDocument(documentId: string) {
    const confirmed = window.confirm("Delete this document and its vector index entries?");
    if (!confirmed) return;
    await deleteDocument(documentId);
    await refreshDocuments("");
    await refreshMetrics();
  }

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError("");

    const data = new FormData(event.currentTarget);
    const email = String(data.get("email") ?? "");
    const password = String(data.get("password") ?? "");
    const fullName = String(data.get("fullName") ?? "");

    try {
      if (authMode === "register") {
        await register(email, password, fullName || email.split("@")[0]);
      }
      const result = await login(email, password);
      localStorage.setItem("kh_token", result.access_token);
      setToken(result.access_token);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed");
    }
  }

  function logout() {
    localStorage.removeItem("kh_token");
    setToken("");
    setUser(null);
  }

  async function handleSemanticSearch(event: FormEvent) {
    event.preventDefault();
    if (!searchQuery.trim()) return;
    setSearchBusy(true);
    try {
      setSearchResults(await semanticSearch(searchQuery));
    } finally {
      setSearchBusy(false);
    }
  }

  function createNewChat() {
    const id = uid();
    setChatConversations((current) => [{ id, title: "New chat", messages: [] }, ...current]);
    setActiveChatId(id);
    setChatDocumentNames([]);
  }

  async function handleChatUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !sessionId) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadState("Only PDF is supported for chat attachments.");
      return;
    }

    setUploadState(`Uploading ${file.name}...`);
    try {
      await uploadChatDocument(file, sessionId);
      setUploadState("Upload successful. Processing started.");
      setChatDocumentNames((prev) => (prev.includes(file.name) ? prev : [...prev, file.name]));
    } catch (e) {
      setUploadState(e instanceof Error ? e.message : "Upload failed");
    } finally {
      event.target.value = "";
    }
  }

  if (!token) {
    return (
      <main className="auth-page">
        <section className="auth-hero">
          <p className="eyebrow">Enterprise RAG Support</p>
          <h1>KnowledgeHub AI</h1>
          <p>
            Upload internal documents, retrieve grounded source context, and draft support replies from your company knowledge base.
          </p>
        </section>
        <form className="auth-panel" onSubmit={handleAuth}>
          <div>
            <p className="eyebrow">{authMode === "login" ? "Welcome back" : "Create workspace user"}</p>
            <h2>{authMode === "login" ? "Sign in" : "Register"}</h2>
          </div>
          {authMode === "register" && <input name="fullName" placeholder="Full name" />}
          <input name="email" type="email" placeholder="Email" required />
          <input name="password" type="password" placeholder="Password" required />
          {authError && <p className="error">{authError}</p>}
          <button className="primary" type="submit">
            {authMode === "login" ? "Log in" : "Create account"}
          </button>
          <button
            className="text-button"
            type="button"
            onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}
          >
            {authMode === "login" ? "Need an account? Register" : "Already registered? Log in"}
          </button>
        </form>
      </main>
    );
  }

  return (
    <div className={`app-shell ${theme}`}>
      <header className="topbar">
        <div className="brand">
          <p className="eyebrow">KnowledgeHub</p>
          <h1>Support Agent</h1>
        </div>
        <nav className="topnav">
          {(["chat", "documents"] as const).map((tab) => ( 
            <button
              key={tab}
              className={activeTab === tab ? "active" : ""}
              onClick={() => setActiveTab(tab)}
              type="button"
            >
              {tab}
            </button>
          ))}
        </nav>
        <div className="top-actions">
          <button
            className="theme-toggle"
            onClick={() =>
              setTheme(theme === "light" ? "dark" : "light")
            }
          >
            {theme === "light" ? "🌙" : "☀️"}
          </button>

          <ProfileMenu
            email={user?.email}
            onLogout={logout}
          />
        </div>
      </header>


      <main className="workspace">

        {activeTab === "documents" && (
          <section className="view">

            <header className="view-header">
              <div>
                <p className="eyebrow">Operations</p>
                <h2>Dashboard</h2>
              </div>
              <button className="secondary" type="button" onClick={() => refreshDocuments("")}>
                Refresh
              </button>
            </header>
            <div className="metric-grid">
              <Metric label="Documents" value={metrics?.total_documents ?? documents.length} />
              <Metric
                label="Indexed"
                value={metrics?.indexed_documents ?? documents.filter((doc) => doc.status === "INDEXED").length}
              />
              <Metric label="Conversations" value={metrics?.total_conversations ?? 0} />
              <Metric label="Est. chunks" value={totalChunks} />
            </div>
            <section className="panel">
              <h3>Processing jobs</h3>
              <div className="job-list">
                {documents.slice(0, 6).map((doc) => (
                  <div className="job-row" key={doc.id}>
                    <span>{doc.file_name}</span>
                    <Status value={doc.status} />
                  </div>
                ))}
                {!documents.length && <p className="muted">Upload documents to populate ingestion status.</p>}
              </div>
            </section>
          </section>
        )}

        {activeTab === "documents" && (
          <section className="view">
            <header className="view-header">
              <div>
                <p className="eyebrow">Knowledge base</p>
                <h2>Documents</h2>
              </div>
              <form
                className="search-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void refreshDocuments();
                }}
              >
                <input value={documentQuery} onChange={(event) => setDocumentQuery(event.target.value)} placeholder="Search files" />
                <button className="secondary" type="submit">
                  Search
                </button>
              </form>
            </header>
            <div className="panel">
              <p className="muted">Global documents are managed here. Chat attachments are per-session inside the Chat tab.</p>
            </div>
            <DocumentTable documents={documents} loading={isLoadingDocs} onDelete={handleDeleteDocument} />
          </section>
        )}

        {false && ( /* search tab removed (UI only) */
          <section className="view">
            <header className="view-header">
              <div>
                <p className="eyebrow">Retrieval</p>
                <h2>Semantic search</h2>
              </div>
              <form className="search-form" onSubmit={handleSemanticSearch}>
                <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Search knowledge chunks" />
                <button className="secondary" type="submit">
                  {searchBusy ? "Searching" : "Search"}
                </button>
              </form>
            </header>
            <Sources sources={searchResults} />
            {!searchResults.length && <p className="muted">Top-K chunks and similarity scores will appear here.</p>}
          </section>
        )}

        {activeTab === "chat" && (
          <section className="chat-layout">
            <aside className="conversation-list">
              <div className="chat-list-top">
                <button className="primary" type="button" onClick={createNewChat}>
                  New conversation
                </button>
                <span className="chat-list-title"></span>
              </div>

              {chatConversations.map((conversation) => (
                <button
                  type="button"
                  className={conversation.id === activeChatId ? "conversation active" : "conversation"}
                  key={conversation.id}
                  onClick={() => setActiveChatId(conversation.id)}
                >
                  <strong>{conversation.title}</strong>
                  <span>{conversation.messages.length} messages</span>
                </button>
              ))}


            </aside>

            <section className="chat-panel">
              <header className="chat-header">
                <div>
                  <p className="eyebrow">Grounded assistant</p>
                  <h2>{activeChat?.title ?? "Chat"}</h2>
                </div>

              </header>

              <div className="messages">
                {(activeChat?.messages ?? []).map((message) => (
                  <article key={message.id} className={`message ${message.role.toLowerCase()}`}>
                    <p>{message.content}</p>
                    {!!message.sources?.length && <Sources sources={message.sources} />}
                  </article>
                ))}
                {!(activeChat?.messages ?? []).length && (
                  <div className="empty-state">Ask anything. Attach PDFs in this chat to ground answers.</div>
                )}
              </div>

              {chatDocumentNames.length > 0 && (
                <div className="chat-attachments" aria-label="Chat attachments">
                  <span className="chat-attachments-label">Attached</span>
                  <div className="chat-attachments-list">
                    {chatDocumentNames.map((name) => (
                      <span key={name} className="chat-attachment-pill" title={name}>
                        <span className="chat-attachment-icon" aria-hidden="true">
                          📄
                        </span>
                        <span className="chat-attachment-name">
                          {name}
                        </span>
                        <button
                          type="button"
                          className="chat-attachment-remove"
                          aria-label={`Remove ${name}`}
                          onClick={() => setChatDocumentNames((prev) => prev.filter((n) => n !== name))}
                        >
                          x
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <form className="composer" onSubmit={handleAsk}>
                <input
                  ref={chatFileInputRef}
                  hidden
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={handleChatUpload}
                />

                <div className="composer-left">
                  <button
                    className="composer-attach-button"
                    type="button"
                    onClick={() => chatFileInputRef.current?.click()}
                    disabled={chatBusy}
                    title="Attach PDF"
                  >
                    +
                  </button>

                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Ask a question..."
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        const form = event.currentTarget.form;
                        if (form) {
                          form.requestSubmit();
                        }
                      }
                    }}
                  />
                </div>
                <button className="primary" disabled={chatBusy} type="submit">
                  {chatBusy ? ("Thinking") : ("send")}
                </button>
              </form>
            </section>
          </section>
        )}
      </main>
    </div>
  );

}

function ProfileMenu({
  email,
  onLogout
}: {
  email?: string | null;
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;

    const onMouseDown = (event: MouseEvent) => {
      const el = boxRef.current;
      if (!el) return;
      if (event.target instanceof Node && !el.contains(event.target)) {
        setOpen(false);
      }
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };

    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div className="profile" ref={boxRef}>
      <button
        type="button"
        className="profile-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {typeof email === "string" && email.length ? email.slice(0, 1).toUpperCase() : "U"}
      </button>

      {open && (
        <div className="profile-menu" role="menu">
          <div className="profile-meta">
            <strong className="profile-name">{email ?? "Signed in"}</strong>
          </div>
          <button type="button" className="profile-logout" onClick={onLogout}>
            Log out
          </button>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {

  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Status({ value }: { value: string }) {
  return <span className={`status ${prettyStatus(value)}`}>{prettyStatus(value)}</span>;
}

function DocumentTable({
  documents,
  loading,
  onDelete
}: {
  documents: DocumentItem[];
  loading: boolean;
  onDelete: (documentId: string) => void;
}) {
  return (
    <section className="panel table-panel">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Size</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <tr key={doc.id}>
              <td>{doc.file_name}</td>
              <td>{doc.file_type}</td>
              <td>{formatBytes(doc.file_size)}</td>
              <td>
                <Status value={doc.status} />
              </td>
              <td>
                <button className="ghost" onClick={() => onDelete(doc.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!documents.length && <p className="muted">{loading ? "Loading documents..." : "No documents found."}</p>}
    </section>
  );
}

// function Sources({ sources }: { sources: SourceItem[] }) {
//   return (
//     <div className="sources">
//       {sources.map((source, index) => (
//         <details key={`${source.document_id}-${index}`} open={index === 0}>
//           <summary>
//             <span>Source {index + 1}</span>
//             <small>{Math.round((source.score ?? 0) * 100)}% match</small>
//           </summary>
//           <p>{source.text}</p>
//           <code>{source.document_id}</code>
//         </details>
//       ))}
//     </div>
//   );
// }

// function Sources({ sources }: { sources: SourceItem[] }) {
//   if (!sources.length) return null;

//   return (
//     <div className="sources">
//       -Source:
//       <div className="source-document">
//         {sources[0].document_id}
//       </div>
//     </div>
//   );
// }

function Sources({ sources }: { sources: SourceItem[] }) {
  if (!sources.length) return null;

  return (
    <div className="sources">
     <div>Source:</div> 
      <div>- {sources[0].document_name}</div>
    </div>
  );
}