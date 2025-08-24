import json
import os
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from api_client import DeepSeekClient

class ToolRecognizer:
    def __init__(self, client: DeepSeekClient, 
                 short_memory=None, full_context: str = ""):
        self.client = client
        self.short_memory = short_memory
        self.current_working_dir = os.getcwd()
        self.full_context = full_context
        self.mcp_client = httpx.AsyncClient(base_url="http://127.0.0.1:8001")

    async def execute_tool(self, tool_name: str, arguments: dict, decision_info: dict = None) -> dict:
        """通过MCP服务器执行工具"""
        print(f"[调试] 开始执行工具: {tool_name}")
        print(f"[调试] 工具参数: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
        if decision_info:
            print(f"[调试] 完整AI决策信息: {json.dumps(decision_info, indent=2, ensure_ascii=False)}")
        try:
            metadata = await self._get_tool_metadata(tool_name)
            is_long_running = metadata.get("timeout", 60) > 30
            
            if is_long_running:
                resp = await self.mcp_client.post(
                    f"/tools/{tool_name}",
                    json={
                        "tool_name": tool_name,
                        "arguments": arguments
                    }
                )
                task_data = resp.json()
                
                while True:
                    status_resp = await self.mcp_client.get(
                        f"/tasks/{task_data['task_id']}"
                    )
                    status = status_resp.json()
                    
                    if status["status"] in ["completed", "failed"]:
                        return {
                            "success": status["status"] == "completed",
                            "result": status.get("result"),
                            "error": status.get("error")
                        }
                    
                    await asyncio.sleep(1)
            else:
                resp = await self.mcp_client.post(
                    f"/tools/{tool_name}",
                    json={
                        "tool_name": tool_name,
                        "arguments": arguments
                    }
                )
                return resp.json()
                
        except Exception as e:
            print(f"[错误] 工具执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_tool_metadata(self, tool_name: str) -> dict:
        """获取工具元数据"""
        try:
            resp = await self.mcp_client.get(f"/tools/{tool_name}/metadata")
            return resp.json()
        except Exception as e:
            print(f"[警告] 获取工具元数据失败: {str(e)}")
            return {"timeout": 60, "category": "action"}

    async def plan_tool_usage(self, user_input: str, context: dict = None) -> Dict[str, Any]:
        """规划工具使用流程，考虑工具分类"""
        context = context or {}
        tool_history = "\n".join(
            f"工具 {i+1}: {call['tool_name']} 结果: {call.get('result', '')}"
            for i, call in enumerate(context.get('tool_calls', [])))
        
        system_prompt = f"""你是一个智能工具规划系统，请以json格式返回结果。请严格遵循以下规则：
1. 分析用户请求是否需要使用工具
2. 如果需要，规划第一个要调用的工具
3. 必须提供完整、具体的参数值
4. 考虑完整对话上下文中的信息
5. 注意工具分类(action/list):
   - action类: 执行操作(如编辑视频)
   - list类: 获取信息(如读取元数据)

完整对话上下文:
{self.full_context}

历史工具调用:
{tool_history}

当前工作目录: {self.current_working_dir}
可用工具:
{await self._get_mcp_tools_list()}

返回json格式:
{{
    "use_tool": boolean,
    "tool_name": string (仅当use_tool=true时),
    "arguments": object (仅当use_tool=true时),
    "reason": string,
    "next_step": string (描述下一步可能需要的工具)
}}"""

        try:
            response = await self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            if not isinstance(result, dict):
                raise ValueError("Invalid response format")
                
            if result.get("use_tool"):
                print(f"[调试] AI决定使用工具, 响应内容: {result}")
                
                if "tool_name" not in result:
                    raise ValueError("无效的工具调用格式: 缺少tool_name字段")
                
                mcp_tools = await self._get_mcp_tools_list()
                if not any(tool["name"] == result["tool_name"] for tool in mcp_tools):
                    raise ValueError(f"未知工具: {result['tool_name']}")
                
                print(f"[调试] 单工具调用: {result['tool_name']}")
                decision_info = {
                    "use_tool": True,
                    "tool_name": result["tool_name"],
                    "arguments": result.get("arguments", {}),
                    "reason": result.get("reason", "AI决策调用工具"),
                    "context_used": result.get("context_used", ""),
                    "next_step": result.get("next_step", "")
                }
                return decision_info
            return {"use_tool": False}
            
        except Exception as e:
            print(f"AI决策失败: {str(e)} - 使用默认无工具决策")
            return {"use_tool": False}

    async def assess_tool_result(self, tool_name: str, result: dict, context: dict) -> Dict[str, Any]:
        """评估工具结果是否完整，考虑工具类型"""
        metadata = await self._get_tool_metadata(tool_name)
        tool_type = metadata.get("category", "action")
        
        system_prompt = f"""请评估工具结果：
1. 工具是否成功执行
2. 结果是否足够回答原始用户问题
3. 是否需要更多工具调用来完成请求
4. 如果目前已知的所有工具实在无法完成请求，应当向用户说明并请求协助

原始用户请求: {context.get('original_request', '')}
当前工具: {tool_name} (类型: {tool_type})
工具结果: {json.dumps(result, indent=2)}

返回json格式:
{{
    "is_success": boolean,
    "is_complete": boolean,
    "assessment": "结果评估摘要",
    "missing_info": "如果结果不完整，描述缺失的信息"
}}"""
        
        try:
            response = await self.client.chat_completion(
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return json.loads(response)
        except Exception as e:
            return {
                "is_success": False,
                "is_complete": False,
                "assessment": f"评估失败: {str(e)}",
                "missing_info": ""
            }

    async def _get_mcp_tools_list(self) -> List[Dict[str, Any]]:
        """从MCP服务器获取工具列表（包含分类信息）"""
        try:
            resp = await self.mcp_client.get("/tools")
            tools_data = resp.json()
            return [
                {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"],
                    "category": tool_info.get("category", "action")
                }
                for tool_name, tool_info in tools_data.items()
            ]
        except Exception as e:
            print(f"[错误] 获取工具列表失败: {str(e)}")
            return []

    def process_tool_output(self, output):
        """处理工具输出，不做任何截断"""
        return output

    async def generate_response(self, tool_results: List[dict], context: dict) -> str:
        """根据所有工具结果生成用户友好响应"""
        processed_results = [
            {
                "tool_name": r["tool_name"],
                "result": self.process_tool_output(r["result"])
            }
            for r in tool_results
        ]
        
        results_str = "\n".join(
            f"工具 {i+1}: {r['tool_name']} 结果: {r['result']}"
            for i, r in enumerate(processed_results))
        
        system_prompt = f"""请根据以下工具结果生成用户友好的最终响应：
原始用户请求: {context.get('original_request', '')}
工具执行历史:
{results_str}
尽可能用自然语言进行回答，而不是输出Markdown格式的内容。
只需返回最终响应文本，不要包含任何JSON格式或额外说明。"""
        
        try:
            return await self.client.chat_completion(
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.7
            )
        except Exception as e:
            return f"无法生成响应: {str(e)}"

    async def plan_next_tool(self, assessment: dict, context: dict) -> Dict[str, Any]:
        """规划下一步工具调用，考虑工具分类"""
        system_prompt = f"""请规划下一步工具调用：
完整对话上下文:
{self.full_context}

原始用户请求: {context.get('original_request', '')}
当前评估: {assessment['assessment']}
缺失信息: {assessment['missing_info']}

可用工具(分类: action/list):
{await self._get_mcp_tools_list()}

返回json格式:
{{
    "tool_name": string,
    "arguments": object,
    "reason": string,
    "next_step": string
}}"""
        
        try:
            response = await self.client.chat_completion(
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            result = json.loads(response)
            return {
                "tool_name": result["tool_name"],
                "arguments": result["arguments"],
                "reason": result["reason"],
                "next_step": assessment.get("missing_info", "")
            }
        except Exception as e:
            return {
                "tool_name": "",
                "arguments": {},
                "reason": f"规划失败: {str(e)}",
                "next_step": ""
            }
