from mcp_server import register_tool
from pathlib import Path

@register_tool(
    tool_name="read_txt_file",
    description="读取TXT文件内容",
    parameters={
        "path": {"type": "string", "description": "文件路径"}
    },
    timeout=3,
    category="list"  # 明确指定为list类工具

)
def read_txt_file(path: str) -> dict:
    """读取指定路径的TXT文件内容
    
    Args:
        path: 文件路径
        
    Returns:
        dict: 包含success, result, error的标准响应
    """
    try:
        file_path = Path(path)
        with open(file_path, 'r', encoding='utf-8') as f:
            return {
                "success": True,
                "result": f.read(),
                "error": None
            }
    except FileNotFoundError:
        return {
            "success": False,
            "result": None,
            "error": f"文件不存在: {path}"
        }
    except PermissionError:
        return {
            "success": False,
            "result": None,
            "error": f"无权限读取文件: {path}"
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"读取文件失败: {str(e)}"
        }
