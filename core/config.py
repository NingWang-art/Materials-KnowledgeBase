"""
RAG系统配置文件（通用版本）
路径通过参数传入，不硬编码
"""
import os
from pathlib import Path
from typing import Optional


def get_rag_config(
    base_dir: str,
    embedding_model: str = "BAAI/bge-large-zh-v1.5",
    embedding_dim: int = 1024,
    top_k: int = 5,
    deepseek_config: Optional[dict] = None
):
    """
    获取RAG配置
    
    Args:
        base_dir: 数据库基础目录路径
        embedding_model: embedding模型名称
        embedding_dim: embedding维度
        top_k: 默认检索top-k
        deepseek_config: DeepSeek配置字典，如果为None则使用默认值
        
    Returns:
        配置字典
    """
    base_path = Path(base_dir)
    
    # 路径配置
    cleaned_text_dir = base_path / "cleaned_text"
    rag_system_dir = base_path / "rag_system"
    embeddings_dir = rag_system_dir / "embeddings"
    faiss_index_dir = rag_system_dir / "faiss_index"
    chunks_dir = rag_system_dir / "chunks"
    db_path = rag_system_dir / "chunks.db"
    index_path = faiss_index_dir / "faiss.index"
    metadata_path = faiss_index_dir / "chunk_ids.pkl"
    
    # 创建必要的目录
    rag_system_dir.mkdir(parents=True, exist_ok=True)
    embeddings_dir.mkdir(parents=True, exist_ok=True)
    faiss_index_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)
    
    # 默认DeepSeek配置
    if deepseek_config is None:
        deepseek_config = {
            "api_key": "sk-dzuipvhsxfexyjcecqsxxtfnorpbgspkeipuumhafohaaqka",
            "api_url": "https://api.siliconflow.cn/v1/chat/completions",
            "model": "deepseek-ai/DeepSeek-V3.2-Exp",
            "temperature": 0.3,
        }
    
    return {
        "BASE_DIR": str(base_path),
        "CLEANED_TEXT_DIR": str(cleaned_text_dir),
        "RAG_SYSTEM_DIR": str(rag_system_dir),
        "EMBEDDINGS_DIR": str(embeddings_dir),
        "FAISS_INDEX_DIR": str(faiss_index_dir),
        "CHUNKS_DIR": str(chunks_dir),
        "DB_PATH": str(db_path),
        "INDEX_PATH": str(index_path),
        "METADATA_PATH": str(metadata_path),
        "CHUNK_SIZE": 768,
        "OVERLAP_SIZE": 120,
        "MIN_CHUNK_SIZE": 200,
        "EMBEDDING_MODEL": embedding_model,
        "EMBEDDING_DIM": embedding_dim,
        "BATCH_SIZE": 32,
        "MAX_LENGTH": 512,
        "TOP_K": top_k,
        "DEEPSEEK_CONFIG": deepseek_config,
    }
