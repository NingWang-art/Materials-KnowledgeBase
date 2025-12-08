"""
答案生成模块
调用DeepSeek API生成答案
"""
import requests
import json
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeepSeekGenerator:
    """DeepSeek答案生成器"""
    
    def __init__(self, api_key: str, api_url: str = "https://api.siliconflow.cn/v1/chat/completions",
                 model: str = "deepseek-ai/DeepSeek-V3", temperature: float = 0.3):
        """
        初始化生成器
        
        Args:
            api_key: API密钥
            api_url: API地址
            model: 模型名称
            temperature: 温度参数
        """
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.temperature = temperature
    
    def _format_context(self, chunks: List[Dict]) -> str:
        """
        格式化检索到的chunks为上下文
        
        Args:
            chunks: chunk列表
            
        Returns:
            格式化后的上下文文本
        """
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            file_id = chunk.get('file_id', '未知')
            chunk_index = chunk.get('chunk_index', 0)
            text = chunk.get('text', '')
            
            context_parts.append(f"【文献片段{i} - 来源: {file_id}, 片段{chunk_index}】\n{text}\n")
        
        return "\n".join(context_parts)
    
    def generate(self, query: str, chunks: List[Dict]) -> str:
        """
        生成答案
        
        Args:
            query: 用户问题
            chunks: 检索到的chunks
            
        Returns:
            生成的答案
        """
        # 构建prompt
        system_prompt = """你是一位高熵合金(HEA)材料科学专家。你的任务是基于提供的文献内容回答用户的问题。

要求：
1. 严格基于提供的文献内容回答，不要编造信息
2. 如果文献中没有相关信息，明确说明
3. 引用具体的数值和数据时要准确
4. 标注信息来源（来自哪篇文献的哪个片段）
5. 如果多个文献有不同观点，分别说明
6. 回答要专业、准确、有条理"""

        context = self._format_context(chunks)
        
        user_prompt = f"""基于以下文献内容回答问题：

【文献内容】
{context}

【问题】
{query}

请基于上述文献内容回答问题，并标注信息来源。如果文献中没有相关信息，请明确说明。"""
        
        # 调用API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            answer = result['choices'][0]['message']['content']
            
            logger.info("答案生成成功")
            return answer
        
        except Exception as e:
            logger.error(f"生成答案时出错: {e}")
            raise













