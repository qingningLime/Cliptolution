import asyncio
import os
import httpx
import json
from enum import Enum, auto
from multiprocessing import Process
from typing import Optional, Dict, Any, List
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from api_client import DeepSeekClient
from tools.tool_recognizer import ToolRecognizer
from creative.src.creative_processor import CreativeProcessor
from creative.src.creative_detector import detect_creative_request
from creative.src.creative_step_processor import CreativeStepProcessor, in_creative_workflow
from config_loader import config

class AgentState(Enum):
    IDLE = auto()
    PROCESSING = auto()
    TOOL_EXECUTING = auto()
    WAITING_INPUT = auto()

class AIAgent:
    def __init__(self, api_key: str = None):
        self.state = AgentState.IDLE
        self.short_memory = ShortTermMemory()
        self.long_memory = LongTermMemory(api_key) if api_key else None
        self.api_key = api_key
        self.is_active = False
        self.mcp_process = None
        if api_key:
            self.client = DeepSeekClient(api_key)
            self.creative_processor = CreativeProcessor(api_key)  # 新增创意处理器
        self.memory_context = self._load_memory_context()
        self._register_core_tools()

    def _load_memory_context(self) -> str:
        try:
            with open("memories.txt", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "无历史记忆"

    def start_mcp_server(self):
        from mcp_server import start_server
        self.mcp_process = Process(target=start_server)
        self.mcp_process.start()
        print(f"MCP服务器已启动 (PID: {self.mcp_process.pid})")

    def stop_mcp_server(self):
        if self.mcp_process and self.mcp_process.is_alive():
            self.mcp_process.terminate()
            self.mcp_process.join()
            print("MCP服务器已停止")

    def _register_core_tools(self):
        """工具注册现在完全由MCP服务器处理"""
        pass

    async def chat(self, user_input: str) -> str:
        # 首先检查是否在创意工作流中
        if in_creative_workflow():
            print("[创意模式] 检测到创意工作流交互")
            processor = CreativeStepProcessor(self.api_key)
            response = await processor.process_step_response(user_input)
            self.short_memory.add_interaction(user_input, response)
            return response
            
        # 判断是否为创意请求
        if hasattr(self, 'creative_processor'):
            # 使用新的创意检测函数
            is_creative = await detect_creative_request(self.client, user_input)
            if is_creative:
                print("[创意模式] 检测到创意设计请求")
                # 交给创意处理器处理
                response = await self.creative_processor.handle_request(user_input)
                # 更新记忆
                self.short_memory.add_interaction(user_input, response)
                return response

        # 保存用户输入（初始无响应）
        self.short_memory.add_interaction(user_input, "")
        print(f"[调试] 短期记忆状态(处理前): {self.short_memory.get_context()}")
        
        try:
            print(f"\n[状态] 开始处理请求: {user_input}")
            
            # 获取完整上下文
            full_context = self.short_memory.get_full_context()
            
            # 初始化工具识别器
            recognizer = ToolRecognizer(
                self.client, 
                self.short_memory,
                full_context=full_context
            )
            
            # 获取工具上下文
            tool_context = {
                **self.short_memory.get_tool_context(),
                "original_request": user_input
            }
            
            # 规划工具使用
            tool_plan = await recognizer.plan_tool_usage(user_input, tool_context)
            
            if not tool_plan.get("use_tool"):
                # 直接响应
                response = await self.client.chat_completion(
                    messages=[
                        {
                            "role": "system", 
                            "content": f"{self.memory_context}\n当前对话上下文:\n{self.short_memory.get_context()}\n请直接回复用户，不需要使用工具"
                        },
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0.7
                )
                # 更新记忆中的AI响应
                self.short_memory.add_interaction(user_input, response)
                print(f"[调试] 短期记忆状态(更新后): {self.short_memory.get_context()}")
                return response
            
            # 执行工具链
            MAX_TOOL_CHAIN = 15  # 最大工具链深度
            tool_chain_count = 0
            final_response = None
            current_tool = tool_plan
            tool_results = []  # 存储所有工具结果
            
            while tool_chain_count < MAX_TOOL_CHAIN and current_tool.get("use_tool"):
                print(f"[状态] 执行工具: {current_tool['tool_name']}")
                tool_result = await recognizer.execute_tool(
                    current_tool["tool_name"],
                    current_tool["arguments"],
                    decision_info=current_tool
                )
                print(f"返回: {tool_result}")  # 新增调试输出
                
                # 记录工具结果
                tool_results.append({
                    "tool_name": current_tool["tool_name"],
                    "arguments": current_tool["arguments"],
                    "result": tool_result
                })
                
                # 记录工具调用到短期记忆
                self.short_memory.add_interaction(
                    user_input, "",
                    tool_call={
                        "tool_name": current_tool["tool_name"],
                        "arguments": current_tool["arguments"],
                        "result": tool_result
                    }
                )
                
                # 更新工具上下文
                tool_context = {
                    **self.short_memory.get_tool_context(),
                    "original_request": user_input
                }
                
                # 评估工具结果
                assessment = await recognizer.assess_tool_result(
                    current_tool["tool_name"],
                    tool_result,
                    tool_context
                )
                
                if assessment["is_complete"]:
                    # 生成最终响应
                    final_response = await recognizer.generate_response(
                        tool_results,
                        tool_context
                    )
                    break
                    
                # 规划下一步工具
                next_tool = await recognizer.plan_next_tool(assessment, tool_context)
                current_tool = {
                    "use_tool": True,
                    "tool_name": next_tool["tool_name"],
                    "arguments": next_tool["arguments"],
                    "reason": next_tool["reason"],
                    "next_step": assessment.get("missing_info", "")
                }
                tool_chain_count += 1
            
            # 处理工具链超限情况
            if not final_response:
                final_response = "工具调用链过长，已中断。请简化您的请求。"
            
            # 更新记忆并返回最终响应
            self.short_memory.add_interaction(user_input, final_response)
            return final_response
                
        except Exception as e:
            error_msg = f"抱歉，处理您的请求时遇到问题: {str(e)}"
            self.short_memory.add_interaction(user_input, error_msg)
            return error_msg

    async def start(self):
        self.start_mcp_server()
        self.is_active = True
        
        print("AI Agent已启动，输入'exit'退出")
        while self.is_active:
            try:
                user_input = input("你: ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    await self.end_conversation()
                    break
                    
                response = await self.chat(user_input)
                print(f"AI: {response}")
                
            except KeyboardInterrupt:
                await self.end_conversation()
                break
            except Exception as e:
                print(f"发生错误: {e}")

    async def end_conversation(self):
        if self.long_memory:
            conversation = self.short_memory.get_context()
            await self.long_memory.analyze_and_store(conversation)
            self.long_memory.export_to_txt("memories.txt")
        
        self.stop_mcp_server()
        self.short_memory.clear()
        self.is_active = False

if __name__ == "__main__":
    api_key = config.get_deepseek_key() or os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("错误: 未配置DeepSeek API密钥，请设置config.json中的api_keys.deepseek或DEEPSEEK_API_KEY环境变量")
        exit(1)
    agent = AIAgent(api_key)
    asyncio.run(agent.start())
