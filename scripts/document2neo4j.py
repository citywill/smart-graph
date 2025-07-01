import sys
import io
import os
from pathlib import Path
from typing import List, Dict
import openai
import json
from py2neo import Graph, Node, Relationship

# 设置标准输出编码为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Neo4j配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
NEO4J_CONN = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# LLM配置
OPENAI_API_KEY = "ollama"
OPENAI_API_BASE = "http://172.16.70.15/ollama"
OPENAI_MODEL = "qwen2.5:14b"

def ask_llm(sys_prompt: str, user_prompt: str) -> Dict:
    """
    与LLM进行对话
    
    Args:
        sys_prompt: 系统提示
        user_prompt: 用户提示
    
    Returns:
        Dict: LLM的回答
    """
    base_url = OPENAI_API_BASE

    client = openai.Client(
        base_url=f"{base_url}/v1",
        api_key=OPENAI_API_KEY, 
    )

    messages=[
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]

    print("\n=== 测试普通对话 ===")

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0,
        response_format={
            'type': 'json_object'
        },
        max_tokens=8000
    )

    result = json.loads(response.choices[0].message.content)

    print(f"==== 回复：{result}")

    return result

def get_document_info(content: str) -> Dict:
    """
    通过LLM提取文书属性
    
    Args:
        content: 文本内容
        
    Returns:
        Dict: 提取的结果
    """
    prompt = f"""请提取文书属性：
- court：审理法院
- case_type：案件类型（如刑事、民事、行政等）
- time：裁判时间
- cause：案由（民事案由或刑事罪名等）
- defendants：被告（列表）
- plaintiffs：原告（列表）

使用中文回复。

严格按照JSON格式输出。
"""

    print("\n=== 测试普通对话 ===")
    
    response = ask_llm(prompt, content[:1000])

    print(f"回复：{response}")

    return response

