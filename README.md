# Knowledge Base Framework

通用知识库检索框架，支持多个领域的知识库服务。**完全解耦设计**，各领域独立运行。

## 📁 目录结构

```
knowledge_base/
├── core/                    # RAG核心组件（完全解耦）
│   ├── embedder.py         # Embedding生成器
│   ├── vector_store.py      # FAISS向量存储
│   ├── database.py          # SQLite数据库管理
│   ├── retriever.py         # 检索器
│   ├── generator.py         # LLM生成器
│   ├── rag_pipeline.py      # RAG流程
│   ├── config.py            # 配置函数（路径通过参数传入）
│   └── chunker.py           # 文本分块工具
├── common/                  # 通用常量和配置
│   └── constants.py         # 状态码等通用常量
├── tools/                   # 通用工具函数
│   └── utils.py             # LLM调用、并行处理等工具
└── domains/                 # 各个领域
    ├── HEA/                 # 高熵合金领域
    │   ├── config.py        # HEA特定配置（包含RAG配置）
    │   ├── prompts.py       # HEA特定提示词
    │   └── server/          # HEA Server实现
    │       ├── server.py    # MCP Server主文件
    │       └── utils.py     # HEA特定工具（读取文献全文）
    ├── stainless_steel/     # 不锈钢领域（待实现）
    └── sse/                  # SSE领域（待实现）
```

## 🎯 设计理念

### 完全解耦
- **core/**: RAG核心组件，不依赖任何特定领域
- **common/**: 通用常量，所有领域共享
- **tools/**: 通用工具，所有领域共享
- **domains/**: 各领域独立实现，只依赖core、common、tools

### 数据文件分离
- **数据库文件**（chunks.db, faiss.index等）保留在原位置（如`/home/HEA/database/`）
- **数据文件**（cleaned_text等）保留在原位置
- 只通过路径引用，不移动大文件

### 配置化
- `core/config.py` 提供 `get_rag_config()` 函数，接受路径参数
- 各领域在 `config.py` 中调用该函数，传入自己的数据库路径
- 模型路径可通过环境变量 `BGE_MODEL_PATH` 配置

## 🚀 使用示例

### HEA Server

```bash
cd /home/knowledge_base/domains/HEA/server
python server.py --port 50003
```

### 添加新领域

1. 在 `domains/` 下创建新领域目录（如 `stainless_steel/`）
2. 创建 `config.py`，调用 `get_rag_config()` 传入数据库路径
3. 创建 `prompts.py`，定义领域特定的提示词
4. 创建 `server/utils.py`，实现 `read_literature_fulltext()` 函数
5. 参考 `HEA/server/server.py` 创建 `server/server.py`

## 📝 导入示例

```python
# 从core导入RAG组件
from core.embedder import BGEEmbedder
from core.vector_store import FAISSVectorStore
from core.database import ChunkDatabase
from core.retriever import Retriever
from core.generator import DeepSeekGenerator
from core.rag_pipeline import RAGPipeline
from core.config import get_rag_config

# 从common导入常量
from common.constants import StatusCode

# 从tools导入工具
from tools.utils import call_llm_api, generate_literature_summaries_parallel
```

## ✅ 解耦验证

- ✅ 不再依赖 `/home/HEA/src/rag/`
- ✅ 所有RAG组件在 `core/` 中
- ✅ 数据文件通过路径引用，不移动
- ✅ 各领域完全独立，可单独运行
