"""
SSEBrain Server配置文件
"""
import os
from pathlib import Path

# ==================== 服务器配置 ====================
SERVER_HOST = os.getenv("SSEBRAIN_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SSEBRAIN_SERVER_PORT", "50007"))
LOG_LEVEL = os.getenv("SSEBRAIN_LOG_LEVEL", "INFO")

# ==================== LLM API配置 ====================
LLM_API_TIMEOUT = int(os.getenv("SSEBRAIN_LLM_TIMEOUT", "300"))  # 5分钟超时
LLM_MAX_RETRIES = int(os.getenv("SSEBRAIN_LLM_MAX_RETRIES", "3"))

# ==================== 并行处理配置 ====================
MAX_WORKERS = int(os.getenv("SSEBRAIN_MAX_WORKERS", "20"))  # 并行处理文献的最大线程数

# ==================== 数据库配置 ====================
# SSEBrain使用固态电解质数据库
DB_NAME = "solid_state_electrolyte_db"

# ==================== DeepSeek配置 ====================
DEEPSEEK_CONFIG = {
    "api_key": os.getenv("DEEPSEEK_API_KEY", "sk-tlhxqudzpcccjjsbiykehrseklpwcknslqaznpelpvqrrrxy"),
    "api_url": os.getenv("DEEPSEEK_API_URL", "https://api.siliconflow.cn/v1/chat/completions"),
    "model": os.getenv("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3"),
    "temperature": float(os.getenv("DEEPSEEK_TEMPERATURE", "0.3")),
}


