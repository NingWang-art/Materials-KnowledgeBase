"""
SSEBrain Structured Search问答系统 MCP Server
提供基于结构化数据库检索的SSEBrain文献知识问答服务
"""
import argparse
import logging
import json
import asyncio
import requests
from typing import List, Dict, Tuple, Optional
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

# 从core导入生成器
from core.generator import DeepSeekGenerator

# 导入通用模块
from common.constants import StatusCode
from tools.utils import (
    generate_literature_summaries_parallel,
    call_llm_api
)

# 导入ssebrain特定模块
try:
    from .config import (
        SERVER_HOST, SERVER_PORT, LOG_LEVEL, MAX_WORKERS, LLM_API_TIMEOUT, LLM_MAX_RETRIES,
        DB_NAME, DEEPSEEK_CONFIG
    )
    from .prompts import (
        LITERATURE_SUMMARY_SYSTEM_PROMPT,
        get_literature_summary_user_prompt,
        DATABASE_QUERY_SYSTEM_PROMPT,
        get_database_query_user_prompt
    )
    from .utils import read_literature_fulltext
except ImportError:
    # 如果相对导入失败，使用绝对导入（直接运行server.py时）
    from domains.ssebrain.server.config import (
        SERVER_HOST, SERVER_PORT, LOG_LEVEL, MAX_WORKERS, LLM_API_TIMEOUT, LLM_MAX_RETRIES,
        DB_NAME, DEEPSEEK_CONFIG
    )
    from domains.ssebrain.server.prompts import (
        LITERATURE_SUMMARY_SYSTEM_PROMPT,
        get_literature_summary_user_prompt,
        DATABASE_QUERY_SYSTEM_PROMPT,
        get_database_query_user_prompt
    )
    from domains.ssebrain.server.utils import read_literature_fulltext

# 导入DatabaseManager
# 添加domains路径以支持导入
sys.path.insert(0, str(Path("/home/knowledge_base/domains")))
# 使用ssebrain_agent中的DatabaseManager，它支持solid_state_electrolyte_db
from ssebrain.ssebrain_agent.tools.database import DatabaseManager

MAX_FULLTEXT_SUMMARIES = 20  # deep research时最多处理的全文文献数

# === ARG PARSING ===
def parse_args():
    parser = argparse.ArgumentParser(description="SSEBrain Structured Search MCP Server")
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


