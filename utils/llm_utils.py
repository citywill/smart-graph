import os
from typing import Dict, List, Any, Optional
import requests
from dotenv import load_dotenv
import json

class LLMUtils:
    """
    大模型工具类，处理模型调用、向量嵌入和实体抽取等功能
    """
    
    def __init__(self):
        """
        初始化LLM工具类
        """
        # 加载环境变量
        load_dotenv()
        
        # LLM API配置
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        
        # 向量模型配置
        self.embedding_url = os.getenv("OLLAMA_API", "http://localhost:11434") + "/api/embeddings"
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "bge")
    
    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的向量嵌入
        
        参数:
            text: 需要嵌入的文本
            
        返回:
            向量嵌入列表
        """
        try:
            # 调用Ollama API获取嵌入向量
            response = requests.post(
                self.embedding_url,
                json={"model": self.embedding_model, "prompt": text}
            )
            
            # 解析响应
            if response.status_code == 200:
                embedding = response.json().get("embedding", [])
                return embedding
            else:
                print(f"获取嵌入向量失败: {response.status_code}, {response.text}")
                # 返回空列表作为后备
                return [0.0] * 768
                
        except Exception as e:
            print(f"获取嵌入向量时出错: {str(e)}")
            # 返回空列表作为后备
            return [0.0] * 768
    
    def generate_summary(self, text: str) -> str:
        """
        为文本生成摘要
        
        参数:
            text: 需要生成摘要的文本
            
        返回:
            摘要文本
        """
        # 裁剪文本以避免超过token限制
        max_length = 4000
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        # 调用大模型生成摘要
        prompt = f"请为以下文本生成一个简短的摘要（100字以内）：\n\n{text}"
        
        try:
            response = self._call_llm(prompt)
            return response
        except Exception as e:
            print(f"生成摘要时出错: {str(e)}")
            # 如果出错，返回截断的原始文本作为摘要
            return text[:100] + "..."
    
    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """
        从文本中提取命名实体
        
        参数:
            text: 需要提取实体的文本
            
        返回:
            实体列表，每个实体为包含name和type的字典
        """
        # 裁剪文本以避免超过token限制
        max_length = 4000
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        # 调用大模型提取实体
        prompt = """请从以下文本中提取命名实体，并以JSON格式返回结果。
实体类型包括：人物、组织、公司、地点、时间、其他。
返回格式示例：
[
  {"name": "马云", "type": "人物"},
  {"name": "阿里巴巴", "type": "公司"},
  {"name": "杭州", "type": "地点"}
]

文本内容：
"""
        prompt += text
        
        try:
            response = self._call_llm(prompt)
            
            # 解析JSON响应
            try:
                # 确保我们提取的是JSON部分
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    entities = json.loads(json_str)
                    # 验证实体格式
                    valid_entities = []
                    for entity in entities:
                        if isinstance(entity, dict) and "name" in entity and "type" in entity:
                            valid_entities.append({
                                "name": entity["name"],
                                "type": entity["type"]
                            })
                    return valid_entities
            except json.JSONDecodeError:
                print("JSON解析失败，实体提取结果格式不正确")
            
            # 如果解析失败，返回空列表
            return []
        except Exception as e:
            print(f"提取实体时出错: {str(e)}")
            return []
    
    def generate_rag_response(self, query: str, context: str, prompt_template: str) -> str:
        """
        生成RAG回答
        
        参数:
            query: 用户查询
            context: 检索到的上下文信息
            prompt_template: 提示词模板
            
        返回:
            大模型生成的回答
        """
        # 填充提示词模板
        prompt = prompt_template.format(query=query, context=context)
        
        try:
            response = self._call_llm(prompt)
            return response
        except Exception as e:
            print(f"生成RAG回答时出错: {str(e)}")
            return "抱歉，处理您的问题时遇到了错误。请稍后再试。"
    
    def _call_llm(self, prompt: str) -> str:
        """
        调用大模型API
        
        参数:
            prompt: 提示词
            
        返回:
            大模型生成的回答
        """
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"API调用失败: {response.status_code}, {response.text}")
                return "API调用失败，请检查配置。"
                
        except Exception as e:
            print(f"调用大模型时出错: {str(e)}")
            return "调用大模型时出错，请检查网络连接和API配置。"
