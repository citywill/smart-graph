import sys
import io
from typing import Dict, List, Optional

# 设置标准输出编码为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def verify_and_process_relations(data: Dict):
    """
    验证关系中的主体和客体是否在persons列表中，如果存在则准备写入neo4j
    
    Args:
        data: 包含persons和relations的字典数据
    """
    persons = data.get('persons', [])
    relations = data.get('relations', [])
    
    for relation in relations:
        subject_person = relation.get('subject')
        object_person = relation.get('object')
        
        # 检查subject是否在persons中
        if subject_person and object_person and object_person in persons and subject_person in persons:
            print(f"关系验证通过: {relation}")
            # TODO: 在这里调用neo4j写入函数
            # write_to_neo4j(relation)

# 测试数据
test_data = {
    'persons': ['高金星', '吉林省长春市人民检察院'],
    'relations': [
        {
            'subject': '高金星',
            'object': '吉林省长春市人民检察院',
            'relation': '被告人',
            'event': '因贩卖毒品罪、非法持有毒品罪一审刑事案件'
        },
        {
            'subject': '吉林省长春市人民检察院',
            'object': None,
            'relation': '公诉机关',
            'event': '对高金星等三人提起公诉'
        }
    ]
}

# 运行测试
verify_and_process_relations(test_data)