from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REDIS_URL: str = "redis://localhost:6379/0"

    # Helper: some dev setups can’t resolve Docker’s hostname `redis`.
    # If user overrides REDIS_URL to `redis://...` but the host isn’t resolvable,
    # we transparently fall back to localhost.
    def resolve_redis_url(self) -> str:
        url = self.REDIS_URL
        try:
            # simple heuristic: only handle redis hostnames
            if url.startswith("redis://redis") or url.startswith("rediss://redis"):
                import socket
                host = url.split("://", 1)[1].split(":", 1)[0]
                socket.gethostbyname(host)
                return url
        except Exception:
            # Fall back
            return url.replace("//redis:", "//localhost:")
        return url

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    MAX_UPLOAD_SIZE_BYTES: int = 20971520
    OLLAMA_MODEL: str = "qwen3:4b"

    # Groq (online)
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # Gemini (online) fallback
    GEMINI_API_KEY: str | None = None
    # Prefer a strong/fast default. You can override in .env via GEMINI_MODEL.
    GEMINI_MODEL: str = "gemini-2.5-flash"

    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"


    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,https://knowledge-hub-ai-rag-system.vercel.app"
    # Optional: prefer remote OpenAI embeddings when provided to avoid loading
    # heavy local ML libraries in the web process (helps stay under 512MB).
    OPENAI_API_KEY: str | None = None


    class Config:
        import os
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        # resolves to: backend/.env



settings = Settings()
settings.REDIS_URL = settings.resolve_redis_url()

