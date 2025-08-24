from mcp_server import register_tool
from pathlib import Path
import time

@register_tool(
    tool_name="list_subtitles",
    description="列出项目已知的所有字幕文件地址",
    parameters={},
    timeout=3,  # 设置3秒超时
    category="list"  # 明确指定为list类工具
)
def list_subtitles() -> dict:
    """获取字幕目录下所有文件信息
    
    Returns:
        dict: 标准返回格式
        {
            "success": bool,
            "result": {
                "files": [{
                    "name": str,
                    "path": str
                }],
                "count": int
            },
            "error": str
        }
    """
    subtitles_dir = Path(__file__).parent.parent.parent / "video" / "subtitles"
    
    try:
        files = []
        for f in subtitles_dir.iterdir():
            if f.is_file():
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "path": str(f.absolute())
                })
        
        return {
            "success": True,
            "result": {
                "files": files,
                "count": len(files)
            },
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": str(e)
        }
