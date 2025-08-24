from pathlib import Path
import subprocess
import re

class VideoMerger:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path
        # 固定路径配置
        self.video_dir = Path("creative/temp/video").resolve()
        self.voiceover = Path("creative/ReadingVoice/read.mp3").resolve()
        self.background_music = Path("creative/temp/Background_Music/PendingMusic.mp3").resolve()
        self.output_path = Path("creative/final_output/video_final.mp4").resolve()
        self.final_path = Path("ai_output/video_final.mp4").resolve()

        # 初始化时验证关键文件是否存在
        if not self.background_music.exists():
            raise FileNotFoundError(f"背景音乐文件不存在: {self.background_music}")
        if not self.voiceover.exists():
            raise FileNotFoundError(f"旁白文件不存在: {self.voiceover}")

    def _convert_to_srt(self, input_path: Path) -> str:
        """将原始字幕格式转换为SRT格式"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            subtitle_lines = [line for line in lines if line.startswith('[') and ']' in line]
            srt_lines = []
            counter = 1
            
            for line in subtitle_lines:
                if ']:' not in line:
                    continue
                time_part, text = line.split(']:', 1)
                time_part = time_part[1:]  # 去掉开头的[
                
                if '-' not in time_part:
                    continue
                start, end = time_part.split('-', 1)
                
                try:
                    start_sec = float(start)
                    end_sec = float(end)
                    start_time = f"{int(start_sec//3600):02d}:{int(start_sec%3600//60):02d}:{int(start_sec%60):02d},{int(start_sec%1*1000):03d}"
                    end_time = f"{int(end_sec//3600):02d}:{int(end_sec%3600//60):02d}:{int(end_sec%60):02d},{int(end_sec%1*1000):03d}"
                    srt_lines.append(f"{counter}\n{start_time} --> {end_time}\n{text}\n\n")
                    counter += 1
                except ValueError:
                    print(f"跳过格式错误的时间戳行: {line}")
                    continue
            return ''.join(srt_lines)
        except Exception as e:
            print(f"字幕转换失败: {str(e)}")
            raise

    def _add_subtitles(self) -> bool:
        """添加字幕并输出到ai_output"""
        root_temp = Path("temp").resolve()
        try:
            # 创建根目录temp文件夹
            root_temp.mkdir(exist_ok=True)
            
            # 复制视频到temp目录
            temp_video = root_temp / "video.mp4"
            if self.output_path.exists():
                import shutil
                shutil.copy2(str(self.output_path), str(temp_video))
            
            # 处理字幕文件
            subtitle_path = Path("creative/ReadingVoice/read.txt").resolve()
            if not subtitle_path.exists():
                print(f"字幕文件不存在: {subtitle_path}")
                return False
                
            temp_sub = root_temp / "subtitle.srt"
            with open(temp_sub, 'w', encoding='utf-8', newline='\n') as f:
                f.write(self._convert_to_srt(subtitle_path))

            # 输出路径处理
            output_dir = Path("ai_output").resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "video_final.mp4"

            # 使用简单路径执行FFmpeg
            ffmpeg_cmd = [
                self.ffmpeg,
                "-i", "temp/video.mp4",
                "-vf", "subtitles='temp/subtitle.srt':force_style='"
                       "FontName=SimHei,FontSize=24,"
                       "Outline=1,PrimaryColour=&HFFFFFF'",
                "-c:a", "copy",
                "-y", str(output_path)
            ]
            
            # 执行命令并检查结果
            result = subprocess.run(ffmpeg_cmd, cwd=root_temp.parent, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"字幕添加失败 - 命令: {' '.join(ffmpeg_cmd)}")
                print(f"错误输出: {result.stderr}")
                return False
            
            if result.returncode != 0:
                print(f"字幕添加失败: {result.stderr}")
                return False
            
            print(f"已添加字幕并输出到: {output_path}")
            return True
        except Exception as e:
            print(f"字幕添加异常: {str(e)}")
            return False
        finally:
            # 清理临时文件
            if 'temp_sub' in locals() and temp_sub.exists():
                temp_sub.unlink()

    def merge(self) -> bool:
        """执行分步视频合并流程"""
        try:
            # 第一步：合并视频片段
            if not self._merge_video_clips():
                return False
                
            # 第二步：添加旁白
            if not self._add_voiceover():
                return False
                
            # 第三步：添加背景音乐
            if not self._add_background_music():
                return False
            
            # 第四步：添加字幕并输出到ai_output
            if not self._add_subtitles():
                return False
            
            # 清理最终输出文件
            if self.output_path.exists():
                self.output_path.unlink()
                print(f"已清理最终输出文件: {self.output_path}")
                
            return True
        except Exception as e:
            print(f"视频处理失败: {str(e)}")
            return False
        

    def _merge_video_clips(self) -> bool:
        """合并视频片段"""
        temp_output = self.output_path.parent / "temp_merged.mp4"
        list_path = self.video_dir / "concat_list.txt"
        
        try:
            # 生成视频片段列表
            with open(list_path, 'w', encoding='utf-8') as f:
                for clip in sorted(self.video_dir.glob("clip_*.mp4")):
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
            
            print(f"临时合并文件已生成: {temp_output}")  # 调试输出
            return True
        except Exception as e:
            print(f"视频合并失败: {str(e)}")
            return False
        finally:
            list_path.unlink(missing_ok=True)
            print(f"已清理临时列表文件: {list_path}")  # 调试输出

    def _add_voiceover(self) -> bool:
        """添加旁白音频(原视频静音)"""
        temp_output = self.output_path.parent / "temp_merged.mp4"
        with_voiceover = self.output_path.parent / "with_voiceover.mp4"
        
        try:
            print(f"开始添加旁白，输入文件: {temp_output}")
            # 直接使用原始mp3文件，确保采样率匹配
            result = subprocess.run([
                self.ffmpeg,
                "-i", str(temp_output),
                "-i", str(self.voiceover),
                "-filter_complex", 
                "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.0[a]",
                "-map", "0:v",
                "-map", "[a]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-y",
                str(with_voiceover)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"旁白添加失败: {result.stderr}")
            
            print(f"旁白添加成功，输出文件: {with_voiceover}")
            return True
        except Exception as e:
            print(f"旁白添加失败: {str(e)}")
            with_voiceover.unlink(missing_ok=True)
            return False

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

    def _add_background_music(self) -> bool:
        """添加背景音乐（精确循环版）"""
        with_voiceover = self.output_path.parent / "with_voiceover.mp4"
        if not with_voiceover.exists():
            print(f"错误：旁白添加后的文件不存在: {with_voiceover}")
            return False

        video_duration = self._get_video_duration(with_voiceover)
        music_duration = self._get_audio_duration(self.background_music)
        
        # 计算需要的循环次数
        import math
        loop_count = math.ceil(video_duration / music_duration) if music_duration > 0 else 1
        
        # 构建动态concat滤镜（处理循环）
        filter_complex = ""
        if loop_count > 1:
            # 创建多个输入引用
            inputs = "".join([f"[1:a]volume=0.2,atrim=0:{music_duration},asetpts=PTS-STARTPTS[part{i}];" 
                             for i in range(loop_count)])
            concat_inputs = "".join([f"[part{i}]" for i in range(loop_count)])
            filter_complex = (
                f"{inputs}"
                f"{concat_inputs}concat=n={loop_count}:v=0:a=1[bg];"
                f"[bg]atrim=0:{video_duration}[bg_trimmed];"
                f"[0:a][bg_trimmed]amix=inputs=2[a]"
            )
        else:
            # 单次播放（背景音乐可能长于视频）
            filter_complex = (
                f"[1:a]volume=0.2,atrim=0:{video_duration}[bg_trimmed];"
                f"[0:a][bg_trimmed]amix=inputs=2[a]"
            )
        
        result = subprocess.run([
            self.ffmpeg,
            "-i", str(with_voiceover),
            "-i", str(self.background_music),
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-y",
            str(self.output_path)
        ], capture_output=True, text=True)
        
        # 调试输出
        if result.returncode != 0:
            print(f"背景音乐添加失败: {result.stderr}")
        else:
            print(f"背景音乐添加成功，输出文件: {self.output_path}")
        
        # 清理中间文件
        temp_merged = self.output_path.parent / "temp_merged.mp4"
        if temp_merged.exists():
            temp_merged.unlink()
        if with_voiceover.exists():
            with_voiceover.unlink()
        
        return result.returncode == 0

    def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频文件时长(秒)"""
        result = subprocess.run([
            self.ffmpeg,
            "-i", str(audio_path),
            "-hide_banner",
            "-f", "null",
            "-"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # 合并stdout和stderr输出
        full_output = result.stdout + "\n" + result.stderr
        print(f"音频文件FFmpeg输出:\n{full_output}")  # 调试输出
        
        match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", full_output)
        if not match:
            raise RuntimeError(f"无法获取音频时长信息，FFmpeg输出:\n{full_output}")
        
        duration = float(match.group(1)) * 3600 + float(match.group(2)) * 60 + float(match.group(3))
        print(f"解析出的音频时长: {duration}秒")  # 调试输出
        return duration
