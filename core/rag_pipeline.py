"""
RAG主流程模块
整合所有组件，提供完整的RAG功能
"""
from typing import List, Dict
try:
    from .retriever import Retriever
    from .generator import DeepSeekGenerator
except ImportError:
    from core.retriever import Retriever
    from core.generator import DeepSeekGenerator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG完整流程"""
    
    def __init__(self, retriever: Retriever, generator: DeepSeekGenerator):
        """
        初始化RAG流程
        
        Args:
            retriever: 检索器
            generator: 答案生成器
        """
        self.retriever = retriever
        self.generator = generator
    
    def query(self, question: str, top_k: int = 5) -> Dict:
        """
        执行完整的RAG查询流程
        
        Args:
            question: 用户问题
            top_k: 检索top-k个chunks
            
        Returns:
            Dict包含:
                - answer: 生成的答案
                - sources: 来源chunks信息
                - retrieved_chunks: 检索到的chunks
        """
        logger.info(f"处理问题: {question}")
        
        # 1. 检索相关chunks
        chunks = self.retriever.retrieve(question, k=top_k)
        
        if not chunks:
            return {
                'answer': '抱歉，未找到相关信息。',
                'sources': [],
                'retrieved_chunks': []
            }
        
        # 2. 生成答案
        answer = self.generator.generate(question, chunks)
        
        # 3. 整理来源信息
        sources = [
            {
                'file_id': chunk['file_id'],
                'chunk_index': chunk['chunk_index'],
                'distance': chunk.get('distance', 0)
            }
            for chunk in chunks
        ]
        
        return {
            'answer': answer,
            'sources': sources,
            'retrieved_chunks': chunks
        }













