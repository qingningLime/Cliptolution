import os
import shutil
import subprocess
import json
from pathlib import Path
from typing import Dict
from mcp_server import register_tool

def get_video_metadata(video_path: str) -> Dict:
    """获取视频元数据"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=codec_name,pix_fmt,width,height,r_frame_rate',
        '-of', 'json',
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise Exception(f"无法获取视频元数据: {result.stderr.decode()}")
    return json.loads(result.stdout.decode())['streams'][0]

def apply_color_grading(input_video: str, lut_file: str, output_path: str) -> Dict:
    """应用LUT调色到视频文件
    
    Args:
        input_video: 输入视频路径
        lut_file: LUT文件路径
        output_path: 输出文件路径
        
    Returns:
        dict: 标准响应格式 {
            "success": bool,
            "result": str or None,
            "error": str or None
        }
    """
    try:
        metadata = get_video_metadata(input_video)
        is_10bit = '10' in metadata['pix_fmt']
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-loglevel", "info",  # 显示详细输出
            "-hwaccel", "auto",
            "-i", input_video,
            "-vf", f"lut3d=file='{Path(lut_file).as_posix()}'",
            "-c:v", "hevc_amf",
            "-profile:v", "main10" if is_10bit else "main",
            "-usage", "transcoding",
            "-quality", "quality",
            "-rc", "cqp",
            "-qp_i", "18",
            "-qp_p", "18",
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-y",  # 自动覆盖输出文件
            output_path
        ]
        
        # 捕获并忽略所有输出
        result = subprocess.run(
            ffmpeg_cmd, 
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        return {
            "success": True,
            "result": output_path,
            "error": None
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "result": None,
            "error": f"视频处理失败: {e.stderr}"
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"处理错误: {str(e)}"
        }

@register_tool(
    tool_name="color_grading",
    description="使用LUT文件对视频进行调色处理",
    parameters={
        "video_path": {
            "type": "string", 
            "description": "输入视频完整路径"
        },
        "lut_path": {
            "type": "string", 
            "description": "LUT文件完整路径"
        },
        "output_dir": {
            "type": "string", 
            "description": "输出目录(默认为 'ai_output')",
            "default": "ai_output"
        }
    },
    timeout=600,
    category="action"  # 明确指定为action类工具
)
def color_grading(
    video_path: str, 
    lut_path: str,
    output_dir: str = "ai_output"
) -> Dict:
    """视频调色工具
    
    Args:
        video_path: 输入视频路径
        lut_path: LUT文件完整路径
        output_dir: 输出目录(默认为 'ai_output')
        
    Returns:
        dict: 标准响应格式 {
            "success": bool, 
            "result": str or None, 
            "error": str or None
        }
    """
    try:
        # 准备临时目录
        temp_dir = Path("video/tmp/color_grading/")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 处理视频文件
        video_file = Path(video_path)
        temp_video = temp_dir / f"temp_video{video_file.suffix}"
        shutil.copy2(video_file, temp_video)
        
        # 处理LUT文件
        lut_file = Path(lut_path)
        if not lut_file.exists():
            return {
                "success": False,
                "result": None,
                "error": f"LUT文件不存在: {lut_file}"
            }
        temp_lut = temp_dir / "temp_lut.cube"
        # 确保目标目录存在
        temp_lut.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lut_file, temp_lut)
        
        # 准备输出路径
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(exist_ok=True)
        output_file = output_dir_path / f"{video_file.stem}_graded_{lut_file.stem}{video_file.suffix}"
        
        # 如果输出文件已存在则删除
        if output_file.exists():
            output_file.unlink()
        
        # 执行调色处理并直接返回结果
        result = apply_color_grading(str(temp_video), str(temp_lut), str(output_file))
        
        # 清理临时文件
        shutil.rmtree(temp_dir)
        return result
        
    except Exception as e:
        # 确保临时文件被清理
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return {
            "success": False,
            "result": None,
            "error": f"工具执行失败: {str(e)}"
        }
