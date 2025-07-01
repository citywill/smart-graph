import os
from typing import List, Optional

class TextFileHandler:
    """
    文本文件处理工具类，处理文本文件的读取和分块等功能
    """
    
    def __init__(self):
        """
        初始化文本文件处理工具类
        """
        pass
    
    def read_file(self, file_path: str) -> str:
        """
        读取文本文件内容
        
        参数:
            file_path: 文件路径
            
        返回:
            文件内容
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 检查文件类型
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in ['.txt', '.md']:
            raise ValueError(f"不支持的文件类型: {file_extension}，仅支持.txt和.md文件")
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试用GBK解码
            with open(file_path, 'r', encoding='gbk') as file:
                return file.read()
    
    def split_text(self, text: str, separator: str = "\n\n", max_chunk_size: int = 500) -> List[str]:
        """
        将文本分割成块
        
        参数:
            text: 要分割的文本
            separator: 分隔符
            max_chunk_size: 每个块的最大大小
            
        返回:
            分块后的文本列表
        """
        # 使用分隔符分割文本
        chunks = text.split(separator)
        
        # 过滤掉空块
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        
        # 处理过大的块
        result = []
        for chunk in chunks:
            if len(chunk) <= max_chunk_size:
                result.append(chunk)
            else:
                # 如果块太大，按句子分割
                sentences = self._split_into_sentences(chunk)
                current_chunk = ""
                
                for sentence in sentences:
                    # 如果当前句子加上现有块不超过最大大小，则添加到当前块
                    if len(current_chunk) + len(sentence) <= max_chunk_size:
                        if current_chunk:
                            current_chunk += " " + sentence
                        else:
                            current_chunk = sentence
                    # 否则，保存当前块并开始一个新块
                    else:
                        if current_chunk:
                            result.append(current_chunk)
                        
                        # 如果单个句子超过最大大小，则需要按字符分割
                        if len(sentence) > max_chunk_size:
                            for i in range(0, len(sentence), max_chunk_size):
                                result.append(sentence[i:i+max_chunk_size])
                            current_chunk = ""
                        else:
                            current_chunk = sentence
                
                # 添加最后一个块（如果有）
                if current_chunk:
                    result.append(current_chunk)
        
        return result
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        将文本分割成句子
        
        参数:
            text: 要分割的文本
            
        返回:
            句子列表
        """
        # 中文句子的结束标记
        sentence_endings = ["。", "！", "？", "…", "\n"]
        
        # 英文句子的结束标记
        sentence_endings.extend([".", "!", "?"])
        
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            
            if char in sentence_endings:
                sentences.append(current_sentence)
                current_sentence = ""
        
        # 添加最后一个句子（如果没有结束标记）
        if current_sentence:
            sentences.append(current_sentence)
        
        return sentences
