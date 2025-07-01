---
trigger: manual
---

neo4j的配置：

- 主机：`localhost`
- 端口号：7687
- 账号：neo4j
- 密码：没有密码

数据模型：

- 节点：包括document、chunk、entity三类
- document属性包括：id、title（标题）、created（创建时间）、summary（摘要）、size、embedding（摘要的向量）
- chunk属性包括：id、position（次序位置）、content（内容）、embedding（内容的向量）
- entity属性包括：id、name（实体名称）、type（实体类型，包括人物、组织、公司、地点、时间等）、embedding（实体名称的向量）