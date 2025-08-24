import os
import subprocess
from typing import List, Dict
from pathlib import Path
from datetime import timedelta
from mcp_server import register_tool

def parse_time(time_input) -> str:
    """将时间输入转换为HH:MM:SS格式"""
    if isinstance(time_input, (int, float)):
        return str(timedelta(seconds=time_input))
    return time_input

@register_tool(
    tool_name="video_clipper",
    description="使用ffmpeg切割视频，实现视频剪辑功能，结束时间必须遵守格式，不可以用end",
    parameters={
        "input_path": {"type": "string", "description": "输入视频路径"},
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": ["string", "number"], "description": "开始时间(HH:MM:SS或秒数)"},
                    "end": {"type": ["string", "number"], "description": "结束时间(HH:MM:SS或秒数)"}
                },
                "required": ["start", "end"]
            }
        }
    },
    timeout=300,
    category="action"  # 明确指定为action类工具
)
async def video_clipper(input_path: str, segments: List[Dict]) -> dict:
    """视频切片工具
    
    Args:
        input_path: 输入视频路径
        segments: 切片时间点列表
        
    Returns:
        dict: 包含success, result, error的标准响应
    """
    try:
        # 验证输入文件
        if not os.path.exists(input_path):
            return {
                "success": False,
                "result": None,
                "error": f"输入视频文件不存在: {input_path}"
            }
        
        input_file = Path(input_path)
        output_files = []
        
        for i, segment in enumerate(segments, 1):
            try:
                start_time = parse_time(segment["start"])
                end_time = parse_time(segment["end"])
                
                # 构建输出文件名(保存到ai_output目录)
                output_dir = Path("ai_output")
                output_dir.mkdir(exist_ok=True)
                output_path = output_dir / f"{input_file.stem}_clip{i}{input_file.suffix}"
                
                # 构建ffmpeg命令
                cmd = [
                    "ffmpeg",
                    "-y",  # 覆盖输出文件
                    "-ss", start_time,
                    "-to", end_time,
                    "-i", str(input_file),
                    "-c", "copy",  # 使用原片质量
                    str(output_path)
                ]
                
                # 执行命令
                subprocess.run(cmd, check=True, capture_output=True)
                output_files.append(str(output_path))
                
            except Exception as e:
                return {
                    "success": False,
                    "result": None,
                    "error": f"切片失败(片段{i}): {str(e)}"
                }
        
        return {
            "success": True,
            "result": output_files,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"工具执行失败: {str(e)}"
        }
