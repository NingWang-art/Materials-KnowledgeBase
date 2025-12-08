"""
SSEBrain领域特定的工具函数
"""
import logging
import asyncio
from typing import List, Dict, Optional
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path("/home/knowledge_base")))
sys.path.insert(0, str(Path("/home/knowledge_base/domains")))

from ssebrain.ssebrain_agent.tools.database import DatabaseManager

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


