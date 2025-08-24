from mcp_server import register_tool
from pathlib import Path

# 使用相对于当前文件的路径
VIDEO_RELATIVE_PATH = "../../video/input"  # 从tools/VideoListTool到video/input

@register_tool(
    tool_name="list_videos",
    description="列出你了解视频的地址",
    parameters={},
    timeout=3,
    category="list"
)
def list_videos() -> dict:
    """获取视频输入目录下所有视频文件信息(使用相对路径)
    
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
    try:
        # 构建绝对路径
        videos_dir = (Path(__file__).parent / VIDEO_RELATIVE_PATH).resolve()
        
        if not videos_dir.exists():
            return {
                "success": False,
                "error": f"视频目录不存在: {videos_dir}"
            }
            
        videos = [
            {"name": f.name, "path": str(f.relative_to(Path.cwd()))}
            for f in videos_dir.glob("*")
            if f.suffix.lower() in {'.mkv', '.mp4', '.avi', '.mov'}
        ]
        
        return {
            "success": True,
            "result": {
                "files": videos,
                "count": len(videos)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
