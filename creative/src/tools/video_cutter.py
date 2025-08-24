import json
import subprocess
from pathlib import Path
import re
from typing import Optional

class VideoCutter:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path
    
    def _extract_json(self, content: str) -> Optional[dict]:
        """从混杂内容中提取JSON数据"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
            
        # 尝试提取代码块中的JSON
        code_blocks = re.findall(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
        if code_blocks:
            try:
                return json.loads(code_blocks[0])
            except json.JSONDecodeError:
                pass
                
        # 尝试提取最长的疑似JSON内容
        json_candidates = re.findall(r'\{.*?\}', content, re.DOTALL)
        if json_candidates:
            # 按长度排序，优先尝试最长的
            json_candidates.sort(key=len, reverse=True)
            for candidate in json_candidates:
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                    
        return None

    def cut_video(self, instruction_path: Path, output_dir: Path, use_gpu: bool = True):
        """增强版的视频切割方法"""
        with open(instruction_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        instructions = self._extract_json(content)
        if not instructions:
            raise ValueError("无法从输入内容中提取有效的JSON指令")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, clip in enumerate(instructions["clips"]):
            output_path = output_dir / f"clip_{i:03d}.mp4"
            source_path = str(Path("video/input") / clip["source"])
            
            # 验证时间格式 (HH:MM:SS.ms)
            if not self._validate_time_format(clip["start"]) or not self._validate_time_format(clip["end"]):
                raise ValueError(f"无效时间格式: {clip['start']} 或 {clip['end']}")
            
            if use_gpu:
                try:
                    # 尝试HEVC_AMF编码
                    self._encode_with_hevc_amf(source_path, clip, output_path)
                    continue
                except Exception as e:
                    print(f"HEVC_AMF编码失败: {str(e)}, 尝试H264_AMF")
                    
                try:
                    # 回退到H264_AMF
                    self._encode_with_h264_amf(source_path, clip, output_path)
                    continue
                except Exception as e:
                    print(f"H264_AMF编码失败: {str(e)}, 回退到CPU编码")
            
            # 最终回退到CPU编码
            self._encode_with_cpu(source_path, clip, output_path)
    
    def _encode_with_hevc_amf(self, input_file: str, clip: dict, output_file: Path):
        cmd = [
            self.ffmpeg,
            '-hwaccel', 'cuda',
            '-hwaccel_device', '1',
            '-ss', clip["start"],
            '-to', clip["end"],
            '-i', input_file,
            '-c:v', 'hevc_amf',
            '-quality', 'balanced',
            '-rc', 'cqp',
            '-qp_i', '18',
            '-qp_p', '18',
            '-c:a', 'aac',
            '-b:a', '192k',
            str(output_file)
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0:
            raise RuntimeError(f"HEVC编码失败: {result.stderr}")
    
    def _encode_with_h264_amf(self, input_file: str, clip: dict, output_file: Path):
        cmd = [
            self.ffmpeg,
            '-hwaccel', 'auto',
            '-hwaccel_device', '0',
            '-ss', clip["start"],
            '-to', clip["end"],
            '-i', input_file,
            '-pix_fmt', 'yuv420p',
            '-c:v', 'h264_amf',
            '-quality', 'balanced',
            '-rc', 'cqp',
            '-qp_i', '18',
            '-qp_p', '18',
            '-c:a', 'aac',
            '-b:a', '192k',
            str(output_file)
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0:
            raise RuntimeError(f"H264编码失败: {result.stderr}")
    
    def _encode_with_cpu(self, input_file: str, clip: dict, output_file: Path):
        cmd = [
            self.ffmpeg,
            "-i", input_file,
            "-ss", clip["start"],
            "-to", clip["end"],
            "-c:v", "libx264", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-y",
            str(output_file)
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0:
            raise RuntimeError(f"CPU编码失败: {result.stderr}")
    
    def _validate_time_format(self, time_str: str) -> bool:
        """验证时间格式 (HH:MM:SS.ms)"""
        return re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3}$", time_str) is not None