def process_document(file_path: str) -> Dict:
    """
    处理单个文档文件，提取关系信息
    
    Args:
        file_path: 文档文件路径
        
    Returns:
        Dict: 包含提取出的关系信息的字典
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 提取文书属性
            document_info = get_document_info(content)

            document_info['name'] = os.path.basename(file_path)

            print(f"=== 文书属性：{document_info}")

            # 将文书写入neo4j数据库
            document_node = Node("Document", **document_info)
            NEO4J_CONN.create(document_node)

            # 目前返回一个示例数据
            print(f"=== 文件{file_path}开始分割")
            chunks = split_sentences_with_sliding_window(content)
            print(f"=== 文件{file_path}完成分割")

            print(f"=== 文件{file_path}开始关系提取")

            # 循环chunks，提取实体和关系
            # Todo ：修改为并行调用
            relations = []
            for chunk in chunks:
                # 提取关系并添加到列表中
                chunk_relations = extract_relations(chunk,document_node)
                if chunk_relations:
                    relations.extend(chunk_relations)

            print(f"=== 文件{file_path}完成关系提取")
            return {
                'file': file_path,
                'chunks': chunks,
                'relations': relations,
                'status': 'success'
            }
            
    except Exception as e:
        print(f"处理文件 {file_path} 时发生错误: {str(e)}")
        return {
            'file': file_path,
            'error': str(e),
            'status': 'failed'
        }

def extract_relations(chunk: str,document_node: Node) -> list:
    """
    提取文本中的关系

    Args:
        chunk: 文本块内容

    Returns:
        list: 关系列表，每个关系是一个字典，包含关系类型、关系实体和关系描述
    """

    role_list = ['被告人','原告','辩护人','审判员','书记员','审判长','受害人','证人']
    relation_list = ['购买毒品','出售毒品','容留吸毒','辩护','中间人']
    
    prompt = f"""请提取该文书中提到的所有人名及关系。
    严格返回json格式，将人名列表放置在"persons"字段中，将人物关系放置在"relations"中：
    - persons，list，抽取到的人物列表：
        - name，str，人物姓名
        - role，str，人物在本案中的角色，要求在文书中明确提及，只包括以下角色：{'、'.join(role_list)}
        - role_desc，str，文书中明确提及人物角色的原文描述
    - relations，list，实体关系列表：
        - subject，str，主体人名，必填字段，采用"persons"中内容
        - object，str，客体人名，必填字段，采用"persons"中内容
        - relation，str，实体关系，必填字段，只包括以下关系：{'、'.join(relation_list)}
        - event，str，事件经过，包含实体行为、时间、地点等事件信息
    """
    
    try:
        result = ask_llm(prompt, chunk)
            
        persons = result.get('persons', [])
        relations = result.get('relations', [])
        
        # 创建一个字典来存储人名到节点的映射
        person_nodes = {}
        
        # 将persons写入neo4j
        for person in persons:
            name = person['name']
            role = person['role']
            if role not in role_list:
                role = '其它关系'
            # 创建人物节点
            person_node = Node("Person", name=name)
            person_nodes[name] = person_node
            # 合并节点和关系
            NEO4J_CONN.merge(person_node, "Person", "name")
            NEO4J_CONN.merge(Relationship(document_node, role, person_node, role_desc=person['role_desc']))

        # 处理关系
        for r in relations:
            subject = r.get('subject')
            object_person = r.get('object')
            
            # 检查subject和object是否在person_nodes中
            if (
                subject and 
                object_person and 
                subject in person_nodes and 
                object_person in person_nodes and
                r['relation'] in relation_list and
                r['event'] != ''
            ):
                # 将人和人的关系写入neo4j
                NEO4J_CONN.merge(Relationship(person_nodes[subject], r['relation'], person_nodes[object_person], event=r['event']))
        
        return relations
        
    except Exception as e:
        print(f"提取关系时发生错误: {str(e)}")
        return []

def split_text_into_sentences(text: str) -> list:
    """
    将文本分割成句子
    
    Args:
        text (str): 输入的中文文本
        
    Returns:
        list: 句子列表
    """
    # 常见的中文句子结束符
    sentence_ends = ['。', '！', '？', '\n']
    sentences = []
    start = 0
    
    for i, char in enumerate(text):
        if char in sentence_ends:
            sentence = text[start:i + 1]
            if sentence:  # 忽略空句子
                sentences.append(sentence)
            start = i + 1
            
    # 处理最后一个句子
    if start < len(text):
        last_sentence = text[start:].strip()
        if last_sentence:
            sentences.append(last_sentence)
            
    return sentences

def split_sentences_with_sliding_window(text: str, window_size: int = 12, step_size: int = 10) -> list:
    """
    使用滑动窗口方式将句子列表组合成文本块
    
    Args:
        sentences (list): 句子列表
        window_size (int): 窗口大小（每个chunk包含的句子数）
        step_size (int): 滑动步长（每次移动的句子数）
        
    Returns:
        list: 包含所有文本块的列表
    """

    sentences = split_text_into_sentences(text)

    if not sentences:
        return []
        
    chunks = []
    start = 0
    i = 0
    
    while start < len(sentences):
        i += 1

        # 获取当前窗口的结束位置
        end = min(start + window_size, len(sentences))
        
        # 将当前窗口内的句子组合成块
        chunk = ''.join(sentences[start:end])
        print(f"==== 当前块{i}: \n{chunk}")
        chunks.append(chunk)
        
        # 如果已经处理到最后，退出循环
        if end == len(sentences):
            break
            
        # 移动窗口
        start += step_size
        
    return chunks

def process_directory(directory_path: str, file_extensions: List[str] = ['.txt', '.md']) -> List[Dict]:
    """
    遍历目录处理所有文本文件
    
    Args:
        directory_path: 要处理的目录路径
        file_extensions: 要处理的文件扩展名列表
        
    Returns:
        List[Dict]: 处理结果列表
    """
    results = []
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"目录不存在: {directory_path}")
        return results
        
    # 遍历目录下的所有文件
    for file_path in directory.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in file_extensions:
            print(f"正在处理文件: {file_path}")
            result = process_document(str(file_path))
            results.append(result)
            
    return results

def main():
    # 处理目录下所有文件
    # docs_dir = './docs/执行'
    # results = process_directory(docs_dir)
    
    # 处理一个文件
    file_path = './docs/贩毒/邹某非、张某甲等走私、贩卖、运输、制造毒品罪刑事一审刑事判决书.md'
    result = process_document(file_path)  # 注意这里改为单数形式
    
    # 输出处理结果
    print(f"\n处理结果状态：{result['status']}")
    
    # 如果处理失败，输出详细信息
    if result['status'] == 'failed':
        print("\n处理失败详情:")
        print(f"文件: {result['file']}")
        print(f"错误: {result['error']}")
    else:
        print(f"\n成功处理文件：{result['file']}")
        print(f"提取的关系数量：{len(result['relations'])}")

if __name__ == "__main__":
    main()