"""
Stainless Steel领域特定的工具函数
"""
import logging
from pathlib import Path
from .config import CLEANED_TEXT_DIR

logger = logging.getLogger(__name__)


def read_literature_fulltext(file_id: str) -> str:
    """
    读取Stainless Steel文献全文
    
    Args:
        file_id: 文献文件ID（不含扩展名）
        
    Returns:
        文献全文内容，如果读取失败返回空字符串
    """
    # 支持 .md 和 .txt 文件
    file_path_md = CLEANED_TEXT_DIR / f"{file_id}.md"
    file_path_txt = CLEANED_TEXT_DIR / f"{file_id}.txt"
    
    file_path = None
    if file_path_md.exists():
        file_path = file_path_md
    elif file_path_txt.exists():
        file_path = file_path_txt
    else:
        logger.warning(f"文献文件不存在: {file_id} (.md 或 .txt)")
        return ""
    
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        logger.info(f"成功读取文献全文: {file_id}, 长度: {len(content)} 字符")
        return content
    except Exception as e:
        logger.error(f"读取文献文件失败 {file_id}: {e}")
        return ""



