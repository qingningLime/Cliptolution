from pathlib import Path
import subprocess
import re

class SimpleVideoMerger:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path
        # 简化路径配置 - 只处理视频和背景音乐
        self.video_dir = Path("creative/temp/video").resolve()
        self.background_music = Path("creative/temp/Background_Music/PendingMusic.mp3").resolve()
        self.output_path = Path("creative/temp/merged_video.mp4").resolve()

    def merge(self) -> bool:
        """执行简化的视频合并流程（无旁白版本）"""
        try:
            # 第一步：合并视频片段
            if not self._merge_video_clips():
                return False
                
            # 第二步：添加背景音乐
            if not self._add_background_music():
                return False
            
            print("视频合并成功（无旁白版本）")
            return True
        except Exception as e:
            print(f"视频处理失败: {str(e)}")
            return False

    def _merge_video_clips(self) -> bool:
        """合并视频片段"""
        temp_output = self.output_path.parent / "temp_merged.mp4"
        list_path = self.video_dir / "concat_list.txt"
        
        try:
            # 检查是否有视频片段
            video_clips = list(self.video_dir.glob("clip_*.mp4"))
            if not video_clips:
                raise RuntimeError("没有找到视频片段文件")
            
            # 生成视频片段列表
            with open(list_path, 'w', encoding='utf-8') as f:
                for clip in sorted(video_clips):
                    f.write(f"file '{clip.name}'\n")
            
            # 执行合并
            merge_result = subprocess.run([
                self.ffmpeg,
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_path),
                "-c", "copy",
                str(temp_output)
            ], capture_output=True, text=True)
            
            if merge_result.returncode != 0:
                raise RuntimeError(f"视频合并失败: {merge_result.stderr}")
            
            print(f"临时合并文件已生成: {temp_output}")
            return True
        except Exception as e:
            print(f"视频合并失败: {str(e)}")
            return False
        finally:
            if list_path.exists():
                list_path.unlink()

    def _get_video_duration(self, video_path: Path) -> float:
        """获取视频时长(秒)"""
        result = subprocess.run([
            self.ffmpeg,
            "-i", str(video_path),
            "-hide_banner",
            "-f", "null",
            "-"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        full_output = result.stdout + "\n" + result.stderr
        match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", full_output)
        if not match:
            raise RuntimeError(f"无法获取视频时长信息，FFmpeg输出:\n{full_output}")
        
        return float(match.group(1)) * 3600 + float(match.group(2)) * 60 + float(match.group(3))

    def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频文件时长(秒)"""
        result = subprocess.run([
            self.ffmpeg,
            "-i", str(audio_path),
            "-hide_banner",
            "-f", "null",
            "-"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        full_output = result.stdout + "\n" + result.stderr
        match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", full_output)
        if not match:
            raise RuntimeError(f"无法获取音频时长信息，FFmpeg输出:\n{full_output}")
        
        return float(match.group(1)) * 3600 + float(match.group(2)) * 60 + float(match.group(3))

    def _add_background_music(self) -> bool:
        """添加背景音乐（直接替换音频，视频时长取决于音频时长）"""
        temp_output = self.output_path.parent / "temp_merged.mp4"
        if not temp_output.exists():
            print(f"错误：合并后的视频文件不存在: {temp_output}")
            return False

        if not self.background_music.exists():
            print(f"警告：背景音乐文件不存在: {self.background_music}")
            # 如果没有背景音乐，直接复制视频到最终输出
            import shutil
            shutil.copy2(str(temp_output), str(self.output_path))
            temp_output.unlink()
            return True

        # 获取音频时长
        music_duration = self._get_audio_duration(self.background_music)
        
        # 直接使用背景音乐替换音频，视频时长取决于音频时长
        result = subprocess.run([
            self.ffmpeg,
            "-i", str(temp_output),
            "-i", str(self.background_music),
            "-map", "0:v",
            "-map", "1:a",
            "-t", str(music_duration),  # 设置输出时长为音频时长
            "-c:v", "copy",             # 视频编码器复制
            "-c:a", "aac", "-b:a", "192k",  # 音频重新编码为AAC
            "-y",
            str(self.output_path)
        ], capture_output=True, text=True)
        
        # 清理临时文件
        if temp_output.exists():
            temp_output.unlink()
        
        if result.returncode != 0:
            print(f"背景音乐添加失败: {result.stderr}")
            return False
        
        print(f"背景音乐添加成功，输出文件: {self.output_path}")
        print(f"视频时长已调整为音频时长: {music_duration:.2f}秒")
        return True
