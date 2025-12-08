"""
Embedding生成模块
使用bge-large-zh-v1.5模型生成文本向量
"""
import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np
# 修复numpy 2.x兼容性问题
if not hasattr(np, 'Inf'):
    np.Inf = np.inf
if not hasattr(np, 'asfarray'):
    np.asfarray = np.asarray
from typing import List, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BGEEmbedder:
    """BGE模型embedding生成器"""
    
    def __init__(self, model_name: str = "BAAI/bge-large-zh-v1.5", device: str = None):
        """
        初始化embedder
        
        Args:
            model_name: 模型名称或路径
            device: 设备（'cuda'或'cpu'），None则自动选择
        """
        self.model_name = model_name
        logger.info(f"Loading model: {model_name}")
        
        # 自动选择设备
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = device
        logger.info(f"Using device: {device}")
        
        # 配置下载参数
        import os
        # 优先使用本地模型目录（检查多个可能路径）
        local_model_paths = [
            "/home/knowledge_base_data/models/bge-large-zh-v1.5",
            "/home/HEA/models/bge-large-zh-v1.5",
            os.getenv("BGE_MODEL_PATH", ""),
        ]
        local_model_path = None
        for path in local_model_paths:
            if path and os.path.exists(path) and (os.path.exists(os.path.join(path, "pytorch_model.bin")) or 
                                                 os.path.exists(os.path.join(path, "model.safetensors"))):
                local_model_path = path
                logger.info(f"找到本地模型: {local_model_path}")
                self.model_name = local_model_path  # 使用本地路径
                break
        
        if local_model_path is None:
            # 如果本地没有，使用HuggingFace下载
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'  # 使用镜像源
            os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '1800'  # 30分钟超时（大文件需要更长时间）
            os.environ['TRANSFORMERS_OFFLINE'] = '0'  # 确保在线模式
        
        # 配置代理（如果环境变量中有）
        proxies = None
        http_proxy = os.getenv('http_proxy') or os.getenv('HTTP_PROXY')
        https_proxy = os.getenv('https_proxy') or os.getenv('HTTPS_PROXY')
        if http_proxy or https_proxy:
            proxies = {
                'http': http_proxy,
                'https': https_proxy or http_proxy
            }
            logger.info(f"Using HuggingFace mirror: https://hf-mirror.com with proxy")
        else:
            logger.info("Using HuggingFace mirror: https://hf-mirror.com (no proxy)")
        
        # 加载tokenizer和model
        # 如果找到了本地模型路径，直接使用；否则尝试加载
        if local_model_path:
            logger.info(f"从本地路径加载模型: {local_model_path}")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    local_model_path,
                    trust_remote_code=True,
                    local_files_only=True
                )
                logger.info("✓ Tokenizer从本地加载完成")
                
                # 尝试使用safetensors格式（避免PyTorch安全警告）
                try:
                    self.model = AutoModel.from_pretrained(
                        local_model_path,
                        trust_remote_code=True,
                        local_files_only=True,
                        use_safetensors=True  # 优先使用safetensors格式
                    )
                    logger.info("✓ 模型权重从本地加载完成（safetensors格式）")
                except Exception as e1:
                    logger.warning(f"safetensors格式加载失败: {e1}，尝试pytorch格式")
                    # 如果safetensors失败，使用pytorch格式
                    os.environ['TRANSFORMERS_SAFE_LOADING'] = '0'  # 允许加载pytorch格式
                    self.model = AutoModel.from_pretrained(
                        local_model_path,
                        trust_remote_code=True,
                        local_files_only=True,
                        use_safetensors=False
                    )
                    logger.info("✓ 模型权重从本地加载完成（pytorch格式）")
            except Exception as e:
                logger.error(f"本地模型加载失败: {e}")
                raise
        else:
            # 如果本地没有，尝试从网络下载
            logger.info("检查本地模型文件...")
            try:
                # 先尝试本地文件
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    proxies=proxies,
                    trust_remote_code=True,
                    local_files_only=True  # 优先使用本地文件
                )
                logger.info("✓ Tokenizer从本地加载完成")
                
                self.model = AutoModel.from_pretrained(
                    model_name,
                    proxies=proxies,
                    trust_remote_code=True,
                    local_files_only=True  # 优先使用本地文件
                )
                logger.info("✓ 模型权重从本地加载完成")
            except Exception as e:
                logger.warning(f"本地文件加载失败: {e}")
                logger.info("开始从网络下载模型...")
                # 如果本地文件不存在，再下载
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    proxies=proxies,
                    trust_remote_code=True,
                    local_files_only=False
                )
                logger.info("✓ Tokenizer下载完成")
                
                self.model = AutoModel.from_pretrained(
                    model_name,
                    proxies=proxies,
                    trust_remote_code=True,
                    local_files_only=False
                )
                logger.info("✓ 模型权重下载完成")
        
        self.model.to(device)
        self.model.eval()
        
        logger.info("Model loaded successfully")
    
    def _mean_pooling(self, model_output, attention_mask):
        """
        Mean pooling - 对token embeddings取平均
        
        Args:
            model_output: 模型输出
            attention_mask: attention mask
            
        Returns:
            pooled embeddings
        """
        token_embeddings = model_output[0]  # First element of model_output contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32, 
               max_length: int = 512, normalize: bool = True) -> np.ndarray:
        """
        对文本进行编码
        
        Args:
            texts: 单个文本或文本列表
            batch_size: 批处理大小
            max_length: 最大长度
            normalize: 是否归一化向量
            
        Returns:
            numpy array of embeddings, shape: (n_texts, embedding_dim)
        """
        if isinstance(texts, str):
            texts = [texts]
        
        all_embeddings = []
        
        # 批处理
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize
            encoded_input = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors='pt'
            )
            
            # 移动到设备
            encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}
            
            # 生成embeddings
            with torch.no_grad():
                model_output = self.model(**encoded_input)
                embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])
                
                # 归一化
                if normalize:
                    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            
            all_embeddings.append(embeddings.cpu().numpy())
        
        # 合并所有batch的结果
        result = np.vstack(all_embeddings)
        return result
    
    def encode_query(self, query: str, normalize: bool = True) -> np.ndarray:
        """
        编码查询文本（用于检索）
        对于BGE模型，查询需要添加特殊指令
        
        Args:
            query: 查询文本
            normalize: 是否归一化
            
        Returns:
            numpy array of embedding, shape: (1, embedding_dim)
        """
        # BGE模型对查询需要添加指令
        instruction = "为这个句子生成表示以用于检索相关文章："
        query_with_instruction = f"{instruction}{query}"
        
        return self.encode(query_with_instruction, normalize=normalize)
    
    def get_embedding_dim(self) -> int:
        """获取embedding维度"""
        # bge-base-zh-v1.5的维度是768, bge-large-zh-v1.5的维度是1024
        if "large" in self.model_name.lower():
            return 1024
        else:
            return 768

