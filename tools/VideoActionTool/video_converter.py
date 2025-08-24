from mcp_server import register_tool
from pathlib import Path
import asyncio
import subprocess
from typing import Optional

@register_tool(
    tool_name="video_converter",
    description="将视频转换为指定格式",
    parameters={
        "input_path": {
            "type": "string",
            "description": "输入视频路径"
        },
        "output_name": {
            "type": "string",
            "description": "输出文件名(不带后缀)"
        },
        "format": {
            "type": "string",
            "enum": ["mp4", "mkv", "mov"],
            "default": "mp4",
            "description": "目标格式"
        },
        "resolution": {
            "type": "string",
            "description": "目标分辨率(如1920x1080)，可选"
        },
        "fps": {
            "type": "number",
            "description": "目标帧率，可选"
        }
    },
    timeout=300,  # 转码可能需要较长时间
    category="action"  # 明确指定为action类工具
)
async def convert_video(
    input_path: str,
    output_name: str,
    format: str = "mp4",
    resolution: Optional[str] = None,
    fps: Optional[float] = None
) -> dict:
    """转换视频格式
    
    Args:
        input_path: 输入视频路径
        output_name: 输出文件名(不带后缀)
        format: 目标格式(mp4/mkv/mov)
        resolution: 目标分辨率(可选)
        fps: 目标帧率(可选)
        
    Returns:
        dict: 标准响应格式 {
            "success": bool,
            "result": {
                "output_path": str  # 转换后视频路径
            },
            "error": str  # 错误信息(失败时)
        }
    """
    try:
        output_dir = Path("ai_output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{output_name}_converted.{format}"

        # 构建FFmpeg命令
        cmd = ["ffmpeg", "-i", str(Path(input_path).absolute())]
        
        # 添加视频处理参数
        if resolution:
            cmd.extend(["-vf", f"scale={resolution}"])
        if fps:
            cmd.extend(["-r", str(fps)])
            
        # 添加输出参数
        cmd.extend([
            "-c:v", "libx264",  # 使用H.264编码
            "-preset", "medium",
            "-crf", "23",  # 中等质量
            "-c:a", "copy",  # 直接复制音频流
            "-y",  # 覆盖输出文件
            str(output_path)
        ])
        
        # 执行转码命令
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
                "error": "FFmpeg转码失败"
            }
            
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"视频转码异常: {str(e)}"
        }
