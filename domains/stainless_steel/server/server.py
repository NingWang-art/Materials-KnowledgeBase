"""
Stainless Steel RAG问答系统 MCP Server
提供基于RAG的不锈钢文献知识问答服务
"""
import argparse
import logging
from typing import List, Dict, Tuple
try:
    from typing_extensions import TypedDict
except ImportError:
    from typing import TypedDict
from pathlib import Path
from datetime import datetime
import sys
from anyio import to_thread

# 添加项目路径
sys.path.insert(0, str(Path("/home/knowledge_base")))

from dp.agent.server import CalculationMCPServer

# 从core导入RAG组件
from core.embedder import BGEEmbedder
from core.vector_store import FAISSVectorStore
from core.database import ChunkDatabase
from core.retriever import Retriever
from core.generator import DeepSeekGenerator
from core.rag_pipeline import RAGPipeline
from core.config import get_rag_config

# 导入通用模块
sys.path.insert(0, str(Path("/home/knowledge_base")))
from common.constants import StatusCode
from tools.utils import (
    generate_literature_summaries_parallel
)

# 导入Stainless Steel特定模块（config和prompts现在在server目录下）
# 支持直接运行和作为模块导入两种方式
try:
    from .config import (
        SERVER_HOST, SERVER_PORT, LOG_LEVEL, MAX_WORKERS, LLM_API_TIMEOUT, LLM_MAX_RETRIES,
        DB_PATH, INDEX_PATH, METADATA_PATH, EMBEDDING_MODEL, EMBEDDING_DIM, DEEPSEEK_CONFIG, TOP_K
    )
    from .prompts import (
        LITERATURE_SUMMARY_SYSTEM_PROMPT,
        get_literature_summary_user_prompt
    )
    from .utils import read_literature_fulltext
except ImportError:
    # 如果相对导入失败，使用绝对导入（直接运行server.py时）
    from domains.stainless_steel.server.config import (
        SERVER_HOST, SERVER_PORT, LOG_LEVEL, MAX_WORKERS, LLM_API_TIMEOUT, LLM_MAX_RETRIES,
        DB_PATH, INDEX_PATH, METADATA_PATH, EMBEDDING_MODEL, EMBEDDING_DIM, DEEPSEEK_CONFIG, TOP_K
    )
    from domains.stainless_steel.server.prompts import (
        LITERATURE_SUMMARY_SYSTEM_PROMPT,
        get_literature_summary_user_prompt
    )
    from domains.stainless_steel.server.utils import read_literature_fulltext

# === ARG PARSING ===
def parse_args():
    parser = argparse.ArgumentParser(description="Stainless Steel RAG MCP Server")
    parser.add_argument('--port', type=int, default=SERVER_PORT, 
                       help=f'Server port (default: {SERVER_PORT})')
    parser.add_argument('--host', default=SERVER_HOST, 
                       help=f'Server host (default: {SERVER_HOST})')
    parser.add_argument('--log-level', default=LOG_LEVEL,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help=f'Logging level (default: {LOG_LEVEL})')
    try:
        return parser.parse_args()
    except SystemExit:
        class Args:
            port = SERVER_PORT
            host = SERVER_HOST
            log_level = LOG_LEVEL
        return Args()

# === OUTPUT TYPE ===
class QueryResult(TypedDict):
    summaries: List[str]           # 文献总结列表
    code: int                      # 状态码：0=正常，非0=异常


