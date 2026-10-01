import os
from pathlib import Path
from dataclasses import dataclass, field


def _load_env_file():
    """
    Explicitly load environment variables from .env files located in
    project directories if not already defined in os.environ.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    candidates = [
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip()
                            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                                val = val[1:-1]
                            if key and (key not in os.environ or not os.environ[key]):
                                os.environ[key] = val
            except Exception:
                pass


_load_env_file()


@dataclass
class Settings:
    """
    Project NPN (Narrative, Proof, Numbers) Configuration Settings
    """
    # System Paths
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    DATA_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data")
    UPLOADS_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "uploads")
    ASSETS_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "assets")
    DB_PATH: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "npn_database.db")
    HISTORY_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "history")

    # Embedding Model Settings
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))
    QUERY_PREFIX: str = "Represent this sentence for searching relevant passages: "
    EMBED_BATCH_SIZE: int = 64

    # Search & Retrieval Settings
    BM25_K1: float = 1.5
    BM25_B: float = 0.75
    RRF_K: int = 60
    TOP_K_DENSE: int = 30
    TOP_K_SPARSE: int = 30
    TOP_K_FINAL: int = 6
    FINAL_TOP_K: int = 6
    RELEVANCE_DENSE_THRESHOLD: float = 0.30
    RELEVANCE_TERM_COVERAGE_THRESHOLD: float = 0.60
    RELEVANCE_COVERAGE_THRESHOLD: float = 0.60

    # LLM Settings
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "gemini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # Configurable Model Settings
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "hf.co/armand0e/Qwen3.5-9B-Opus-Agent-GGUF:Q5_K_M")
    OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Parsing Settings
    FONT_PROFILING_PAGES: int = 15
    HEADING_FONT_RATIO: float = 1.3
    TABLE_TRIAGE_MIN_CHARS: int = 40
    TABLE_TRIAGE_MIN_DIGIT_RATIO: float = 0.02

    def __post_init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        self.HISTORY_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