# === STRUCTURED SEARCH SYSTEM INITIALIZATION ===
class StructuredSearchSystem:
    """结构化检索系统单例"""
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            logging.info("初始化结构化检索系统...")
            
            # 初始化数据库管理器
            self.db_manager = DatabaseManager(DB_NAME)
            # 异步初始化数据库（获取表结构）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.db_manager.async_init())
            loop.close()
            
            # 创建生成器：用于文献总结和查询转换
            self.summary_generator = DeepSeekGenerator(**DEEPSEEK_CONFIG)
            self.query_generator = DeepSeekGenerator(**DEEPSEEK_CONFIG)
            
            logging.info("结构化检索系统初始化完成！")
            
            StructuredSearchSystem._initialized = True
    
    def _convert_query_to_filters(self, query_description: str) -> Dict:
        """
        使用LLM将自然语言查询转换为结构化filters
        
        Args:
            query_description: 自然语言查询描述
            
        Returns:
            结构化filters字典，如果转换失败返回None
        """
        try:
            system_prompt = DATABASE_QUERY_SYSTEM_PROMPT
            user_prompt = get_database_query_user_prompt(query_description)
            
            # 调用LLM生成filters JSON
            headers = {
                "Authorization": f"Bearer {self.query_generator.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.query_generator.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt + "\n\n请直接返回JSON格式的filters结构，不要包含其他解释文字。"}
                ],
                "temperature": 0.1  # 使用较低温度以确保结构化输出
            }
            
            response = requests.post(
                self.query_generator.api_url, 
                headers=headers, 
                json=data, 
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            filters_text = result['choices'][0]['message']['content']
            
            # 尝试提取JSON（可能包含markdown代码块）
            filters_text = filters_text.strip()
            if filters_text.startswith("```"):
                # 移除markdown代码块标记
                filters_text = filters_text.split("```")[1]
                if filters_text.startswith("json"):
                    filters_text = filters_text[4:]
                filters_text = filters_text.strip()
            
            filters = json.loads(filters_text)
            logging.info(f"成功转换查询为filters: {filters}")
            return filters
            
        except Exception as e:
            logging.error(f"转换查询为filters失败: {e}", exc_info=True)
            return None
    
    async def _query_database(self, filters: Dict, table_name: str = "526kq03") -> Tuple[List[str], Dict[str, Dict]]:
        """
        执行数据库查询，返回论文DOI列表和元数据信息
        
        Args:
            filters: 结构化filters
            table_name: 要查询的表名（默认使用论文元数据表526kq03）
            
        Returns:
            (DOI列表, DOI到元数据的映射字典)
        """
        try:
            query_table = self.db_manager.init_query_table()
            filters_json = json.dumps(filters)
            
            result = await query_table(
                table_name=table_name,
                filters_json=filters_json,
                selected_fields=None,
                page=1,
                page_size=100  # 限制最多100条结果
            )
            
            if 'error' in result:
                logging.warning(f"数据库查询错误: {result['error']}")
                return [], {}
            
            dois = result.get('papers', [])
            logging.info(f"数据库查询完成，找到 {len(dois)} 篇论文")
            
            # 如果有DOI列表，查询论文元数据表获取详细信息
            metadata_dict = {}
            if dois:
                # 查询论文元数据表 (526kq03) - 如果主查询表就是元数据表，则直接使用result中的result
                if result.get('result'):
                    # 如果主查询已经返回了元数据，直接使用
                    for paper in result['result']:
                        doi = paper.get('doi')
                        if doi:
                            metadata_dict[doi] = paper
                else:
                    # 否则单独查询元数据表
                    paper_metadata_filters = {
                        "type": 1,
                        "field": "doi",
                        "operator": "in",
                        "value": dois[:100]  # 限制最多100个DOI
                    }
                    metadata_result = await query_table(
                        table_name="526kq03",
                        filters_json=json.dumps(paper_metadata_filters),
                        selected_fields=None,
                        page=1,
                        page_size=100
                    )
                    
                    if 'error' not in metadata_result and metadata_result.get('result'):
                        for paper in metadata_result['result']:
                            doi = paper.get('doi')
                            if doi:
                                metadata_dict[doi] = paper
                
                logging.info(f"获取到 {len(metadata_dict)} 篇论文的元数据")
            
            return dois, metadata_dict
            
        except Exception as e:
            logging.error(f"数据库查询失败: {e}", exc_info=True)
            return [], {}
    
    def _generate_metadata_summary(self, doi: str, metadata: Dict, query_description: str) -> str:
        """
        基于数据库元数据生成文献简要总结
        
        Args:
            doi: 文献DOI
            metadata: 论文元数据字典
            query_description: 用户查询描述
            
        Returns:
            基于元数据的简要总结文本
        """
        try:
            # 提取元数据信息
            title = metadata.get('title', metadata.get('Title', '未知标题'))
            authors = metadata.get('authors', metadata.get('Authors', metadata.get('author', '未知作者')))
            journal = metadata.get('journal', metadata.get('Journal', metadata.get('journal_name', '未知期刊')))
            year = metadata.get('year', metadata.get('Year', metadata.get('publication_year', '')))
            abstract = metadata.get('abstract', metadata.get('Abstract', ''))
            
            # 构建简要总结
            summary_parts = [
                f"**文献信息（仅数据库元数据，无全文）**",
                f"",
                f"**标题**: {title}",
                f"**DOI**: {doi}",
            ]
            
            if authors and authors != '未知作者':
                summary_parts.append(f"**作者**: {authors}")
            
            if journal and journal != '未知期刊':
                summary_parts.append(f"**期刊**: {journal}")
            
            if year:
                summary_parts.append(f"**发表年份**: {year}")
            
            if abstract:
                # 限制摘要长度
                abstract_text = abstract[:500] + "..." if len(abstract) > 500 else abstract
                summary_parts.append(f"")
                summary_parts.append(f"**摘要**: {abstract_text}")
            
            summary_parts.append(f"")
            summary_parts.append(f"**说明**: 此文献在数据库中无全文内容，以上信息来自数据库元数据。")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logging.error(f"生成元数据总结失败 {doi}: {e}", exc_info=True)
            return f"**文献信息（仅数据库元数据）**\n\n**DOI**: {doi}\n\n**说明**: 此文献在数据库中无全文内容，仅提供DOI信息。"
    
    def query(self, query_description: str) -> QueryResult:
        """
        执行结构化检索查询流程：
        1. 将自然语言查询转换为结构化filters
        2. 执行数据库查询获取论文DOI列表和元数据
        3. 检查哪些DOI有全文
        4. 只对有全文的进行deep research（生成详细总结）
        5. 对无全文的使用元数据生成简要条目
        6. 返回文献总结列表（汇总由agent完成）
        
        Returns:
            QueryResult包含summaries和code
            summaries: 文献总结文本列表（包含详细总结和元数据条目）
            code: 使用StatusCode常量定义的状态码
        """
        try:
            query_start = datetime.now()
            logging.info(f"开始处理查询: {query_description}")
            
            # 步骤1: 将自然语言查询转换为结构化filters
            logging.info("步骤1: 转换自然语言查询为结构化filters...")
            filters = self._convert_query_to_filters(query_description)
            
            if not filters:
                logging.warning("无法转换查询为结构化filters")
                return {
                    "summaries": [],
                    "code": StatusCode.OTHER_ERROR
                }
            
            # 步骤2: 执行数据库查询获取DOI列表和元数据
            logging.info("步骤2: 执行数据库查询...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            dois, metadata_dict = loop.run_until_complete(self._query_database(filters))
            loop.close()
            
            if not dois:
                logging.warning("未找到相关论文")
                return {
                    "summaries": [],
                    "code": StatusCode.NO_RESULTS
                }
            
            logging.info(f"找到 {len(dois)} 篇相关论文: {dois[:5]}...")  # 只显示前5个
            
            # 步骤3: 检查哪些DOI有全文（只对有全文的进行deep research）
            logging.info("步骤3: 检查文献全文可用性...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 批量检查全文可用性
            async def check_fulltext_availability(doi: str) -> tuple:
                """检查单个DOI是否有全文"""
                fulltext = await read_literature_fulltext(doi, self.db_manager)
                return (doi, bool(fulltext))
            
            # 并行检查所有DOI的全文可用性
            check_tasks = [check_fulltext_availability(doi) for doi in dois]
            check_results = loop.run_until_complete(asyncio.gather(*check_tasks))
            loop.close()
            
            # 分离有全文和无全文的DOI
            dois_with_fulltext = [doi for doi, has_fulltext in check_results if has_fulltext]
            dois_without_fulltext = [doi for doi, has_fulltext in check_results if not has_fulltext]
            
            logging.info(f"全文可用性检查完成: {len(dois_with_fulltext)} 篇有全文, {len(dois_without_fulltext)} 篇无全文")
            
            summary_texts = []
            
            # 步骤4: 只对有全文的DOI进行并行读取和总结生成
            if dois_with_fulltext:
                if len(dois_with_fulltext) > MAX_FULLTEXT_SUMMARIES:
                    logging.info(
                        f"限制有全文文献数为 {MAX_FULLTEXT_SUMMARIES} (原有 {len(dois_with_fulltext)} 篇)"
                    )
                    dois_with_fulltext = dois_with_fulltext[:MAX_FULLTEXT_SUMMARIES]
                logging.info(f"步骤4: 对 {len(dois_with_fulltext)} 篇有全文的文献进行总结生成...")
                
                # 创建适配函数：将DOI转换为file_id格式（用于generate_literature_summaries_parallel）
                def read_fulltext_by_doi(doi: str) -> str:
                    """适配函数：同步读取DOI对应的全文"""
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        fulltext = loop.run_until_complete(
                            read_literature_fulltext(doi, self.db_manager)
                        )
                        return fulltext
                    finally:
                        loop.close()
                
                # 使用generate_literature_summaries_parallel生成总结
                # 注意：这里只使用有全文的DOI
                literature_summaries = generate_literature_summaries_parallel(
                    file_ids=dois_with_fulltext,  # 只使用有全文的DOI
                    question=query_description,
                    generator=self.summary_generator,
                    system_prompt=LITERATURE_SUMMARY_SYSTEM_PROMPT,
                    get_user_prompt_func=get_literature_summary_user_prompt,
                    read_fulltext_func=read_fulltext_by_doi,
                    max_workers=MAX_WORKERS,
                    timeout=LLM_API_TIMEOUT,
                    max_retries=LLM_MAX_RETRIES
                )
                
                if literature_summaries:
                    summary_texts.extend([summary['summary'] for summary in literature_summaries])
            
            # 步骤5: 对于无全文的文献，使用数据库元数据生成简要条目
            if dois_without_fulltext:
                logging.info(f"步骤5: 为 {len(dois_without_fulltext)} 篇无全文的文献生成元数据条目...")
                
                for doi in dois_without_fulltext:
                    metadata = metadata_dict.get(doi, {})
                    # 生成基于元数据的简要总结
                    metadata_summary = self._generate_metadata_summary(doi, metadata, query_description)
                    if metadata_summary:
                        summary_texts.append(metadata_summary)
            
            if not summary_texts:
                logging.warning("无法生成任何文献总结或元数据条目")
                return {
                    "summaries": [],
                    "code": StatusCode.NO_LITERATURE
                }
            
            total_time = (datetime.now() - query_start).total_seconds()
            logging.info(f"查询完成，总耗时: {total_time:.2f}s")
            logging.info(f"返回 {len(summary_texts)} 个条目（{len(dois_with_fulltext)} 篇有全文的文献总结 + {len(dois_without_fulltext)} 篇无全文的元数据条目）")
            
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

# 初始化结构化检索系统
search_system = StructuredSearchSystem()

mcp = CalculationMCPServer("SSEkb", port=args.port, host=args.host)


# === MCP TOOL ===
@mcp.tool()
async def query_ssekb_literature(
    query_description: str
) -> QueryResult:
    """
    📚 查询SSEkb文献知识库，基于结构化数据库检索进行文献检索和总结生成。

    🔍 功能说明:
    -----------------------------------
    本工具采用多阶段处理流程：
    1. 使用LLM将自然语言查询转换为结构化数据库查询条件（filters）
    2. 执行结构化数据库查询，从SSEkb数据库中检索匹配的论文DOI
    3. 检查哪些论文有全文可用
    4. 对有全文的论文进行deep research（并行读取全文并生成详细总结）
    5. 对无全文的论文使用数据库元数据生成简要条目
    6. 返回文献总结列表（汇总由agent完成）

    🧩 参数:
    -----------------------------------
    query_description : str
        要查询的自然语言描述，例如：
        - "查找具有特定性能的材料相关论文"
        - "查找特定材料类型的相关论文"

    📤 返回:
    -----------------------------------
    QueryResult (dict) 包含:
        - summaries: 文献总结文本列表（List[str]），包含详细总结和元数据条目
        - code: 状态码（使用StatusCode常量）
            - StatusCode.SUCCESS (0): 正常完成
            - StatusCode.NO_RESULTS (1): 未找到相关信息
            - StatusCode.NO_LITERATURE (2): 无法读取文献全文
            - StatusCode.OTHER_ERROR (4): 其他异常

    📝 使用示例:
    -----------------------------------
    # 基础查询
    query_ssekb_literature(
        query_description="查找具有特定性能的材料相关论文"
    )
    """
    logger.info(f"收到查询: {query_description}")
    
    # 执行查询（在后台线程中运行，避免阻塞）
    result = await to_thread.run_sync(
        lambda: search_system.query(query_description)
    )
    
    return result


# === START SERVER ===
if __name__ == "__main__":
    logger.info("Starting SSEkb MCP Server...")
    logger.info(f"Server will run on {args.host}:{args.port}")
    logger.info("Structured search system ready")
    mcp.run(transport="sse")

