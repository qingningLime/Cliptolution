from mcp_server import register_tool
from pathlib import Path

@register_tool(
    tool_name="write_file",
    description="写入文件内容",
    parameters={
        "path": {"type": "string", "description": "文件路径"},
        "content": {"type": "string", "description": "要写入的内容"}
    },
    timeout=3,
    category="list"  # 明确指定为list类工具
)
def write_file(path: str, content: str) -> dict:
    """写入文件内容
    
    Args:
        path: 文件路径
        content: 要写入的内容
        
    Returns:
        dict: 包含success, result, error的标准响应
    """
    try:
        # 确保目录存在
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {
            "success": True,
            "result": f"文件写入成功: {path}",
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"文件写入失败: {str(e)}"
        }
