"""
Stainless Steel Server配置文件
"""
import os
from pathlib import Path

# ==================== 服务器配置 ====================
SERVER_HOST = os.getenv("STAINLESS_STEEL_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("STAINLESS_STEEL_SERVER_PORT", "50009"))
LOG_LEVEL = os.getenv("STAINLESS_STEEL_LOG_LEVEL", "INFO")

# ==================== LLM API配置 ====================
LLM_API_TIMEOUT = int(os.getenv("STAINLESS_STEEL_LLM_TIMEOUT", "300"))  # 5分钟超时
LLM_MAX_RETRIES = int(os.getenv("STAINLESS_STEEL_LLM_MAX_RETRIES", "3"))

# ==================== 并行处理配置 ====================
MAX_WORKERS = int(os.getenv("STAINLESS_STEEL_MAX_WORKERS", "20"))  # 并行处理文献的最大线程数

# ==================== 路径配置 ====================
# Stainless Steel数据库路径（指向实际数据位置）
STAINLESS_STEEL_BASE_DIR = Path("/home/knowledge_base_data/database/stainless-steel")
STAINLESS_STEEL_DATABASE_DIR = STAINLESS_STEEL_BASE_DIR
CLEANED_TEXT_DIR = STAINLESS_STEEL_DATABASE_DIR / "text"  # 实际文件在text目录

# RAG配置（通过函数获取，传入数据库路径）
from core.config import get_rag_config
RAG_CONFIG = get_rag_config(
    base_dir=str(STAINLESS_STEEL_DATABASE_DIR),
    embedding_model="BAAI/bge-large-zh-v1.5",
    embedding_dim=1024,
    top_k=5,
    deepseek_config={
        "api_key": os.getenv("DEEPSEEK_API_KEY", "sk-tlhxqudzpcccjjsbiykehrseklpwcknslqaznpelpvqrrrxy"),
        "api_url": os.getenv("DEEPSEEK_API_URL", "https://api.siliconflow.cn/v1/chat/completions"),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3"),
        "temperature": float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3")),
    }
)

# 导出RAG配置
DB_PATH = RAG_CONFIG["DB_PATH"]
INDEX_PATH = RAG_CONFIG["INDEX_PATH"]
METADATA_PATH = RAG_CONFIG["METADATA_PATH"]
EMBEDDING_MODEL = RAG_CONFIG["EMBEDDING_MODEL"]
EMBEDDING_DIM = RAG_CONFIG["EMBEDDING_DIM"]
DEEPSEEK_CONFIG = RAG_CONFIG["DEEPSEEK_CONFIG"]
TOP_K = RAG_CONFIG["TOP_K"]



