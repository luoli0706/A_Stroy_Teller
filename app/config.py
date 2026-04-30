import os
from pathlib import Path
from dotenv import load_dotenv

_config_initialized = False


def init_config() -> None:
    """显式初始化配置（加载 .env 并创建必要目录）。

    调用方在应用入口处显式调用此函数，避免模块导入时产生副作用。
    幂等：多次调用仅生效一次。
    """
    global _config_initialized
    if _config_initialized:
        return
    load_dotenv()
    DATA_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    OPT_STORIES_DIR.mkdir(parents=True, exist_ok=True)
    _config_initialized = True


# --- 基础路径配置 ---
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / ".data"

# 角色与记忆存储
ROLE_DIR = BASE_DIR / "role"
MEMORY_DIR = BASE_DIR / "memory"
STORIES_DIR = BASE_DIR / "stories"

# 日志与导出
LOG_DIR = BASE_DIR / "logs"
OPT_DIR = BASE_DIR / "opt"
OPT_STORIES_DIR = OPT_DIR / "stories"

# 既定事实与向量库
SQLITE_DB_PATH = DATA_DIR / "story_teller.db"
CHECKPOINT_DB_PATH = DATA_DIR / "checkpoints.db"
METADATA_DB_PATH = DATA_DIR / "metadata.db"
CHROMA_DIR = DATA_DIR / "rag_chroma"

# --- Provider 选择 ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")          # ollama | openai | anthropic
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "")    # 空则跟随 LLM_PROVIDER（anthropic 回退 ollama）

# --- Ollama 配置 (向下兼容) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL_PLANNER = os.getenv("OLLAMA_MODEL_PLANNER", "qwen3.5:9b")
OLLAMA_MODEL_ROLE = os.getenv("OLLAMA_MODEL_ROLE", "qwen3.5:9b")
OLLAMA_MODEL_INTEGRATOR = os.getenv("OLLAMA_MODEL_INTEGRATOR", "qwen3.5:9b")
OLLAMA_MODEL_QUALITY = os.getenv("OLLAMA_MODEL_QUALITY", "")    # 空则跟随 INTEGRATOR
OLLAMA_MODEL_EMBEDDING = os.getenv("OLLAMA_MODEL_EMBEDDING", "nomic-embed-text-v2-moe")

# --- OpenAI 配置 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL_PLANNER = os.getenv("OPENAI_MODEL_PLANNER", "gpt-4o")
OPENAI_MODEL_ROLE = os.getenv("OPENAI_MODEL_ROLE", "gpt-4o")
OPENAI_MODEL_INTEGRATOR = os.getenv("OPENAI_MODEL_INTEGRATOR", "gpt-4o")
OPENAI_MODEL_QUALITY = os.getenv("OPENAI_MODEL_QUALITY", "")
OPENAI_MODEL_EMBEDDING = os.getenv("OPENAI_MODEL_EMBEDDING", "text-embedding-3-small")

# --- Anthropic 配置 ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL_PLANNER = os.getenv("ANTHROPIC_MODEL_PLANNER", "claude-sonnet-4-20250514")
ANTHROPIC_MODEL_ROLE = os.getenv("ANTHROPIC_MODEL_ROLE", "claude-sonnet-4-20250514")
ANTHROPIC_MODEL_INTEGRATOR = os.getenv("ANTHROPIC_MODEL_INTEGRATOR", "claude-sonnet-4-20250514")
ANTHROPIC_MODEL_QUALITY = os.getenv("ANTHROPIC_MODEL_QUALITY", "")

# --- 生成参数 ---
DEFAULT_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
MAX_RETRY = int(os.getenv("MAX_RETRY", "1"))
LLM_REQUEST_RETRY = int(os.getenv("LLM_REQUEST_RETRY", "3"))

# --- RAG 检索配置 ---
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() in ("true", "1", "yes")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "story_memory_slices")

# --- UI 配置 ---
DEFAULT_STORY_ID = "urban_detective"
DEFAULT_LANG = os.getenv("APP_LANG", "zh")


def get_effective_model_config() -> dict:
    """根据 LLM_PROVIDER 返回实际使用的模型名称映射。"""
    provider = LLM_PROVIDER.lower()

    if provider == "openai":
        return {
            "provider": "openai",
            "planner": OPENAI_MODEL_PLANNER,
            "role": OPENAI_MODEL_ROLE,
            "integrator": OPENAI_MODEL_INTEGRATOR,
            "quality": OPENAI_MODEL_QUALITY or OPENAI_MODEL_INTEGRATOR,
            "embedding": OPENAI_MODEL_EMBEDDING,
        }

    if provider == "anthropic":
        return {
            "provider": "anthropic",
            "planner": ANTHROPIC_MODEL_PLANNER,
            "role": ANTHROPIC_MODEL_ROLE,
            "integrator": ANTHROPIC_MODEL_INTEGRATOR,
            "quality": ANTHROPIC_MODEL_QUALITY or ANTHROPIC_MODEL_INTEGRATOR,
            "embedding": "",  # Anthropic 无 embedding API
        }

    # 默认 ollama (向下兼容)
    return {
        "provider": "ollama",
        "planner": OLLAMA_MODEL_PLANNER,
        "role": OLLAMA_MODEL_ROLE,
        "integrator": OLLAMA_MODEL_INTEGRATOR,
        "quality": OLLAMA_MODEL_QUALITY or OLLAMA_MODEL_INTEGRATOR,
        "embedding": OLLAMA_MODEL_EMBEDDING,
    }


def resolve_embedding_provider() -> str:
    """解析实际使用的 Embedding Provider。

    Anthropic 无 embedding API，自动回退到 ollama。
    """
    if EMBEDDING_PROVIDER:
        return EMBEDDING_PROVIDER.lower()

    llm = LLM_PROVIDER.lower()
    if llm == "anthropic":
        return "ollama"     # Anthropic 无 embedding，回退 Ollama
    if llm == "openai":
        return "openai"     # OpenAI 有原生 embedding
    return "ollama"
