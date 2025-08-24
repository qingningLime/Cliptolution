from mcp_server import register_tool
from pathlib import Path
import asyncio
import subprocess
from typing import List

@register_tool(
    tool_name="video_merger",
    description="按顺序合并多个视频文件",
    parameters={
        "video_paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "待合并视频路径列表(按顺序)"
        },
        "output_name": {
            "type": "string",
            "description": "输出文件名(不带后缀)"
        }
    },
    timeout=300,  # 视频处理可能需要较长时间
    category="action"  # 明确指定为action类工具
)
async def merge_videos(video_paths: List[str], output_name: str) -> dict:
    """合并多个视频文件
    
    Args:
        video_paths: 待合并视频路径列表(按顺序)
        output_name: 输出文件名(不带后缀)
        
    Returns:
        dict: 标准响应格式 {
            "success": bool,
            "result": {
                "output_path": str  # 合并后视频路径
            },
            "error": str  # 错误信息(失败时)
        }
    """
    try:
        output_dir = Path("ai_output")
        output_dir.mkdir(exist_ok=True)
        
        # 生成FFmpeg输入文件列表
        list_file = output_dir / "merge_list.txt"
        with open(list_file, 'w', encoding='utf-8') as f:
            for path in video_paths:
                f.write(f"file '{Path(path).absolute()}'\n")

        # 设置输出路径
        output_path = output_dir / f"{output_name}_merged.mp4"

        # 执行FFmpeg合并命令
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c:v", "libx264",  # 统一视频编码
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",  # 统一音频编码
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await proc.communicate()
        
        if proc.returncode == 0:
            return {
                "success": True,
                "result": {
                    "output_path": str(output_path)
                },
                "error": None
            }
        else:
            return {
                "success": False,
                "result": None,
                "error": "FFmpeg合并失败"
            }
            
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"视频合并异常: {str(e)}"
        }