# === RAG SYSTEM INITIALIZATION ===
class RAGSystem:
    """RAG系统单例"""
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            logging.info("初始化RAG系统...")
            
            # 加载组件
            self.embedder = BGEEmbedder(model_name=EMBEDDING_MODEL)
            self.vector_store = FAISSVectorStore(embedding_dim=EMBEDDING_DIM)
            self.database = ChunkDatabase(DB_PATH)
            self.retriever = Retriever(self.vector_store, self.embedder, self.database)
            # 创建生成器：用于文献总结
            self.summary_generator = DeepSeekGenerator(**DEEPSEEK_CONFIG)
            self.pipeline = RAGPipeline(self.retriever, self.summary_generator)
            
            # 加载索引
            logging.info("加载FAISS索引...")
            self.vector_store.load(INDEX_PATH, METADATA_PATH)
            
            logging.info("RAG系统初始化完成！")
            logging.info(f"索引包含 {self.vector_store.get_total_vectors()} 个向量")
            
            RAGSystem._initialized = True
    
    def query(self, question: str, top_k: int = TOP_K) -> QueryResult:
        """
        执行RAG查询流程：
        1. RAG检索找到相关chunks
        2. 提取唯一的文献ID
        3. 并行读取每个文献的全文并生成总结
        4. 返回文献总结列表（汇总由agent完成）
        
        Returns:
            QueryResult包含summaries和code
            summaries: 文献总结文本列表
            code: 使用StatusCode常量定义的状态码
        """
        try:
            query_start = datetime.now()
            logging.info(f"开始处理查询: {question}")
            
            # 步骤1: RAG检索找到相关chunks
            logging.info("步骤1: RAG检索相关chunks...")
            chunks = self.retriever.retrieve(question, k=top_k)
            
            if not chunks:
                logging.warning("未找到相关信息")
                return {
                    "summaries": [],
                    "code": StatusCode.NO_RESULTS
                }
            
            # 步骤2: 提取唯一的文献ID（去重）
            logging.info("步骤2: 提取唯一文献ID...")
            unique_file_ids = list(set([chunk['file_id'] for chunk in chunks]))
            logging.info(f"找到 {len(unique_file_ids)} 篇相关文献: {unique_file_ids}")
            
            # 步骤3-4: 并行读取全文并生成文献总结
            logging.info("步骤3-4: 并行读取文献全文并生成总结...")
            literature_summaries = generate_literature_summaries_parallel(
                file_ids=unique_file_ids,
                question=question,
                generator=self.summary_generator,
                system_prompt=LITERATURE_SUMMARY_SYSTEM_PROMPT,
                get_user_prompt_func=get_literature_summary_user_prompt,
                read_fulltext_func=read_literature_fulltext,
                max_workers=MAX_WORKERS,
                timeout=LLM_API_TIMEOUT,
                max_retries=LLM_MAX_RETRIES
            )
            
            if not literature_summaries:
                logging.warning("无法读取相关文献的全文")
                return {
                    "summaries": [],
                    "code": StatusCode.NO_LITERATURE
                }
            
            # 提取summary文本列表
            summary_texts = [summary['summary'] for summary in literature_summaries]
            
            total_time = (datetime.now() - query_start).total_seconds()
            logging.info(f"查询完成，总耗时: {total_time:.2f}s，返回 {len(summary_texts)} 个文献总结")
            
            return {
                "summaries": summary_texts,
                "code": StatusCode.SUCCESS
            }
            
        except Exception as e:
            logging.error(f"查询处理失败: {e}", exc_info=True)
            return {
                "summaries": [],
                "code": StatusCode.OTHER_ERROR
            }


# === MCP SERVER ===
args = parse_args()
logging.basicConfig(level=args.log_level)
logger = logging.getLogger(__name__)

# 初始化RAG系统
rag_system = RAGSystem()

mcp = CalculationMCPServer("STEELkb", port=args.port, host=args.host)


# === MCP TOOL ===
@mcp.tool()
async def query_steelkb_literature(
    question: str,
    top_k: int = 5
) -> QueryResult:
    """
    📚 查询STEELkb不锈钢文献知识库，基于RAG技术进行文献检索和总结生成。

    🔍 功能说明:
    -----------------------------------
    本工具采用多阶段处理流程：
    1. 使用RAG向量检索技术从STEELkb文献库中检索top-k个最相关的文本片段
    2. 从检索结果中提取唯一的文献ID（去重）
    3. 并行读取每篇相关文献的全文
    4. 并行对每篇文献调用LLM API，结合用户问题生成文献总结（n个并行API调用，n=文献数）
    5. 返回文献总结列表（汇总由agent完成）

    🧩 参数:
    -----------------------------------
    question : str
        要查询的问题，例如：
        - "不锈钢的腐蚀机制是什么？"
        - "不锈钢的力学性能如何？"
        - "不锈钢的微观结构特征"
        - "不锈钢的制备方法和工艺"
    top_k : int, optional
        检索的top-k个相关chunks数量 (默认: 5)
        建议范围: 5-15，更多chunks可能找到更多相关文献，但也会增加处理时间
        注意：实际处理的文献数量可能少于top_k（因为会去重）

    📤 返回:
    -----------------------------------
    QueryResult (dict) 包含:
        - summaries: 文献总结文本列表（List[str]），每个元素是一篇文献的总结
        - code: 状态码（使用StatusCode常量）
            - StatusCode.SUCCESS (0): 正常完成
            - StatusCode.NO_RESULTS (1): 未找到相关信息
            - StatusCode.NO_LITERATURE (2): 无法读取文献全文
            - StatusCode.OTHER_ERROR (4): 其他异常

    📝 使用示例:
    -----------------------------------
    # 基础查询
    query_steelkb_literature(
        question="不锈钢的腐蚀行为和防护机制是什么？"
    )

    # 检索更多结果（可能找到更多相关文献）
    query_steelkb_literature(
        question="不锈钢的力学性能和微观结构关系",
        top_k=10
    )
    """
    top_k = min(top_k, 20)
    logger.info(f"收到查询: {question} (top_k={top_k})")
    
    # 执行查询（在后台线程中运行，避免阻塞）
    result = await to_thread.run_sync(
        lambda: rag_system.query(question, top_k=top_k)
    )
    
    return result


# === START SERVER ===
if __name__ == "__main__":
    logger.info("Starting STEELkb MCP Server...")
    logger.info(f"Server will run on {args.host}:{args.port}")
    logger.info(f"RAG system ready with {rag_system.vector_store.get_total_vectors()} vectors")
    mcp.run(transport="sse")



