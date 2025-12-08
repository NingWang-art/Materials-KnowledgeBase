"""
ChemBrain Server配置文件
"""
import os
from pathlib import Path

# ==================== 服务器配置 ====================
SERVER_HOST = os.getenv("CHEMBRAIN_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("CHEMBRAIN_SERVER_PORT", "50005"))
LOG_LEVEL = os.getenv("CHEMBRAIN_LOG_LEVEL", "INFO")

# ==================== LLM API配置 ====================
LLM_API_TIMEOUT = int(os.getenv("CHEMBRAIN_LLM_TIMEOUT", "300"))  # 5分钟超时
LLM_MAX_RETRIES = int(os.getenv("CHEMBRAIN_LLM_MAX_RETRIES", "3"))

# ==================== 并行处理配置 ====================
MAX_WORKERS = int(os.getenv("CHEMBRAIN_MAX_WORKERS", "20"))  # 并行处理文献的最大线程数

# ==================== 数据库配置 ====================
DB_NAME = "polymer_db"

# ==================== DeepSeek配置 ====================
DEEPSEEK_CONFIG = {
    "api_key": os.getenv("DEEPSEEK_API_KEY", "sk-tlhxqudzpcccjjsbiykehrseklpwcknslqaznpelpvqrrrxy"),
    "api_url": os.getenv("DEEPSEEK_API_URL", "https://api.siliconflow.cn/v1/chat/completions"),
    "model": os.getenv("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3"),
    "temperature": float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3")),
}

