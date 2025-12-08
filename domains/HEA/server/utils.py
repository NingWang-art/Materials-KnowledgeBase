"""
HEA领域特定的工具函数
"""
import logging
from pathlib import Path
from .config import CLEANED_TEXT_DIR

logger = logging.getLogger(__name__)


def read_literature_fulltext(file_id: str) -> str:
    """
    读取HEA文献全文
    
    Args:
        file_id: 文献文件ID（不含.txt扩展名）
        
    Returns:
        文献全文内容，如果读取失败返回空字符串
    """
    file_path = CLEANED_TEXT_DIR / f"{file_id}.txt"
    if not file_path.exists():
        logger.warning(f"文献文件不存在: {file_path}")
        return ""
    
    try:
        content = file_path.read_text(encoding='utf-8')
        logger.info(f"成功读取文献全文: {file_id}, 长度: {len(content)} 字符")
        return content
    except Exception as e:
        logger.error(f"读取文献文件失败 {file_id}: {e}")
        return ""


