from collections import deque
from typing import Tuple, Deque, List, Dict, Any
import json

class ShortTermMemory:
    """增强版短期记忆模块，支持工具调用历史记录"""
    
    def __init__(self, max_turns: int = 10):
        """初始化短期记忆
        Args:
            max_turns: 最大对话轮数
        """
        self.memory: Deque[Tuple[str, str]] = deque(maxlen=max_turns)
        self.tool_calls: List[Dict[str, Any]] = []  # 工具调用历史
        self.current_context: str = ""

    def add_interaction(self, user_input: str, ai_response: str, tool_call: Dict[str, Any] = None) -> None:
        """添加交互记录，可选记录工具调用
        Args:
            user_input: 用户输入
            ai_response: AI响应
            tool_call: 工具调用记录(包含tool_name, arguments, result)
        """
        self.memory.append((user_input, ai_response))
        if tool_call:
            self.tool_calls.append(tool_call)
        self._update_context()

    def _update_context(self) -> None:
        """更新当前对话上下文，包含工具历史"""
        dialog_ctx = "\n".join(
            f"User: {u}\nAI: {a}" for u, a in self.memory
        )
        tool_ctx = "\n".join(
            f"[工具] {t['tool_name']}({json.dumps(t['arguments'], ensure_ascii=False)}) -> 成功: {t['result']['success']}"
            for t in self.tool_calls[-5:]  # 保留最近5个工具调用
        )
        self.current_context = f"{dialog_ctx}\n\n工具历史:\n{tool_ctx}"

    def get_context(self) -> str:
        """获取完整对话上下文"""
        return self.current_context
        
    def get_full_context(self) -> str:
        """获取完整对话上下文（包含用户消息和工具历史）"""
        return self.current_context

    def get_tool_context(self) -> Dict[str, Any]:
        """获取工具调用上下文"""
        return {
            "tool_calls": self.tool_calls.copy(),
            "last_tool_result": self.tool_calls[-1]['result'] if self.tool_calls else None
        }

    def clear(self) -> None:
        """清空记忆"""
        self.memory.clear()
        self.tool_calls.clear()
        self.current_context = ""
