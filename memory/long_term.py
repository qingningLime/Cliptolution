import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from api_client import DeepSeekClient

@dataclass
class MemoryItem:
    category: str
    key: Optional[str] = None
    value: str = ""
    timestamp: float = 0.0

class LongTermMemory:
    """纯文本长期记忆模块"""
    
    def __init__(self, api_key: str):
        self.client = DeepSeekClient(api_key)
        self.memories = []
        self.load_memories()

    def load_memories(self):
        """从txt文件加载记忆"""
        self.memories = []
        try:
            with open("memories.txt", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    # 解析格式: [category] key=value @timestamp
                    if line.startswith("[") and "]" in line:
                        category_end = line.index("]")
                        category = line[1:category_end]
                        rest = line[category_end+1:].strip()
                        
                        # 解析key和value
                        if "=" in rest:
                            eq_pos = rest.index("=")
                            key = rest[:eq_pos].strip()
                            value_part = rest[eq_pos+1:].split("@")[0].strip()
                            value = value_part
                        else:
                            key = None
                            value = rest.split("@")[0].strip()
                            
                        # 解析时间戳
                        timestamp = 0.0
                        if "@" in rest:
                            timestamp_str = rest.split("@")[1].strip()
                            try:
                                timestamp = float(timestamp_str)
                            except ValueError:
                                pass
                                
                        self.memories.append(
                            MemoryItem(
                                category=category,
                                key=key if key else None,
                                value=value,
                                timestamp=timestamp
                            )
                        )
        except FileNotFoundError:
            pass

    def save_memories(self):
        """保存记忆到txt文件"""
        with open("memories.txt", "w", encoding="utf-8") as f:
            f.write("# 记忆存储格式: [category] key=value @timestamp\n")
            for mem in self.memories:
                key_part = f"{mem.key}=" if mem.key else ""
                line = f"[{mem.category}] {key_part}{mem.value} @{mem.timestamp}\n"
                f.write(line)

    async def analyze_and_store(self, conversation: str) -> bool:
        """分析对话并存储重要记忆"""
        try:
            # 构建包含历史记忆的prompt
            existing_memories = "\n".join(
                f"- {m.category}: {m.value}" 
                for m in self.memories[:20]  # 限制最多20条记忆
            )
            
            prompt = self._build_safe_prompt(conversation, existing_memories)
            response = await self.client.chat_completion(
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            memories = self._parse_response(response)
            self.memories.extend(memories)
            self.save_memories()
            return True
        except Exception as e:
            print(f"记忆分析失败: {str(e)}")
            return False

    def _build_safe_prompt(self, conversation: str, existing_memories: str = "") -> str:
        """构建安全的prompt"""
        memory_context = f"""
当前已有记忆：
{existing_memories}
""" if existing_memories else ""
        
        return f"""
{memory_context}
请从以下对话中提取关键信息，返回JSON格式：
{{
    "user_info": {{
        "name": "用户姓名",
        "preferences": ["偏好1", "偏好2"]
    }},
    "knowledge": ["知识点1", "知识点2"],
    "facts": ["事实1", "事实2"]
}}

对话内容：
{conversation}

要求：
1. 对比新旧信息，更新过时或矛盾的记忆
2. 忽略已存在的重复信息
3. 需要返回以前有的记忆点和新的记忆点
4. 只有你觉得最重要的部分才记下来，如果这个内容不重要，就不要记下来，这是一个长时记忆系统，只记忆重点，总结要言简意赅
"""

    def _parse_response(self, response: str) -> List[MemoryItem]:
        """解析API响应"""
        try:
            data = json.loads(response)
            memories = []
            
            if "user_info" in data:
                for key, values in data["user_info"].items():
                    if isinstance(values, list):
                        for value in values:
                            memories.append(
                                MemoryItem(category="user_info", key=key, value=value))
            
            for category in ["knowledge", "facts"]:
                if category in data and isinstance(data[category], list):
                    for value in data[category]:
                        memories.append(MemoryItem(category=category, value=value))
            
            return memories
        except Exception as e:
            raise ValueError(f"响应解析失败: {str(e)}")

    def get_memories(self, category: str, key: str = None) -> List[str]:
        """获取指定类型的记忆"""
        return [
            item.value for item in self.memories
            if item.category == category and (key is None or item.key == key)
        ]

    def clear_memories(self, category: str = None) -> bool:
        """清空记忆"""
        if category:
            self.memories = [m for m in self.memories if m.category != category]
        else:
            self.memories = []
        self.save_memories()
        return True

    def export_to_txt(self, filepath: str) -> bool:
        """导出记忆为可读文本"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("=== 长时间记忆摘要 (作为长时记忆，在对话中仅作为参考，在更新记忆时，需要作为历史记忆考虑,knowledge中的内容是聊天时聊到的一些概念，参考意义不大)===\n\n")
                for category in {"user_info", "knowledge", "facts"}:
                    items = [m for m in self.memories if m.category == category]
                    if items:
                        f.write(f"【{category}】\n")
                        for item in items:
                            key_part = f"{item.key}:" if item.key else ""
                            f.write(f"- {key_part} {item.value}\n")
                        f.write("\n")
            return True
        except Exception as e:
            print(f"导出失败: {str(e)}")
            return False
