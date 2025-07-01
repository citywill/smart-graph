# -*- coding: utf-8 -*-
import re

def split_text_into_sentences(text: str) -> list:
    """
    将文本分割成句子
    
    Args:
        text (str): 输入的中文文本
        
    Returns:
        list: 句子列表
    """
    # 常见的中文句子结束符
    sentence_ends = ['。', '！', '？', '\n', '…']
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
    
    while start < len(sentences):
        # 获取当前窗口的结束位置
        end = min(start + window_size, len(sentences))
        
        # 将当前窗口内的句子组合成块
        chunk = ''.join(sentences[start:end])
        chunks.append(chunk)
        
        # 如果已经处理到最后，退出循环
        if end == len(sentences):
            break
            
        # 移动窗口
        start += step_size
        
    return chunks

def main():
    # 测试代码
    file_path = './docs/白玉走私、贩卖、运输、制造毒品罪、走私、贩卖、运输、制造毒品罪刑事一审刑事判决书.md'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用滑动窗口组合句子
    chunks = split_sentences_with_sliding_window(content, window_size=15, step_size=12)
    print("\n分割结果：")
    for i, chunk in enumerate(chunks, 1):
        print(f"============== Chunk {i}: ============== \n{chunk}")

if __name__ == "__main__":
    main()