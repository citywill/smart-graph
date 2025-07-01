import os
from typing import Dict, List, Any, Optional
from utils.neo4j_utils import Neo4jConnection
from utils.llm_utils import LLMUtils
import prompts

class RAGService:
    """
    基于向量召回和知识图谱的问答服务
    """
    
    def __init__(self):
        """
        初始化RAG服务
        """
        self.neo4j = Neo4jConnection()
        self.llm = LLMUtils()
    
    def get_response(self, query: str) -> Dict[str, Any]:
        """
        根据用户查询获取回答和相关知识图谱
        
        参数:
            query: 用户查询
            
        返回:
            包含回答和知识图谱数据的字典
        """
        # 1. 生成查询向量
        query_embedding = self.llm.get_embedding(query)
        
        # 2. 向量检索相关块
        relevant_chunks = self.neo4j.get_relevant_chunks(query_embedding, limit=1)
        
        # 3. 如果没有找到相关块，返回无相关信息的回复
        if not relevant_chunks:
            return {
                "response": "我在知识库中没有找到与您问题相关的信息。请尝试调整问题或上传更多相关文档。",
                "graph_data": None
            }
        
        # 4. 提取相关块的文档ID，并获取相关实体
        chunk_ids = [chunk["id"] for chunk in relevant_chunks]
        related_entities = self.neo4j.get_entities_for_chunks(chunk_ids)
        
        # 5. 构建知识图谱数据
        graph_data = self._build_graph_data(relevant_chunks, related_entities)
        
        # 6. 构建上下文信息
        context = "\n\n".join([f"文档块 {i+1}:\n{chunk['content']}" for i, chunk in enumerate(relevant_chunks)])
        
        # 7. 调用大模型生成回答
        response = self.llm.generate_rag_response(query, context, prompts.RAG_PROMPT)
        
        return {
            "response": response,
            "graph_data": graph_data
        }
    
    def _build_graph_data(self, chunks: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        构建知识图谱可视化数据
        
        参数:
            chunks: 相关的文档块
            entities: 相关的实体
            
        返回:
            可视化图表数据
        """
        nodes = []
        edges = []
        
        # 添加文档块节点
        for chunk in chunks:
            doc_id = chunk['doc_id']
            doc_info = self.neo4j.get_document(doc_id)
            
            # 添加文档节点
            if not any(node['id'] == doc_id for node in nodes):
                nodes.append({
                    "id": doc_id,
                    "label": doc_info["title"],
                    "title": f"文档: {doc_info['title']}\n摘要: {doc_info['summary']}",
                    "color": "#6baed6"  # 蓝色
                })
            
            # 添加块节点
            chunk_id = chunk['id']
            nodes.append({
                "id": chunk_id,
                "label": f"块 {chunk['position']}",
                "title": chunk['content'][:100] + "...",
                "color": "#9ecae1"  # 浅蓝色
            })
            
            # 添加文档到块的边
            edges.append({
                "from": doc_id,
                "to": chunk_id,
                "label": "包含"
            })
        
        # 添加实体节点和关系
        for entity in entities:
            entity_id = entity['id']
            
            # 添加实体节点
            nodes.append({
                "id": entity_id,
                "label": entity['name'],
                "title": f"实体: {entity['name']}\n类型: {entity['type']}",
                "color": self._get_entity_color(entity['type'])
            })
            
            # 添加块到实体的边
            for chunk_id in entity['chunk_ids']:
                edges.append({
                    "from": chunk_id,
                    "to": entity_id,
                    "label": "提及"
                })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def _get_entity_color(self, entity_type: str) -> str:
        """
        根据实体类型获取颜色
        
        参数:
            entity_type: 实体类型
            
        返回:
            十六进制颜色代码
        """
        color_map = {
            "人物": "#fd8d3c",    # 橙色
            "组织": "#f03b20",    # 红色
            "公司": "#bd0026",    # 深红色
            "地点": "#31a354",    # 绿色
            "时间": "#756bb1",    # 紫色
            "其他": "#636363"     # 灰色
        }
        
        return color_map.get(entity_type, "#636363")
