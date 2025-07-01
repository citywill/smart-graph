from typing import Dict, List, Any, Optional
import numpy as np
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

class Neo4jConnection:
    """
    Neo4j数据库连接和操作工具类
    """
    
    def __init__(self):
        """
        初始化Neo4j连接
        """
        # 加载环境变量
        load_dotenv()
        
        # Neo4j连接配置
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "")
        
        # 创建数据库连接
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        
        # 确保必要的索引存在
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """
        确保必要的Neo4j索引存在
        """
        with self.driver.session() as session:
            # 文档ID索引
            session.run("CREATE INDEX document_id IF NOT EXISTS FOR (d:Document) ON (d.id)")
            # 文档标题索引
            session.run("CREATE INDEX document_title IF NOT EXISTS FOR (d:Document) ON (d.title)")
            # 块ID索引
            session.run("CREATE INDEX chunk_id IF NOT EXISTS FOR (c:Chunk) ON (c.id)")
            # 实体ID索引
            session.run("CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.id)")
            # 实体名称索引
            session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)")
    
    def close(self):
        """
        关闭Neo4j连接
        """
        if self.driver:
            self.driver.close()
    
    def create_document_node(self, doc_id: str, title: str, created: str, summary: str, size: int, embedding: List[float]):
        """
        创建文档节点
        
        参数:
            doc_id: 文档ID
            title: 文档标题
            created: 创建时间
            summary: 摘要
            size: 文件大小
            embedding: 摘要的向量嵌入
        """
        with self.driver.session() as session:
            session.run(
                """
                CREATE (d:Document {
                    id: $id, 
                    title: $title, 
                    created: $created, 
                    summary: $summary, 
                    size: $size, 
                    embedding: $embedding
                })
                """,
                id=doc_id,
                title=title,
                created=created,
                summary=summary,
                size=size,
                embedding=embedding
            )
    
    def create_chunk_node(self, chunk_id: str, doc_id: str, position: int, content: str, embedding: List[float]):
        """
        创建文档块节点，并与文档建立关系
        
        参数:
            chunk_id: 块ID
            doc_id: 文档ID
            position: 块在文档中的位置
            content: 块的内容
            embedding: 块内容的向量嵌入
        """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (d:Document {id: $doc_id})
                CREATE (c:Chunk {
                    id: $id, 
                    position: $position, 
                    content: $content, 
                    embedding: $embedding
                })
                CREATE (d)-[:CONTAINS]->(c)
                """,
                id=chunk_id,
                doc_id=doc_id,
                position=position,
                content=content,
                embedding=embedding
            )
    
    def create_entity_node(self, entity_id: str, name: str, entity_type: str, embedding: List[float]):
        """
        创建或更新实体节点
        
        参数:
            entity_id: 实体ID
            name: 实体名称
            entity_type: 实体类型
            embedding: 实体名称的向量嵌入
        """
        with self.driver.session() as session:
            session.run(
                """
                MERGE (e:Entity {id: $id})
                ON CREATE SET e.name = $name, e.type = $type, e.embedding = $embedding
                ON MATCH SET e.name = $name, e.type = $type, e.embedding = $embedding
                """,
                id=entity_id,
                name=name,
                type=entity_type,
                embedding=embedding
            )
    
    def create_chunk_entity_relationship(self, chunk_id: str, entity_id: str):
        """
        创建块和实体之间的关系
        
        参数:
            chunk_id: 块ID
            entity_id: 实体ID
        """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (c:Chunk {id: $chunk_id}), (e:Entity {id: $entity_id})
                MERGE (c)-[:MENTIONS]->(e)
                """,
                chunk_id=chunk_id,
                entity_id=entity_id
            )
    
    def get_documents(self, title_filter: str = "") -> List[Dict[str, Any]]:
        """
        获取所有文档，可按标题筛选
        
        参数:
            title_filter: 标题筛选条件
            
        返回:
            文档列表
        """
        with self.driver.session() as session:
            if title_filter:
                result = session.run(
                    """
                    MATCH (d:Document) 
                    WHERE d.title CONTAINS $title_filter 
                    RETURN d 
                    ORDER BY d.created DESC
                    """,
                    title_filter=title_filter
                )
            else:
                result = session.run(
                    """
                    MATCH (d:Document) 
                    RETURN d 
                    ORDER BY d.created DESC
                    """
                )
            
            return [self._format_document(record["d"]) for record in result]
    
    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """
        获取指定ID的文档
        
        参数:
            doc_id: 文档ID
            
        返回:
            文档信息
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (d:Document {id: $id}) 
                RETURN d
                """,
                id=doc_id
            )
            
            record = result.single()
            if record:
                return self._format_document(record["d"])
            return None
    
    def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        获取指定文档的所有块
        
        参数:
            doc_id: 文档ID
            
        返回:
            块列表
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (d:Document {id: $id})-[:CONTAINS]->(c:Chunk) 
                RETURN c 
                ORDER BY c.position
                """,
                id=doc_id
            )
            
            return [self._format_chunk(record["c"]) for record in result]
    
    
    def get_relevant_chunks(self, query_embedding: List[float], limit: int = 5) -> List[Dict]:
        """
        搜索与查询相关的文本块，使用向量检索
        
        Args:
            query_embedding (List[float]): 查询的向量嵌入
            limit (int): 返回结果数量限制
            
        Returns:
            List[Dict]: 相关文本块列表
        """
        with self.driver.session() as session:
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
            
            chunks = []
            for record in result:
                chunk = self._format_chunk(record["c"])
                chunk["doc_id"] = record["doc_id"]
                chunk["score"] = record["score"]
                chunks.append(chunk)
            
            print("相关块：", chunks)
            return chunks
    
    def get_entities_for_chunks(self, chunk_ids: List[str]) -> List[Dict[str, Any]]:
        """
        获取与指定块相关的所有实体
        
        参数:
            chunk_ids: 块ID列表
            
        返回:
            实体列表
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)
                WHERE c.id IN $chunk_ids
                WITH e, COLLECT(c.id) AS chunks
                RETURN e, chunks
                """,
                chunk_ids=chunk_ids
            )
            
            entities = []
            for record in result:
                entity = self._format_entity(record["e"])
                entity["chunk_ids"] = record["chunks"]
                entities.append(entity)
                
            return entities
    
    def delete_document(self, doc_id: str):
        """
        删除文档及其相关的块和关系
        
        参数:
            doc_id: 文档ID
        """
        with self.driver.session() as session:
            # 删除文档、相关块及关系
            session.run(
                """
                MATCH (d:Document {id: $id})
                OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)
                OPTIONAL MATCH (c)-[r:MENTIONS]->(e:Entity)
                DELETE r
                DELETE c
                DELETE d
                """,
                id=doc_id
            )
    
    def _format_document(self, node) -> Dict[str, Any]:
        """
        格式化文档节点
        
        参数:
            node: Neo4j节点
            
        返回:
            格式化后的文档字典
        """
        return {
            "id": node["id"],
            "title": node["title"],
            "created": node["created"],
            "summary": node["summary"],
            "size": node["size"],
        }
    
    def _format_chunk(self, node) -> Dict[str, Any]:
        """
        格式化块节点
        
        参数:
            node: Neo4j节点
            
        返回:
            格式化后的块字典
        """
        return {
            "id": node["id"],
            "position": node["position"],
            "content": node["content"],
        }
    
    def _format_entity(self, node) -> Dict[str, Any]:
        """
        格式化实体节点
        
        参数:
            node: Neo4j节点
            
        返回:
            格式化后的实体字典
        """
        return {
            "id": node["id"],
            "name": node["name"],
            "type": node["type"],
        }
    
    def _format_relationship(self, rel) -> Dict[str, Any]:
        """
        格式化关系
        
        参数:
            rel: Neo4j关系
            
        返回:
            格式化后的关系字典
        """
        return {
            "type": rel.type,
            "properties": dict(rel)
        }
