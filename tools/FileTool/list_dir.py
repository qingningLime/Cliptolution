from mcp_server import register_tool
import os
import sys

@register_tool(
    tool_name="list_dir",
    description="列出目录内容，支持中文路径",
    parameters={
        "path": {"type": "string", "description": "目录路径"}
    },
    timeout=3,
    category="list"  # 明确指定为list类工具
)
def list_dir(path: str) -> dict:
    """列出目录内容，支持中文路径"""
    try:
        # Windows系统直接使用UTF-8路径
        if sys.platform == 'win32':
            path = path  # 保持原样
        else:
            path = path.encode('utf-8').decode('utf-8')
        
        if not os.path.exists(path):
            return {
                "success": False,
                "error": f"路径不存在: {path}",
                "result": None
            }
        if not os.path.isdir(path):
            return {
                "success": False,
                "error": f"不是目录: {path}",
                "result": None
            }
            
        entries = []
        for entry in os.scandir(path):
            try:
                entries.append(entry.name)
            except Exception as e:
                entries.append(f"错误: 无法读取条目 {entry.path}: {str(e)}")
        
        return {
            "success": True,
            "result": entries,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "result": None
        }
