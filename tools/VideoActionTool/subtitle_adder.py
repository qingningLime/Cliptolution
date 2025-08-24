from mcp_server import register_tool
import subprocess
import os
import shutil
import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("subtitle_adder")

def convert_to_srt(input_path: str) -> str:
    """将原始字幕格式转换为标准SRT格式"""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        # 跳过文件开头的非字幕行
        subtitle_lines = [line for line in lines if line.startswith('[') and ']' in line]
        
        srt_lines = []
        counter = 1
        
        for line in subtitle_lines:
            # 提取时间部分和文本内容
            if ']:' not in line:
                continue
                
            time_part, text = line.split(']:', 1)
            time_part = time_part[1:]  # 去掉开头的[
            
            # 解析开始和结束时间
            if '-' not in time_part:
                continue
                
            start, end = time_part.split('-', 1)
            
            try:
                # 转换时间格式为SRT标准
                start_sec = float(start)
                end_sec = float(end)
                
                start_time = f"{int(start_sec//3600):02d}:{int(start_sec%3600//60):02d}:{int(start_sec%60):02d},{int(start_sec%1*1000):03d}"
                end_time = f"{int(end_sec//3600):02d}:{int(end_sec%3600//60):02d}:{int(end_sec%60):02d},{int(end_sec%1*1000):03d}"
                
                # 构建SRT块
                srt_lines.append(f"{counter}\n{start_time} --> {end_time}\n{text}\n\n")
                counter += 1
            except ValueError:
                logger.warning(f"跳过格式错误的时间戳行: {line}")
                continue
        
        return ''.join(srt_lines)
    except Exception as e:
        logger.error(f"字幕转换失败: {str(e)}")
        raise

def escape_ffmpeg_path(path: str) -> str:
    """转义FFmpeg路径中的特殊字符"""
    # 仅替换反斜杠为正斜杠，并用双引号包裹路径
    return f'"{path.replace("\\", "/")}"'

@register_tool(
    tool_name="add_subtitles",
    description="为视频添加字幕，需要提供视频完整路径和字幕文件名",
    parameters={
        "video_path": {
            "type": "string", 
            "description": "输入视频完整路径"
        },
        "subtitle_name": {
            "type": "string", 
            "description": "字幕文件名（不带扩展名，位于video/subtitles目录下）"
        },
        "output_dir": {
            "type": "string", 
            "description": "输出目录（默认为 'ai_output'）",
            "default": "ai_output"
        },
        "font_name": {
            "type": "string", 
            "description": "字幕字体（默认为 'SimHei'）",
            "default": "SimHei"
        },
        "font_size": {
            "type": "integer", 
            "description": "字幕大小（默认为 24）",
            "default": 24
        }
    },
    timeout=300,  # 设置5分钟超时
    category="action"  # 明确指定为action类工具
)
async def add_subtitles(
    video_path: str,
    subtitle_name: str,
    output_dir: str = "ai_output",
    font_name: str = "SimHei",
    font_size: int = 24
) -> dict:
    """
    为视频添加硬编码字幕
    
    Args:
        video_name: 输入视频文件名（不带扩展名）
        subtitle_name: 字幕文件名（不带扩展名）
        output_dir: 输出目录（默认为 'ai_output'）
        font_name: 字幕字体（默认为 'SimHei'）
        font_size: 字幕大小（默认为 24）
        
    Returns:
        dict: 标准响应格式 {
            "success": bool, 
            "result": dict or None, 
            "error": str or None
        }
    """
    try:
        # 获取项目根目录
        project_root = Path(__file__).parents[2]
        
        # 解析视频路径
        video_path = Path(video_path)
        if not video_path.exists():
            return {
                "success": False,
                "result": None,
                "error": f"视频文件不存在: {video_path}"
            }
            
        video_ext = video_path.suffix.lower()
        if video_ext not in ['.mp4', '.mkv', '.mov', '.avi']:
            return {
                "success": False,
                "result": None,
                "error": f"不支持的视频格式: {video_ext}"
            }
            
        video_name = video_path.stem
        subtitle_path = project_root / "video" / "subtitles" / f"{subtitle_name}.txt"
        
        # 验证字幕文件存在
        if not subtitle_path.exists():
            return {
                "success": False,
                "result": None,
                "error": f"字幕文件不存在: {subtitle_path}"
            }

        # 创建唯一ID用于临时文件命名
        unique_id = uuid.uuid4().hex[:8]
        
        # 创建临时工作目录
        temp_dir = project_root / f"temp_{unique_id}"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # 1. 复制视频到临时目录并重命名为简单名称(保留格式)
            temp_video = temp_dir / f"video{video_ext}"
            shutil.copy2(video_path, temp_video)
            
            # 2. 转换并保存字幕文件到临时目录(简单名称)
            srt_content = convert_to_srt(str(subtitle_path))
            temp_sub = temp_dir / "subtitle.srt"
            with open(temp_sub, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            # 3. 准备输出路径
            output_dir_path = project_root / output_dir
            os.makedirs(output_dir_path, exist_ok=True)
            
            # 输出文件名（保持原格式）
            output_filename = f"subtitled_{video_name}{video_ext}"
            output_path = output_dir_path / output_filename
            
            # 4. 构建FFmpeg命令(使用相对路径和简单文件名)
            cmd = [
                'ffmpeg',
                '-i', f'video{video_ext}',  # 临时目录中的简单文件名(保留格式)
                '-vf', f"subtitles='subtitle.srt':force_style='"
                       f"FontName={font_name},"
                       f"FontSize={font_size},"
                       f"Outline=1,"
                       f"PrimaryColour=&HFFFFFF'",
                '-c:a', 'copy',
                '-y',  # 覆盖输出文件（如果存在）
                str(output_path)  # 输出路径保持原样
            ]
            
            # 在临时目录中执行FFmpeg命令
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=temp_dir  # 关键：在临时目录中执行
            )
            
            # 等待进程完成并获取输出
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                error_msg = f"FFmpeg失败，返回码: {proc.returncode}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "result": None,
                    "error": error_msg
                }
            
            return {
                "success": True,
                "result": {
                    "output_path": str(output_path),
                    "video_name": output_filename
                },
                "error": None
            }
            
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        error_msg = f"字幕添加失败: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "result": None,
            "error": error_msg
        }
