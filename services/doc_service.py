import os
import datetime
import hashlib
from typing import Dict, List, Any, Optional
from utils.neo4j_utils import Neo4jConnection
from utils.llm_utils import LLMUtils
from utils.txt_utils import TextFileHandler

class DocumentService:
    """
    文档处理服务，负责文档的上传、处理、检索和删除等功能
    """
    
    def __init__(self):
        """
        初始化文档服务
        """
        self.neo4j = Neo4jConnection()
        self.llm = LLMUtils()
        self.text_handler = TextFileHandler()
        
        # 确保上传目录存在
        os.makedirs("uploads", exist_ok=True)
    
    def process_document(self, file_path: str, separator: str = "\n\n", max_chunk_size: int = 500) -> Dict[str, Any]:
        """
        处理上传的文档，包括分块、生成嵌入、保存到Neo4j等
        
        参数:
            file_path: 文件路径
            separator: 分块分隔符
            max_chunk_size: 每个分块的最大大小
            
        返回:
            包含处理结果的字典
        """
        try:
            # 1. 读取文件内容
            file_content = self.text_handler.read_file(file_path)
            
            # 2. 提取文件元数据
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            creation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 3. 生成文档摘要
            summary = self.llm.generate_summary(file_content)
            
            # 4. 生成文档ID
            doc_id = hashlib.md5(f"{file_name}_{creation_time}".encode()).hexdigest()
            
            # 5. 生成摘要的嵌入向量
            doc_embedding = self.llm.get_embedding(summary)
            
            # 6. 创建文档节点
            self.neo4j.create_document_node(
                doc_id=doc_id,
                title=file_name,
                created=creation_time,
                summary=summary,
                size=file_size,
                embedding=doc_embedding
            )
            
            # 7. 分割文档为块
            chunks = self.text_handler.split_text(file_content, separator, max_chunk_size)
            
            # 8. 处理每个块
            entities_count = 0
            for i, chunk_content in enumerate(chunks):
                # 为块生成ID
                chunk_id = f"{doc_id}_chunk_{i}"
                
                # 生成块的嵌入向量
                chunk_embedding = self.llm.get_embedding(chunk_content)
                
                # 创建块节点
                self.neo4j.create_chunk_node(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    position=i,
                    content=chunk_content,
                    embedding=chunk_embedding
                )
                
                # 提取块中的实体
                entities = self.llm.extract_entities(chunk_content)
                
                # 处理每个实体
                for entity in entities:
                    # 为实体生成ID
                    entity_id = hashlib.md5(f"{entity['name']}_{entity['type']}".encode()).hexdigest()
                    
                    # 生成实体的嵌入向量
                    entity_embedding = self.llm.get_embedding(entity['name'])
                    
                    # 创建或获取实体节点
                    self.neo4j.create_entity_node(
                        entity_id=entity_id,
                        name=entity['name'],
                        entity_type=entity['type'],
                        embedding=entity_embedding
                    )
                    
                    # 创建块和实体的关系
                    self.neo4j.create_chunk_entity_relationship(chunk_id, entity_id)
                    
                entities_count += len(entities)
            
            return {
                "success": True,
                "doc_id": doc_id,
                "chunks_count": len(chunks),
                "entities_count": entities_count
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_documents(self, title_filter: str = "") -> List[Dict[str, Any]]:
        """
        获取所有文档，可按标题筛选
        
        参数:
            title_filter: 标题筛选条件
            
        返回:
            文档列表
        """
        return self.neo4j.get_documents(title_filter)
    
    def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        获取指定文档的所有块
        
        参数:
            doc_id: 文档ID
            
        返回:
            块列表
        """
        return self.neo4j.get_document_chunks(doc_id)
    
    def get_document_content(self, doc_id: str) -> str:
        """
        获取整个文档的内容，用于下载
        
        参数:
            doc_id: 文档ID
            
        返回:
            文档完整内容
        """
        chunks = self.neo4j.get_document_chunks(doc_id)
        chunks.sort(key=lambda x: x['position'])
        return "\n\n".join([chunk['content'] for chunk in chunks])
    
    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档及其相关的块和关系
        
        参数:
            doc_id: 文档ID
            
        返回:
            删除成功返回True，否则返回False
        """
        try:
            # 获取文档信息
            doc = self.neo4j.get_document(doc_id)
            
            # 删除数据库中的文档及相关节点和关系
            self.neo4j.delete_document(doc_id)
            
            # 尝试删除上传的文件
            try:
                file_path = os.path.join("uploads", doc['title'])
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                # 如果文件删除失败，仍然继续处理
                pass
            
            return True
        except Exception:
            return False
