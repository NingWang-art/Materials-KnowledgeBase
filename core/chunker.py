"""
文档分块模块
将文本文件分割成固定大小的chunks，支持重叠
"""
import re
from typing import List, Dict
from pathlib import Path


class TextChunker:
    """文本分块器"""
    
    def __init__(self, chunk_size: int = 768, overlap_size: int = 120, min_chunk_size: int = 200):
        """
        初始化分块器
        
        Args:
            chunk_size: 目标块大小（tokens，约等于字符数*0.75）
            overlap_size: 重叠大小（tokens）
            min_chunk_size: 最小块大小（tokens）
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
    
    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量
        简单估算：中文字符*1.5 + 英文单词*1.3
        """
        # 更简单的估算：字符数 * 0.75（对于中英文混合文本）
        return int(len(text) * 0.75)
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """将文本分割成段落"""
        # 按双换行符分割
        paragraphs = re.split(r'\n\s*\n', text)
        # 过滤空段落
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return paragraphs
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        # 按句号、问号、感叹号分割，保留分隔符
        sentences = re.split(r'([.!?。！？]\s*)', text)
        # 合并句子和分隔符
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])
        return [s.strip() for s in result if s.strip()]
    
    def chunk_text(self, text: str, file_id: str) -> List[Dict]:
        """
        将文本分割成chunks
        
        Args:
            text: 输入文本
            file_id: 文件ID
            
        Returns:
            List[Dict]: chunk列表，每个chunk包含：
                - chunk_id: chunk唯一标识
                - file_id: 文件ID
                - chunk_index: chunk在文件中的索引
                - text: chunk文本内容
                - start_char: 在原文中的起始位置
                - end_char: 在原文中的结束位置
                - token_count: token数量估算
        """
        chunks = []
        paragraphs = self._split_into_paragraphs(text)
        
        current_chunk = []
        current_chunk_tokens = 0
        current_start = 0
        chunk_index = 0
        last_chunk_end = 0  # 用于重叠
        
        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]
            para_tokens = self._estimate_tokens(para)
            
            # 如果单个段落就超过chunk_size，需要进一步切分
            if para_tokens > self.chunk_size:
                # 先保存当前chunk（如果有）
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunk_dict = self._create_chunk_dict(
                        file_id, chunk_index, chunk_text,
                        current_start, current_start + len(chunk_text),
                        current_chunk_tokens
                    )
                    chunks.append(chunk_dict)
                    last_chunk_end = current_start + len(chunk_text)
                    chunk_index += 1
                    current_chunk = []
                    current_chunk_tokens = 0
                
                # 切分大段落
                sentences = self._split_into_sentences(para)
                for sentence in sentences:
                    sent_tokens = self._estimate_tokens(sentence)
                    
                    if current_chunk_tokens + sent_tokens > self.chunk_size:
                        # 保存当前chunk
                        if current_chunk:
                            chunk_text = '\n\n'.join(current_chunk)
                            chunk_dict = self._create_chunk_dict(
                                file_id, chunk_index, chunk_text,
                                current_start, current_start + len(chunk_text),
                                current_chunk_tokens
                            )
                            chunks.append(chunk_dict)
                            last_chunk_end = current_start + len(chunk_text)
                            chunk_index += 1
                            
                            # 添加重叠
                            if chunks and last_chunk_end > 0:
                                overlap_text = self._get_overlap_text(
                                    text, last_chunk_end, self.overlap_size
                                )
                                current_chunk = [overlap_text] if overlap_text else []
                                current_chunk_tokens = self._estimate_tokens(overlap_text)
                                current_start = last_chunk_end - len(overlap_text) if overlap_text else last_chunk_end
                            else:
                                current_chunk = []
                                current_chunk_tokens = 0
                                current_start = last_chunk_end
                    
                    current_chunk.append(sentence)
                    current_chunk_tokens += sent_tokens
                    if current_start == 0:
                        current_start = text.find(sentence)
            
            # 正常情况：段落可以加入当前chunk
            elif current_chunk_tokens + para_tokens <= self.chunk_size:
                current_chunk.append(para)
                current_chunk_tokens += para_tokens
                if not current_chunk or current_start == 0:
                    current_start = text.find(para, last_chunk_end)
            
            # 当前chunk已满，保存并开始新chunk
            else:
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunk_dict = self._create_chunk_dict(
                        file_id, chunk_index, chunk_text,
                        current_start, current_start + len(chunk_text),
                        current_chunk_tokens
                    )
                    chunks.append(chunk_dict)
                    last_chunk_end = current_start + len(chunk_text)
                    chunk_index += 1
                    
                    # 添加重叠
                    overlap_text = self._get_overlap_text(
                        text, last_chunk_end, self.overlap_size
                    )
                    current_chunk = [overlap_text] if overlap_text else []
                    current_chunk_tokens = self._estimate_tokens(overlap_text)
                    current_start = last_chunk_end - len(overlap_text) if overlap_text else last_chunk_end
                
                # 添加当前段落
                current_chunk.append(para)
                current_chunk_tokens += para_tokens
                if current_start == 0:
                    current_start = text.find(para, last_chunk_end)
            
            i += 1
        
        # 保存最后一个chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            # 检查是否满足最小大小要求
            if self._estimate_tokens(chunk_text) >= self.min_chunk_size:
                chunk_dict = self._create_chunk_dict(
                    file_id, chunk_index, chunk_text,
                    current_start, current_start + len(chunk_text),
                    current_chunk_tokens
                )
                chunks.append(chunk_dict)
        
        return chunks
    
    def _get_overlap_text(self, text: str, start_pos: int, overlap_tokens: int) -> str:
        """获取重叠文本"""
        if start_pos <= 0:
            return ""
        
        # 从start_pos向前查找overlap_tokens的文本
        overlap_chars = int(overlap_tokens / 0.75)  # 转换为字符数
        overlap_start = max(0, start_pos - overlap_chars)
        
        # 尽量在段落或句子边界开始
        overlap_text = text[overlap_start:start_pos]
        
        # 尝试在段落边界开始
        para_start = overlap_text.rfind('\n\n')
        if para_start > len(overlap_text) * 0.3:  # 如果找到的边界不太靠前
            overlap_text = overlap_text[para_start + 2:]
        else:
            # 尝试在句子边界开始
            sent_start = max(
                overlap_text.rfind('。'),
                overlap_text.rfind('.'),
                overlap_text.rfind('！'),
                overlap_text.rfind('!'),
                overlap_text.rfind('？'),
                overlap_text.rfind('?')
            )
            if sent_start > len(overlap_text) * 0.3:
                overlap_text = overlap_text[sent_start + 1:]
        
        return overlap_text.strip()
    
    def _create_chunk_dict(self, file_id: str, chunk_index: int, text: str,
                          start_char: int, end_char: int, token_count: int) -> Dict:
        """创建chunk字典"""
        chunk_id = f"{file_id}_chunk_{chunk_index}"
        return {
            'chunk_id': chunk_id,
            'file_id': file_id,
            'chunk_index': chunk_index,
            'text': text,
            'start_char': start_char,
            'end_char': end_char,
            'token_count': token_count
        }
    
    def chunk_file(self, file_path: Path) -> List[Dict]:
        """
        对文件进行分块
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[Dict]: chunk列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        file_id = file_path.stem
        return self.chunk_text(text, file_id)













