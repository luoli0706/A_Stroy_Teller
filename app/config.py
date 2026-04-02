import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- 基础路径配置 ---
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / ".data"
DATA_DIR.mkdir(exist_ok=True)

# 角色与记忆存储
ROLE_DIR = BASE_DIR / "role"
MEMORY_DIR = BASE_DIR / "memory"
STORIES_DIR = BASE_DIR / "stories"

# 日志与导出
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
OPT_DIR = BASE_DIR / "opt"
OPT_STORIES_DIR = OPT_DIR / "stories"
OPT_STORIES_DIR.mkdir(parents=True, exist_ok=True)

# 数据库路径
SQLITE_DB_PATH = DATA_DIR / "story_teller.db"
CHROMA_DIR = DATA_DIR / "rag_chroma"

# --- 模型服务配置 (Ollama) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

# 模型选型
MODEL_PLANNER = os.getenv("OLLAMA_MODEL_PLANNER", "qwen3.5:9b")
MODEL_ROLE = os.getenv("OLLAMA_MODEL_ROLE", "qwen3.5:9b")
MODEL_INTEGRATOR = os.getenv("OLLAMA_MODEL_INTEGRATOR", "qwen3.5:9b")
MODEL_QUALITY = os.getenv("OLLAMA_MODEL_QUALITY", MODEL_INTEGRATOR)
MODEL_EMBEDDING = os.getenv("OLLAMA_MODEL_EMBEDDING", "nomic-embed-text-v2-moe")

# 生成参数
DEFAULT_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
MAX_RETRY = int(os.getenv("MAX_RETRY", "1"))

# --- RAG 检索配置 ---
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() in ("true", "1", "yes")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "story_memory_slices")

# --- UI 配置 ---
DEFAULT_STORY_ID = "urban_detective"
DEFAULT_LANG = os.getenv("APP_LANG", "zh")
