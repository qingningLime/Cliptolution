import asyncio
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime
import asyncio
from enum import Enum

app = FastAPI()

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ToolMetadata(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    timeout: int = 60  # 默认超时60秒
    category: str = "action"  # action/list

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    metadata: Optional[ToolMetadata] = None

class ToolResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    usage: Optional[Dict[str, int]] = None

# 工具注册表
TOOL_REGISTRY = {}

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: str
    tool_name: str
    arguments: dict
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

# 任务存储
TASK_STORE = {}

def register_tool(tool_name: str = None, description: str = "", parameters: dict = None, timeout: int = 60, category: str = "action"):
    """装饰器注册工具，包含元数据
    Args:
        tool_name: 工具名称
        description: 工具描述
        parameters: 工具参数定义
        timeout: 超时时间(秒)，默认60秒
        category: 工具类型(action/list)，默认action
    """
    def decorator(func):
        # 确保工具名称不为空
        final_name = tool_name or func.__name__
        
        # 注册工具
        TOOL_REGISTRY[final_name] = {
            "func": func,
            "metadata": {
                "name": final_name,
                "description": description,
                "parameters": parameters or {},
                "timeout": timeout,
                "category": category
            }
        }
        return func
    
    # 如果直接调用(非装饰器语法)，返回装饰后的函数
    if callable(tool_name):
        return decorator(tool_name)
    return decorator

@app.get("/tools/{tool_name}/metadata")
async def get_tool_metadata(tool_name: str):
    """获取工具元数据"""
    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail="Tool not found")
    return TOOL_REGISTRY[tool_name]["metadata"]

@app.get("/tools")
async def list_tools():
    """列出所有可用工具及其元数据"""
    return {
        tool: data["metadata"]
        for tool, data in TOOL_REGISTRY.items()
    }

async def run_tool_in_background(task_id: str, tool_name: str, arguments: dict):
    """后台执行工具任务"""
    tool_data = TOOL_REGISTRY[tool_name]
    task = TASK_STORE[task_id]
    
    try:
        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now()
        
        if asyncio.iscoroutinefunction(tool_data["func"]):
            result = await tool_data["func"](**arguments)
        else:
            # 同步函数在线程池中执行
            result = await asyncio.to_thread(tool_data["func"], **arguments)
            
        task.result = result
        task.status = TaskStatus.COMPLETED
    except Exception as e:
        task.error = str(e)
        task.status = TaskStatus.FAILED
    finally:
        task.updated_at = datetime.now()

@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, request: ToolRequest, background_tasks: BackgroundTasks):
    """执行工具端点"""
    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    tool_data = TOOL_REGISTRY[tool_name]
    timeout = tool_data["metadata"].get("timeout", 60)
    
    # 如果是长时间任务(超时>30秒)，使用异步模式
    if timeout > 30:
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            tool_name=tool_name,
            arguments=request.arguments,
            status=TaskStatus.PENDING
        )
        TASK_STORE[task_id] = task
        
        background_tasks.add_task(run_tool_in_background, task_id, tool_name, request.arguments)
        
        return {
            "task_id": task_id,
            "status": task.status,
            "message": "长时间任务已提交后台执行"
        }
    else:
        # 短时间任务直接执行
        try:
            import time
            start_time = time.time()
            
            if asyncio.iscoroutinefunction(tool_data["func"]):
                result = await asyncio.wait_for(
                    tool_data["func"](**request.arguments),
                    timeout=timeout
                )
            else:
                result = tool_data["func"](**request.arguments)
            
            return ToolResponse(
                success=True,
                result=result,
                execution_time=time.time() - start_time,
                usage={"calls": 1}
            )
        except asyncio.TimeoutError:
            return ToolResponse(
                success=False,
                result=None,
                error=f"工具执行超时({timeout}秒)",
                usage={"failed_calls": 1}
            )
        except Exception as e:
            return ToolResponse(
                success=False,
                result=None,
                error=str(e),
                usage={"failed_calls": 1}
            )

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in TASK_STORE:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = TASK_STORE[task_id]
    return {
        "task_id": task.id,
        "tool_name": task.tool_name,
        "status": task.status,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at,
        "updated_at": task.updated_at
    }

def import_tools():
    """自动导入tools目录下的所有工具"""
    import importlib
    from pathlib import Path
    import os
    
    # 扫描tools目录及其子目录下的所有.py文件
    tools_dir = Path(os.getcwd()) / "tools"
    for tool_file in tools_dir.rglob("*.py"):
        if tool_file.name == "__init__.py":
            continue
            
        # 计算相对路径并转换为模块路径
        rel_path = tool_file.relative_to(tools_dir.parent)
        module_path = str(rel_path.with_suffix('')).replace(os.sep, '.')
        
        print(f"正在导入工具模块: {module_path}")  # 调试输出
        
        # 根据路径自动设置工具类别
        tool_category = "action"
        if "VideoListTool" in str(rel_path):
            tool_category = "list"
        try:
            # 动态导入工具模块
            module = importlib.import_module(module_path)
            print(f"成功导入: {module_path}")
        except Exception as e:
            print(f"导入失败 {module_path}: {str(e)}")
    return

def start_server(host: str = "127.0.0.1", port: int = 8001):
    """启动MCP服务器"""
    import_tools()
    print("注册工具:")
    for tool_name in TOOL_REGISTRY:
        print(f"- {tool_name}")
    
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_server()
