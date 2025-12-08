"""
ChemBrain领域特定的工具函数
"""
import logging
import asyncio
from typing import List, Dict, Optional
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path("/home/knowledge_base")))
sys.path.insert(0, str(Path("/home/knowledge_base/domains")))

from chembrain.chembrain_agent.tools.database import DatabaseManager

logger = logging.getLogger(__name__)


async def read_literature_fulltext(doi: str, db_manager: DatabaseManager) -> str:
    """
    通过DOI从数据库读取文献全文
    
    Args:
        doi: 文献DOI
        db_manager: 数据库管理器实例
        
    Returns:
        文献全文内容，如果读取失败返回空字符串
    """
    try:
        fetch_paper_content = db_manager.init_fetch_paper_content()
        result = await fetch_paper_content(doi)
        
        if 'error' in result:
            logger.warning(f"无法获取文献全文: {doi}, 错误: {result['error']}")
            return ""
        
        full_text = result.get('main_txt', '')
        if not full_text:
            logger.warning(f"文献全文为空: {doi}")
            return ""
        
        logger.info(f"成功读取文献全文: {doi}, 长度: {len(full_text)} 字符")
        return full_text
    except Exception as e:
        logger.error(f"读取文献全文失败 {doi}: {e}", exc_info=True)
        return ""


async def query_database_by_description(
    query_description: str,
    db_manager: DatabaseManager
) -> Dict:
    """
    根据自然语言描述查询数据库，返回相关的论文DOI列表
    
    Args:
        query_description: 用户的自然语言查询描述
        db_manager: 数据库管理器实例
        
    Returns:
        包含papers（DOI列表）和code（状态码）的字典
    """
    try:
        # 这里需要调用LLM来将自然语言转换为结构化查询
        # 暂时先返回空结果，后续可以在server.py中实现完整的查询逻辑
        logger.info(f"处理查询: {query_description}")
        
        # TODO: 实现自然语言到结构化查询的转换
        # 这需要调用LLM来生成filters结构
        
        return {
            "papers": [],
            "code": 1  # 暂时返回未找到结果
        }
    except Exception as e:
        logger.error(f"数据库查询失败: {e}", exc_info=True)
        return {
            "papers": [],
            "code": 4  # 其他错误
        }

