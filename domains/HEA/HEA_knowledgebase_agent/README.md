# HEA Knowledge Base Agent

高熵合金(HEA)文献知识库Agent，基于RAG技术提供智能文献查询和综合分析服务。

## 目录结构

```
agent/
├── __init__.py      # 模块初始化
├── agent.py          # Agent主文件
└── README.md         # 说明文档
```

## 功能特点

- **RAG技术**：基于向量检索的文献查询
- **多文档分析**：并行处理多篇文献
- **智能总结**：自动生成文献总结和综合报告
- **自然语言查询**：支持中文自然语言问题

## 环境配置

### 1. 创建.env文件

在`agent`目录下创建`.env`文件（或复制`.env.example`）：

```bash
cd /home/knowledge_base/domains/HEA/agent
cp .env.example .env
```

### 2. 配置环境变量

编辑`.env`文件，设置以下变量：

```bash
# ==================== HEA RAG Server配置 ====================
# HEA RAG Server的SSE连接URL（必须配置）
# 格式: http://host:port/sse
# 默认端口: 50003
HEA_SERVER_URL=http://localhost:50003/sse

# ==================== Bohrium存储配置 ====================
# 用于存储Agent执行结果和中间数据（可选）
HTTP_PLUGIN_TYPE=bohrium
BOHRIUM_ACCESS_KEY=your_bohrium_access_key
BOHRIUM_PROJECT_ID=your_bohrium_project_id

# ==================== DP Tech平台配置 ====================
# 如果需要使用DP Tech平台的其他服务（可选）
OPENAPI_HOST=https://openapi.test.dp.tech
DFLOW_HOST=https://lbg-workflow-mlops.test.dp.tech
DFLOW_K8S_API_SERVER=https://lbg-workflow-mlops.test.dp.tech
BOHRIUM_API_URL=https://bohrium-api.test.dp.tech
```

### 3. 重要说明

- **HEA_SERVER_URL**: 必须配置，指向HEA RAG Server的SSE端点
  - 本地运行: `http://localhost:50003/sse`
  - 远程运行: `http://your-server-ip:50003/sse`
  - 注意URL必须以`/sse`结尾

- **Bohrium配置**: 可选，如果不需要存储功能可以注释掉

- 确保HEA RAG Server正在运行，并且可以通过配置的URL访问

## 使用方法

```python
from domains.HEA.agent.agent import root_agent

# Agent会自动连接到HEA RAG Server
# 可以通过ADK框架使用root_agent
```

## Agent能力

Agent可以回答以下类型的问题：

1. **相变机制**：FCC到HCP相变、TRIP机制等
2. **力学性能**：低温性能、高温性能、疲劳性能等
3. **腐蚀行为**：腐蚀机制、防护方法等
4. **微观结构**：结构特征、热处理调控等
5. **制备方法**：不同制备工艺的影响
6. **元素选择**：设计原则、元素组合影响
7. **强化机制**：固溶强化、析出强化等
8. **应用领域**：应用前景和优势

## 工具说明

Agent使用 `query_hea_literature` 工具，参数：

- `question` (str): 查询问题
- `top_k` (int, 默认5): 检索的chunks数量，建议5-15

返回：

- `report`: 综合研究报告（1000-1500字）
- `code`: 状态码（0=成功，其他=错误）

## 注意事项

1. 确保HEA RAG Server正在运行
2. 需要安装相关依赖：`nest_asyncio`, `google-adk`, `dp-agent`等
3. 建议使用conda环境`hea_rag`来避免依赖冲突

