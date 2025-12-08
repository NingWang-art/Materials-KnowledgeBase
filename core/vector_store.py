"""
FAISS向量存储模块
管理向量索引的构建、保存和加载
"""
import faiss
import numpy as np
from pathlib import Path
from typing import List, Optional
import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """FAISS向量存储"""
    
    def __init__(self, embedding_dim: int = 1024):
        """
        初始化向量存储
        
        Args:
            embedding_dim: embedding维度
        """
        self.embedding_dim = embedding_dim
        self.index = None
        self.chunk_ids = []  # 存储chunk_id列表，与index中的向量一一对应
    
    def build_index(self, embeddings: np.ndarray, chunk_ids: List[str]):
        """
        构建FAISS索引
        
        Args:
            embeddings: 向量数组，shape: (n_chunks, embedding_dim)
            chunk_ids: chunk_id列表，与embeddings一一对应
        """
        if len(embeddings) != len(chunk_ids):
            raise ValueError("embeddings和chunk_ids长度不匹配")
        
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(f"embedding维度不匹配: 期望{self.embedding_dim}, 实际{embeddings.shape[1]}")
        
        # 确保是float32类型
        embeddings = embeddings.astype('float32')
        
        # 创建FAISS索引（使用L2距离）
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        
        # 添加向量
        self.index.add(embeddings)
        self.chunk_ids = chunk_ids.copy()
        
        logger.info(f"索引构建完成: {len(chunk_ids)}个向量")
    
    def search(self, query_vector: np.ndarray, k: int = 5) -> List[tuple]:
        """
        搜索最相似的k个向量
        
        Args:
            query_vector: 查询向量，shape: (1, embedding_dim) 或 (embedding_dim,)
            k: 返回top-k结果
            
        Returns:
            List[tuple]: [(chunk_id, distance), ...]，按距离从小到大排序
        """
        if self.index is None:
            raise ValueError("索引未构建，请先调用build_index")
        
        # 确保是float32和正确的shape
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        query_vector = query_vector.astype('float32')
        
        # 搜索
        distances, indices = self.index.search(query_vector, min(k, len(self.chunk_ids)))
        
        # 转换为chunk_id列表
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.chunk_ids):
                chunk_id = self.chunk_ids[idx]
                distance = float(distances[0][i])
                results.append((chunk_id, distance))
        
        return results
    
    def save(self, index_path: str, metadata_path: str):
        """
        保存索引和元数据
        
        Args:
            index_path: 索引文件路径
            metadata_path: 元数据文件路径（chunk_ids）
        """
        if self.index is None:
            raise ValueError("索引未构建")
        
        # 保存FAISS索引
        faiss.write_index(self.index, index_path)
        logger.info(f"索引已保存到: {index_path}")
        
        # 保存chunk_ids
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.chunk_ids, f)
        logger.info(f"元数据已保存到: {metadata_path}")
    
    def load(self, index_path: str, metadata_path: str):
        """
        加载索引和元数据
        
        Args:
            index_path: 索引文件路径
            metadata_path: 元数据文件路径
        """
        # 加载FAISS索引
        # 对于大索引，尝试使用mmap减少内存占用
        try:
            # 先尝试直接加载
            self.index = faiss.read_index(index_path)
            logger.info(f"索引已加载: {self.index.ntotal}个向量")
        except MemoryError:
            logger.warning("直接加载失败，尝试使用mmap...")
            # 如果内存不足，可能需要使用其他策略
            # 注意：IndexFlatL2不支持mmap，但可以尝试其他方法
            raise MemoryError("索引文件太大，无法在当前内存限制下加载。建议增加内存或使用更小的索引。")
        
        # 加载chunk_ids
        with open(metadata_path, 'rb') as f:
            self.chunk_ids = pickle.load(f)
        logger.info(f"元数据已加载: {len(self.chunk_ids)}个chunk_id")
    
    def get_total_vectors(self) -> int:
        """获取向量总数"""
        if self.index is None:
            return 0
        return self.index.ntotal
    
    def add_vectors(self, embeddings: np.ndarray, chunk_ids: List[str]):
        """
        向现有索引添加向量（增量更新）
        
        Args:
            embeddings: 新向量
            chunk_ids: 新chunk_ids
        """
        if self.index is None:
            self.build_index(embeddings, chunk_ids)
            return
        
        if len(embeddings) != len(chunk_ids):
            raise ValueError("embeddings和chunk_ids长度不匹配")
        
        embeddings = embeddings.astype('float32')
        self.index.add(embeddings)
        self.chunk_ids.extend(chunk_ids)
        logger.info(f"已添加{len(chunk_ids)}个向量，当前总数: {self.index.ntotal}")

