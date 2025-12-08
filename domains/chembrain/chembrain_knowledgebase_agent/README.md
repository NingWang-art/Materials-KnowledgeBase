# ChemBrain Knowledge Base Agent

ChemBrain知识库Agent，提供基于结构化数据库检索的聚合物文献知识查询服务。

## 概述

与HEA和Stainless Steel知识库不同，ChemBrain使用**结构化数据库检索**而非RAG（向量检索）来查找相关文献。

## 工作流程

1. **自然语言查询转换**：将用户的自然语言查询转换为结构化的数据库查询条件（filters）
2. **结构化数据库查询**：在polymer_db数据库中执行查询，获取匹配的论文DOI列表
3. **并行读取全文**：并行读取每篇相关文献的全文
4. **并行生成总结**：并行对每篇文献调用LLM API，结合用户问题生成文献总结
5. **综合报告生成**：Agent将多个文献总结整合成一份综合性的研究报告

## 数据库结构

ChemBrain使用polymer_db数据库，包含以下主要表：

- **polym00**: 聚合物属性表，包含聚合物名称、类型、组成、属性、DOI等
- **690hd00**: 论文元数据表，包含标题、摘要、作者、发表日期、期刊信息、DOI等
- **690hd02**: 论文全文表，包含完整的论文文本和补充信息
- **690hd16/690hd17**: 单体信息表，包含单体缩写、全名、SMILES、备注等

## 使用示例

```python
# 查询特定类型的聚合物
query_chembrain_literature(
    query_description="查找玻璃化转变温度低于400°C的聚酰亚胺相关论文"
)

# 查询特定单体
query_chembrain_literature(
    query_description="查找包含PMDA单体的聚合物相关论文"
)

# 查询特定属性的聚合物
query_chembrain_literature(
    query_description="查找发表在一区期刊上的聚酰亚胺论文"
)
```

## 配置

Agent通过环境变量配置：

- `CHEMBRAIN_SERVER_URL`: ChemBrain MCP Server的URL（默认: `http://keld1409173.bohrium.tech:50007/sse`）

## 与HEA/Stainless Steel的区别

| 特性 | HEA/Stainless Steel | ChemBrain |
|------|-------------------|-----------|
| 检索方式 | RAG（向量相似度检索） | 结构化数据库查询 |
| 查询输入 | 自然语言问题 | 自然语言描述（转换为结构化查询） |
| 数据源 | 向量化的文本chunks | 结构化的数据库表 |
| 优势 | 语义理解，模糊匹配 | 精确查询，结构化数据 |


