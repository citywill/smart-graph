---
trigger: always_on
---

# 技术栈

- 开发语言：Python 3.10
- 开发框架：Streamlit
- 智能体框架：langchain
- 数据库：neo4j 5.27.0
- 大模型调用：兼容 open ai 的 api
- 向量模型使用 bge-m3:latest ，基于 ollama 的 api

所有依赖均使用默认版本，`requirements.txt` 中不要限定版本号。

# 技术方案

## 知识召回

```python
result = session.run(
    """
    MATCH (c:Chunk)
    WHERE c.embedding IS NOT NULL
    WITH c, vector.similarity.cosine(c.embedding, $query_embedding) AS score
    ORDER BY score DESC
    LIMIT $limit
    MATCH (d:Document)-[:CONTAINS]->(c)
    RETURN c, d.id AS doc_id, score
    """,
    query_embedding=query_embedding,
    limit=limit
)
```