import openai
import json
from typing import List, Dict

# LLM配置
OPENAI_API_KEY = "ollama"
OPENAI_API_BASE = "http://172.16.70.15/ollama"
OPENAI_MODEL = "phi4" # qwen2.5:14b phi4

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

    print(f"\n==== 回复：{result}")

    return result