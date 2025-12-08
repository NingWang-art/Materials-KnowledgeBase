"""
通用Server工具函数模块
"""
import logging
import requests
from pathlib import Path
from typing import List, Dict, Tuple, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)


def call_llm_api(
    generator,
    system_prompt: str,
    user_prompt: str,
    timeout: int = 300,
    max_retries: int = 3
) -> str:
    """
    调用LLM API（带重试机制）
    
    Args:
        generator: LLM生成器实例（需有api_key, api_url, model, temperature属性）
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
        
    Returns:
        LLM生成的文本
        
    Raises:
        Exception: API调用失败时抛出异常
    """
    headers = {
        "Authorization": f"Bearer {generator.api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": generator.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": generator.temperature
    }
    
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                generator.api_url,
                headers=headers,
                json=data,
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"LLM API调用失败 (尝试 {attempt}/{max_retries}): {e}，正在重试...")
                time.sleep(1 * attempt)  # 指数退避
            else:
                logger.error(f"LLM API调用失败，已重试 {max_retries} 次: {e}")
        except Exception as e:
            logger.error(f"LLM API调用时发生未知错误: {e}")
            raise
    
    # 所有重试都失败
    raise last_exception


def generate_single_literature_summary(
    file_id: str,
    fulltext: str,
    question: str,
    generator,
    system_prompt: str,
    get_user_prompt_func: Callable[[str, str], str],
    timeout: int = 300,
    max_retries: int = 3
) -> Tuple[str, str, float]:
    """
    为单个文献生成总结（用于并行处理）
    
    Args:
        file_id: 文献ID
        fulltext: 文献全文
        question: 用户问题
        generator: LLM生成器实例
        system_prompt: 系统提示词
        get_user_prompt_func: 生成用户提示词的函数
        timeout: API超时时间
        max_retries: 最大重试次数
        
    Returns:
        (file_id, summary, generation_time) 元组
    """
    start_time = datetime.now()
    
    try:
        user_prompt = get_user_prompt_func(question, fulltext)
        summary = call_llm_api(generator, system_prompt, user_prompt, timeout, max_retries)
        generation_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"文献总结生成成功: {file_id}, 耗时: {generation_time:.2f}s")
        return (file_id, summary, generation_time)
    except Exception as e:
        logger.error(f"生成文献总结失败 {file_id}: {e}")
        generation_time = (datetime.now() - start_time).total_seconds()
        return (file_id, f"生成总结时出错: {str(e)}", generation_time)


def generate_literature_summaries_parallel(
    file_ids: List[str],
    question: str,
    generator,
    system_prompt: str,
    get_user_prompt_func: Callable[[str, str], str],
    read_fulltext_func: Callable[[str], str],
    max_workers: int = 20,
    timeout: int = 300,
    max_retries: int = 3
) -> List[Dict]:
    """
    并行生成多篇文献的总结
    
    Args:
        file_ids: 文献ID列表
        question: 用户问题
        generator: LLM生成器实例
        system_prompt: 系统提示词
        get_user_prompt_func: 生成用户提示词的函数
        read_fulltext_func: 读取文献全文的函数
        max_workers: 最大并行线程数
        timeout: API超时时间
        max_retries: 最大重试次数
        
    Returns:
        文献总结列表，每个元素包含 file_id, summary, generation_time
    """
    logger.info(f"开始并行处理 {len(file_ids)} 篇文献的总结（最大并行数: {max_workers}）")
    
    # 读取所有文献全文
    literature_data = []
    for file_id in file_ids:
        fulltext = read_fulltext_func(file_id)
        if fulltext:
            literature_data.append((file_id, fulltext))
        else:
            logger.warning(f"跳过文献 {file_id}（无法读取全文）")
    
    if not literature_data:
        logger.warning("没有可处理的文献")
        return []
    
    # 并行生成总结
    summaries = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_file_id = {
            executor.submit(
                generate_single_literature_summary,
                file_id, fulltext, question, generator,
                system_prompt, get_user_prompt_func, timeout, max_retries
            ): file_id
            for file_id, fulltext in literature_data
        }
        
        # 收集结果
        for future in as_completed(future_to_file_id):
            file_id = future_to_file_id[future]
            try:
                result_file_id, summary, generation_time = future.result()
                summaries.append({
                    "file_id": result_file_id,
                    "summary": summary,
                    "generation_time": f"{generation_time:.2f}s"
                })
            except Exception as e:
                logger.error(f"处理文献 {file_id} 时出错: {e}")
                summaries.append({
                    "file_id": file_id,
                    "summary": f"处理时出错: {str(e)}",
                    "generation_time": "0.00s"
                })
    
    logger.info(f"完成 {len(summaries)} 篇文献的总结生成")
    return summaries

