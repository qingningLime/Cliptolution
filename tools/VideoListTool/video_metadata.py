import json
import subprocess
from pathlib import Path
from mcp_server import register_tool

@register_tool(
    tool_name="video_metadata",
    description="获取视频时长和分辨率信息，如果你不清楚视频的结束时间，可以通过该工具查看",
    parameters={
        "video_path": {"type": "string", "description": "视频文件路径"}
    },
    timeout=30,
    category="list"  # 明确指定为list类工具
)
def get_video_metadata(video_path: str) -> dict:
    """获取视频基础元数据
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        dict: 包含success, result, error的标准响应
        result中包含path, duration, resolution字段
    """
    try:
        # 验证文件存在
        if not Path(video_path).exists():
            return {
                "success": False,
                "result": None,
                "error": f"视频文件不存在: {video_path}"
            }

        # 使用ffprobe获取元数据
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # 提取关键信息
        stream = data["streams"][0]
        duration = float(stream["duration"])
        resolution = f"{stream['width']}x{stream['height']}"

        return {
            "success": True,
            "result": {
                "path": video_path,
                "duration": duration,
                "resolution": resolution
            },
            "error": None
        }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "result": None,
            "error": f"ffprobe执行失败: {e.stderr}"
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"元数据解析失败: {str(e)}"
        }
