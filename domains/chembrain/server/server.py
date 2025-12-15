"""
ChemBrain Structured Search问答系统 MCP Server
提供基于结构化数据库检索的聚合物文献知识问答服务
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

# 导入chembrain特定模块
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
    from domains.chembrain.server.config import (
        SERVER_HOST, SERVER_PORT, LOG_LEVEL, MAX_WORKERS, LLM_API_TIMEOUT, LLM_MAX_RETRIES,
        DB_NAME, DEEPSEEK_CONFIG
    )
    from domains.chembrain.server.prompts import (
        LITERATURE_SUMMARY_SYSTEM_PROMPT,
        get_literature_summary_user_prompt,
        DATABASE_QUERY_SYSTEM_PROMPT,
        get_database_query_user_prompt
    )
    from domains.chembrain.server.utils import read_literature_fulltext

# 导入DatabaseManager
# 添加domains路径以支持导入
sys.path.insert(0, str(Path("/home/knowledge_base/domains")))
from chembrain.chembrain_agent.tools.database import DatabaseManager

MAX_FULLTEXT_SUMMARIES = 20  # deep research时最多处理的全文文献数

# === ARG PARSING ===
def parse_args():
    parser = argparse.ArgumentParser(description="ChemBrain Structured Search MCP Server")
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
            
            # 兼容旧格式：如果返回的是单个filters，转换为新格式
            if 'tables' not in filters and ('filters' in filters or 'type' in filters):
                # 旧格式，只有单个表的filters
                filters = {
                    'tables': [{
                        'table_name': 'polym00',
                        'filters': filters.get('filters', filters)
                    }]
                }
            
            return filters
            
        except Exception as e:
            logging.error(f"转换查询为filters失败: {e}", exc_info=True)
            return None
    
    async def _query_database(self, filters: Dict, table_name: str = "polym00") -> Tuple[List[str], Dict[str, Dict], Dict[str, Dict]]:
        """
        执行数据库查询，返回论文DOI列表、查询结果数据和元数据信息
        
        Args:
            filters: 结构化filters
            table_name: 要查询的表名
            
        Returns:
            (DOI列表, DOI到查询结果数据的映射字典, DOI到论文元数据的映射字典)
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
                return [], {}, {}
            
            dois = result.get('papers', [])
            logging.info(f"数据库查询完成，找到 {len(dois)} 篇论文")
            
            # 保存查询结果中每个条目的完整数据
            # 对于有DOI的表，使用DOI作为key；对于没有DOI的表（如环氧表），使用其他唯一标识符
            query_data_dict = {}
            if result.get('result'):
                for item in result['result']:
                    doi = item.get('doi')
                    if doi:
                        # 有DOI的表，使用DOI作为key
                        query_data_dict[doi] = item
                    elif table_name == "677df00":
                        # 环氧表没有DOI，使用formulation_id作为唯一标识符
                        formulation_id = item.get('formulation_id')
                        if formulation_id is not None:
                            key = f"epoxy_{formulation_id}"
                            query_data_dict[key] = item
                        else:
                            _id = item.get('_id')
                            if _id:
                                key = f"epoxy_{_id}"
                                query_data_dict[key] = item
                logging.info(f"保存了 {len(query_data_dict)} 个查询条目的数据")
            
            # 如果有DOI列表，查询论文元数据表获取详细信息
            metadata_dict = {}
            if dois:
                # 查询论文元数据表 (690hd00)
                paper_metadata_filters = {
                    "type": 1,
                    "field": "doi",
                    "operator": "in",
                    "value": dois[:100]  # 限制最多100个DOI
                }
                metadata_result = await query_table(
                    table_name="690hd00",
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
            
            return dois, query_data_dict, metadata_dict
            
        except Exception as e:
            logging.error(f"数据库查询失败: {e}", exc_info=True)
            return [], {}, {}
    
    def _generate_metadata_summary(self, doi: str, entry_data: Dict, query_description: str) -> str:
        """
        基于查询结果数据和元数据生成文献简要总结
        
        Args:
            doi: 文献DOI
            entry_data: 查询结果条目数据（包含查询表中的数据和论文元数据）
            query_description: 用户查询描述
            
        Returns:
            基于查询结果数据的简要总结文本
        """
        try:
            # 提取论文元数据信息（尝试多种可能的字段名）
            title = (entry_data.get('title') or entry_data.get('Title') or 
                    entry_data.get('paper_title') or entry_data.get('论文标题') or '')
            authors = (entry_data.get('authors') or entry_data.get('Authors') or 
                      entry_data.get('author') or entry_data.get('Authors_list') or 
                      entry_data.get('作者') or '')
            journal = (entry_data.get('journal') or entry_data.get('Journal') or 
                      entry_data.get('journal_name') or entry_data.get('journalName') or 
                      entry_data.get('期刊') or '')
            year = (entry_data.get('year') or entry_data.get('Year') or 
                   entry_data.get('publication_year') or entry_data.get('pub_year') or 
                   entry_data.get('发表年份') or '')
            abstract = (entry_data.get('abstract') or entry_data.get('Abstract') or 
                       entry_data.get('摘要') or '')
            
            # 构建简要总结
            summary_parts = [
                f"**数据库条目信息（无全文）**",
                f"",
            ]
            
            # 显示DOI或标识符
            if doi.startswith("环氧表条目_"):
                identifier = doi.replace("环氧表条目_", "")
                summary_parts.append(f"**条目标识符**: {identifier}")
            else:
                summary_parts.append(f"**DOI**: {doi}")
            
            # 显示论文基本信息（如果有）
            if title:
                summary_parts.append(f"**标题**: {title}")
            if authors:
                summary_parts.append(f"**作者**: {authors}")
            if journal:
                summary_parts.append(f"**期刊**: {journal}")
            if year:
                summary_parts.append(f"**发表年份**: {year}")
            if abstract:
                abstract_text = abstract[:500] + "..." if len(abstract) > 500 else abstract
                summary_parts.append(f"")
                summary_parts.append(f"**摘要**: {abstract_text}")
            
            # 显示查询结果中的其他数据字段（排除系统字段和已显示的字段）
            excluded_keys = {'doi', 'title', 'title', 'authors', 'author', 'journal', 'year', 'abstract',
                           'title', 'authors', 'journal_name', 'publication_year', 'abstract',
                           'paper_title', 'authors_list', 'pub_year', '论文标题', '作者', '期刊', '发表年份', '摘要',
                           '_id', 'a1b2c3d4e5_audit_id', 'a1b2c3d4e5_is_locked', 'a1b2c3d4e5_owner_id',
                           'a1b2c3d4e5_project_id', 'a1b2c3d4e5_source', 'a1b2c3d4e5_status', 'createTime', 'updateTime'}
            
            # 定义重要字段的优先级（化学信息、结构信息等）
            priority_fields = [
                'smiles', 'SMILES', 'smile', 'SMILE',
                'smiles_0', 'smiles_1', 'smiles_2', 'smiles_3',
                'SMILES_0', 'SMILES_1', 'SMILES_2', 'SMILES_3',
                'monomer', 'monomers', 'compound', 'compounds', 'compound_0', 'compound_1',
                'temperature', 'viscosity', 'ratio', 'ratios', 'ratio_0', 'ratio_1',
                'polymer_type', 'tensile_strength', 'flexural_strength', 'tensile_modulus',
                'elongation_at_break', 'glass_transition_temperature'
            ]
            
            priority_data = []
            normal_data = []
            for key, value in entry_data.items():
                key_lower = key.lower()
                if (key_lower not in excluded_keys and 
                    value is not None and 
                    str(value).strip() and 
                    not str(key).startswith('_') and
                    not str(key).startswith('a1b2c3d4e5_')):
                    # 检查是否是重要字段
                    is_priority = any(priority_key.lower() in key_lower for priority_key in priority_fields)
                    if is_priority:
                        priority_data.append((key, value))
                    else:
                        normal_data.append((key, value))
            
            # 先显示重要字段，再显示其他字段
            all_fields = priority_data + normal_data
            
            if all_fields:
                summary_parts.append(f"")
                summary_parts.append(f"**条目数据**:")
                for key, value in all_fields:
                    # 格式化显示
                    value_str = str(value)
                    if isinstance(value, (list, tuple)):
                        if len(value) > 10:
                            value_str = str(value[:10]) + f"... (共{len(value)}项)"
                        else:
                            value_str = str(value)
                    elif len(value_str) > 300:
                        value_str = value_str[:300] + "..."
                    summary_parts.append(f"  - **{key}**: {value_str}")
            
            summary_parts.append(f"")
            summary_parts.append(f"**说明**: 此条目在数据库中无全文内容，以上信息来自数据库查询结果。")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logging.error(f"生成条目总结失败 {doi}: {e}", exc_info=True)
            return f"**数据库条目信息**\n\n**DOI**: {doi}\n\n**说明**: 此条目在数据库中无全文内容，数据获取失败。"
    
    def query(self, query_description: str) -> QueryResult:
        """
        执行结构化检索查询流程：
        1. 将自然语言查询转换为结构化filters
        2. 执行数据库查询获取论文DOI列表
        3. 并行读取每个文献的全文并生成总结
        4. 返回文献总结列表（汇总由agent完成）
        
        Returns:
            QueryResult包含summaries和code
            summaries: 文献总结文本列表
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
            
            # 步骤2: 执行数据库查询获取DOI列表、查询结果数据和元数据
            logging.info("步骤2: 执行数据库查询...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 支持多表查询：如果filters包含tables数组，对每个表执行查询
            if isinstance(filters, dict) and 'tables' in filters:
                all_dois = []
                query_data_dict = {}
                metadata_dict = {}
                
                for table_query in filters['tables']:
                    table_name = table_query.get('table_name', 'polym00')
                    table_filters = table_query.get('filters', {})
                    
                    # 如果filters是数组，转换为组合条件格式
                    if isinstance(table_filters, list):
                        if len(table_filters) == 1:
                            table_filters = table_filters[0]
                        elif len(table_filters) > 1:
                            # 多个条件，使用AND组合
                            table_filters = {
                                'type': 2,
                                'groupOperator': 'and',
                                'sub': table_filters
                            }
                        else:
                            # 空数组，使用空条件
                            table_filters = {}
                    
                    logging.info(f"查询表 {table_name}...")
                    table_dois, table_query_data, table_metadata = loop.run_until_complete(
                        self._query_database(table_filters, table_name=table_name)
                    )
                    
                    # 合并结果
                    all_dois.extend(table_dois)
                    query_data_dict.update(table_query_data)
                    metadata_dict.update(table_metadata)
                
                # 去重DOI
                dois = list(set(all_dois))
                logging.info(f"多表查询完成，共找到 {len(dois)} 个唯一DOI，{len(query_data_dict)} 个条目")
            else:
                # 兼容旧格式：单个表查询
                dois, query_data_dict, metadata_dict = loop.run_until_complete(
                    self._query_database(filters.get('filters', filters) if isinstance(filters, dict) else filters)
                )
            
            loop.close()
            
            # 检查是否有无DOI的条目（如环氧表）
            epoxy_entries = {k: v for k, v in query_data_dict.items() if k.startswith('epoxy_')}
            
            if not dois and not epoxy_entries:
                logging.warning("未找到相关论文或条目")
                return {
                    "summaries": [],
                    "code": StatusCode.NO_RESULTS
                }
            
            logging.info(f"找到 {len(dois)} 篇相关论文: {dois[:5] if dois else []}...")  # 只显示前5个
            if epoxy_entries:
                logging.info(f"找到 {len(epoxy_entries)} 个环氧表条目")
            
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
                
                # 如果查询数据字典中没有某些DOI的信息，尝试重新查询
                missing_dois = [doi for doi in dois_without_fulltext if doi not in query_data_dict]
                if missing_dois:
                    logging.info(f"为 {len(missing_dois)} 个缺失查询数据的DOI重新查询...")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    # 查询缺失的DOI元数据
                    paper_metadata_filters = {
                        "type": 1,
                        "field": "doi",
                        "operator": "in",
                        "value": missing_dois[:100]  # 限制最多100个DOI
                    }
                    query_table = self.db_manager.init_query_table()
                    missing_metadata_result = loop.run_until_complete(
                        query_table(
                            table_name="690hd00",
                            filters_json=json.dumps(paper_metadata_filters),
                            selected_fields=None,
                            page=1,
                            page_size=100
                        )
                    )
                    loop.close()
                    
                    if 'error' not in missing_metadata_result and missing_metadata_result.get('result'):
                        for paper in missing_metadata_result['result']:
                            doi = paper.get('doi')
                            if doi and doi not in query_data_dict:
                                query_data_dict[doi] = paper
                                metadata_dict[doi] = paper
                        logging.info(f"补充获取到 {len([d for d in missing_dois if d in query_data_dict])} 个条目的数据")
                
                for doi in dois_without_fulltext:
                    # 优先使用查询结果中的数据，其次使用论文元数据
                    query_data = query_data_dict.get(doi, {})
                    paper_metadata = metadata_dict.get(doi, {})
                    # 合并查询结果数据和论文元数据
                    combined_data = {**query_data, **paper_metadata}  # 查询数据优先
                    # 生成基于查询结果数据和元数据的总结
                    metadata_summary = self._generate_metadata_summary(doi, combined_data, query_description)
                    if metadata_summary:
                        summary_texts.append(metadata_summary)
            
            # 处理环氧表等没有DOI的条目
            if epoxy_entries:
                logging.info(f"步骤6: 为 {len(epoxy_entries)} 个环氧表条目生成总结...")
                for key, entry_data in epoxy_entries.items():
                    # 生成基于查询结果数据的总结
                    identifier = entry_data.get('formulation_id') or entry_data.get('_id', key)
                    metadata_summary = self._generate_metadata_summary(
                        f"环氧表条目_{identifier}", 
                        entry_data, 
                        query_description
                    )
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

mcp = CalculationMCPServer("POLYMERkb", port=args.port, host=args.host)


# === MCP TOOL ===
@mcp.tool()
async def query_polymerkb_literature(
    query_description: str
) -> QueryResult:
    """
    📚 查询POLYMERkb聚合物文献知识库，基于结构化数据库检索进行文献检索和总结生成。

    🔍 功能说明:
    -----------------------------------
    本工具采用多阶段处理流程：
    1. 使用LLM将自然语言查询转换为结构化数据库查询条件（filters）
    2. 执行结构化数据库查询，从POLYMERkb数据库中检索匹配的论文DOI
    3. 并行读取每篇相关文献的全文
    4. 并行对每篇文献调用LLM API，结合用户问题生成文献总结（n个并行API调用，n=文献数）
    5. 返回文献总结列表（汇总由agent完成）

    🧩 参数:
    -----------------------------------
    query_description : str
        要查询的自然语言描述，例如：
        - "查找玻璃化转变温度低于400°C的聚酰亚胺相关论文"
        - "查找包含PMDA单体的聚合物相关论文"
        - "查找发表在一区期刊上的聚酰亚胺论文"
        - "查找具有特定机械性能的聚合物材料"

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
    query_polymerkb_literature(
        query_description="查找玻璃化转变温度低于400°C的聚酰亚胺相关论文"
    )

    # 查询特定单体
    query_polymerkb_literature(
        query_description="查找包含PMDA单体的聚合物相关论文"
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
    logger.info("Starting POLYMERkb MCP Server...")
    logger.info(f"Server will run on {args.host}:{args.port}")
    logger.info("Structured search system ready")
    mcp.run(transport="sse")

