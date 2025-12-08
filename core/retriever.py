"""
检索模块
整合向量存储和embedder，提供完整的检索功能
"""
from typing import List, Dict
import numpy as np
try:
    from .vector_store import FAISSVectorStore
    from .embedder import BGEEmbedder
    from .database import ChunkDatabase
except ImportError:
    from core.vector_store import FAISSVectorStore
    from core.embedder import BGEEmbedder
    from core.database import ChunkDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Retriever:
    """检索器"""
    
    def __init__(self, vector_store: FAISSVectorStore, embedder: BGEEmbedder, 
                 database: ChunkDatabase):
        """
        初始化检索器
        
        Args:
            vector_store: 向量存储
            embedder: embedding生成器
            database: chunk数据库
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.database = database
    
    def retrieve(self, query: str, k: int = 5) -> List[Dict]:
        """
        检索相关chunks
        
        Args:
            query: 查询文本
            k: 返回top-k结果
            
        Returns:
            List[Dict]: 检索到的chunks，包含完整信息
        """
        # 1. 将查询向量化
        query_vector = self.embedder.encode_query(query)
        
        # 2. 在FAISS中搜索
        search_results = self.vector_store.search(query_vector, k=k)
        
        # 3. 从数据库获取chunk详细信息
        chunk_ids = [chunk_id for chunk_id, _ in search_results]
        chunks = self.database.get_chunks_by_ids(chunk_ids)
        
        # 4. 添加相似度距离信息
        distance_map = {chunk_id: distance for chunk_id, distance in search_results}
        for chunk in chunks:
            chunk['distance'] = distance_map.get(chunk['chunk_id'], float('inf'))
        
        # 按距离排序（距离越小越相似）
        chunks.sort(key=lambda x: x.get('distance', float('inf')))
        
        logger.info(f"检索到{len(chunks)}个相关chunks")
        return chunks













