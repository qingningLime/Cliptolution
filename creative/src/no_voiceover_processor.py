from pathlib import Path
from api_client import DeepSeekClient
from music.src.convertmusic import convert_to_mp3
import asyncio
import shutil
import subprocess
import json

class NoVoiceoverProcessor:
    def __init__(self, api_key: str):
        self.client = DeepSeekClient(api_key)
    
    async def _call_llm(self, prompt: str, temperature: float = 0.5) -> str:
        """调用大语言模型的通用方法"""
        response = await self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="deepseek-reasoner",
            temperature=temperature
        )
        return response
    
    async def _call_llm_for_deepseek_chat(self, prompt: str, temperature: float = 0.5) -> str:
        """专门为生成剪辑指令调用大语言模型的方法，使用deepseek-chat模型"""
        response = await self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="deepseek-chat",
            temperature=temperature
        )
        return response
    
    async def process(self, target_content: str) -> str:
        """独立处理无口播视频的主方法（简化版）"""
        # 1. 处理背景音乐
        await self._process_background_music(target_content)
        
        # 2. 总结用户需求（可选）
        await self._summarize_user_requirements()
        
        # 3. 生成剪辑脚本
        await self._generate_preliminary_direction()

        # 清空CuttingOutput.md文件
        output_path = Path("creative/think_output/CuttingOutput.md")
        output_path.write_text("", encoding="utf-8")

        # 分三步生成详细分镜
        for step in range(3):
            await self._generate_detailed_storyboard(step)

        await self._generate_clip_instructions()
        

        # 4. 执行视频切割
        from .tools.video_cutter import VideoCutter
        cutter = VideoCutter()
        video_clips_dir = Path("creative/temp/video")
        video_clips_dir.mkdir(parents=True, exist_ok=True)
        instructions_path = Path("creative/temp/cut_instructions.json")
        cutter.cut_video(instructions_path, video_clips_dir)
        
        # 5. 视频合并（使用简化版本）
        from .tools.simple_video_merger import SimpleVideoMerger
        merger = SimpleVideoMerger()
        if not merger.merge():
            raise RuntimeError("视频合并失败")
        
        # 6. 添加字幕（背景音乐已在simple_video_merger中处理）
        await self._add_subtitles_only()
        
        # 7. 生成友好的最终回复
        final_video_path = Path("creative/final_output/video_final.mp4")
        final_response = await self._generate_friendly_response(final_video_path)
        
        # 8. 清理临时文件
        self._cleanup_files()
        
        return final_response

    async def _get_music_duration(self) -> float:
        """获取音乐文件的实际时长（秒）"""
        music_path = Path("creative/temp/Background_Music/PendingMusic.mp3")
        
        if not music_path.exists():
            raise FileNotFoundError(f"音乐文件不存在: {music_path}")
        
        # 使用 ffprobe 获取音乐时长
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(music_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            duration = float(data["format"]["duration"])
            return duration
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"无法获取音乐时长: {e}")

    async def _generate_preliminary_direction(self):
        """生成初步剪辑方向：将音乐分段并规划视频内容"""
        # 1. 读取各种输入文件
        read_path = Path("creative/think_output/read.md")
        temp_dir = Path("creative/temp")
        
        # 读取用户需求总结
        user_requirements = read_path.read_text(encoding="utf-8") if read_path.exists() else ""
        
        # 读取视频分析内容
        video_output = []
        for file in Path("video/output").glob("*"):
            if file.is_file() and file.suffix == ".txt":
                video_output.append(f"## {file.name}\n{file.read_text(encoding='utf-8')}")
        
        # 读取音乐相关文件
        music_report = (temp_dir / "Background_Music_report.txt").read_text(encoding="utf-8") \
            if (temp_dir / "Background_Music_report.txt").exists() else ""
        music_subtitles = (temp_dir / "Background_Music_subtitles.txt").read_text(encoding="utf-8") \
            if (temp_dir / "Background_Music_subtitles.txt").exists() else ""

        # 获取音乐实际时长
        music_duration = await self._get_music_duration()
        print(f"[DEBUG] 音频总时长: {music_duration} 秒")
        
        # 2. 构建提示词
        prompt = f"""
【剪辑脚本生成指令】
用户需要制作视频，需要你根据用户需求，把视频分析内容和已经选择的音乐的分析内容，
制作一个简单的剪辑脚本表格，以便用于指导剪辑。
请注意，我们只要求你制作一个简易的剪辑脚本表格，所以你需要你把音乐为三个部分（就是将几大段歌词合并为一个大模块），再根据模块编写对应的内容方向
【资料】
1. 用户需求总结：
{user_requirements}
用户希望这种一个这样的视频

2. 视频分析内容：
{'\n'.join(video_output)}
这是用于制作视频的视频素材

3. 音乐分析报告：
{music_report}
这是用于情感分析报告，可用于复制分析

4. 音乐字幕内容：
{music_subtitles}

5. 音频总时长：{music_duration}，单位s（秒）需要你进一位为整秒

【输出要求】
1. 将音乐平分为三个大模块，涵盖用户要求视频类型的叙事节奏，并且让输出的表格中可以了解用户希望表诉的视频内容，但是不允许在歌词中间切断
2. 输出格式为：
hh:mm:ss:ms~hh:mm:ss:ms
规划的内容：xxxxxxxxxxxxxxx（用300字描述这部分需要什么内容,并且用300字描述要使用什么场景剧情,不要局限于一个场景）
hh:mm:ss:ms~hh:mm:ss:ms
规划的内容：xxxxxxxxxxxxxxx（用300字描述这部分需要什么内容,并且用300字描述要使用什么场景剧情,不要局限于一个场景）
hh:mm:ss:ms~hh:mm:ss:ms
规划的内容：xxxxxxxxxxxxxxx（用300字描述这部分需要什么内容,并且用300字描述要使用什么场景剧情,不要局限于一个场景）
3. 时间格式：hh:mm:ss:ms
            时间转换公式：
            mm = INT(227.42/60)
            ss = INT(MOD(227.42,60))
            ms = (MOD(227.42,60) - INT(MOD(227.42,60))) * 1000
请使用音频分析文件提供的时间转换公式计算时间（这里的时间只是例子）
4. 将几大段歌词合并为一个大模块

时间轨道需要覆盖音频总时长，不能超出，也不能少于，要清楚歌词并不是歌曲的全部，只有音频长度才能保证整首歌的长度
时间轨道输出格式：【hh:mm:ss:ms-hh:mm:ss:ms】
5. 我们要求吧剧情爆点放在音乐的最后，这样可以尽可能保证用户观感觉，特别在中文歌曲中必须严格遵守
6. 只需要输出规划内容即可，不允许输出其他内容
8. 这里的平分是指尽可能根据时间绝对的平均分配，不能出现一个模块特别长，另外一个模块特别短的情况


"""
        
        # 3. 调用大模型生成结果
        result = await self._call_llm(prompt, temperature=0.7)
        
        # 4. 保存结果
        output_path = Path("creative/think_output/ReadingCut.md")
        output_path.write_text(result, encoding="utf-8")

    async def _summarize_user_requirements(self):
        """读取list.md并总结用户需求到read.md"""
        list_path = Path("creative/think_output/list.md")
        read_path = Path("creative/think_output/read.md")
        
        if not list_path.exists():
            return
            
        content = list_path.read_text(encoding="utf-8")
        
        prompt = f"""
请用一段话总结以下用户需求：
{content}

输出要求：
1. 简明扼要，不超过100字
2. 直接输出总结内容，不要额外说明
"""
        summary = await self._call_llm_for_deepseek_chat(prompt, temperature=0.5)
        
        read_path.write_text(summary, encoding="utf-8")
    
    async def _process_background_music(self, content: str):
        """处理背景音乐"""
        # 1. 选择音乐
        selected_music = await self._select_background_music(content)
        
        # 2. 准备临时目录
        temp_dir = Path("creative/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 3. 处理音乐文件
        music_path = temp_dir / "Background_Music"
        src_path = Path("music/MusicInput") / selected_music
        convert_to_mp3(str(src_path), str(music_path))
        
        # 4. 复制相关文件
        base_name = selected_music.split('.')[0]
        
        # 复制字幕文件
        subtitles_src = Path("music/MucicSubtitles") / f"{base_name}_subtitles.txt"
        subtitles_dest = temp_dir / "Background_Music_subtitles.txt"
        if subtitles_src.exists():
            shutil.copy2(subtitles_src, subtitles_dest)
            
        # 复制报告文件
        report_src = Path("music/report_output") / f"{base_name}_report.txt"
        report_dest = temp_dir / "Background_Music_report.txt"
        if report_src.exists():
            shutil.copy2(report_src, report_dest)
    
    async def _select_background_music(self, content: str) -> str:
        """选择背景音乐"""
        # 读取视频分析内容
        video_output = []
        for file in Path("video/output").glob("*"):
            if file.is_file() and file.suffix == ".txt":
                video_output.append(f"## {file.name}\n{file.read_text(encoding='utf-8')}")
        
        # 获取可用音乐列表
        music_files = [f.name for f in Path("music/MusicInput").glob("*") if f.is_file()]
        
        prompt = f"""
【背景音乐选择指令】
根据视频需求选择最合适的背景音乐，请注意，我们希望选择一首贴近用户期望的制作视频类型的音乐，一般用户会指定一个视频制作方向。
你需要选择一首合适的音乐

【输入内容】
1. 用户视频需求：
{content}

2. 视频分析内容：
{'\n'.join(video_output)}

3. 可用音乐文件：
{', '.join(music_files)}

【输出要求】
1. 直接输出最合适的音乐文件名（仅文件名，不要路径）
2. 不要任何额外说明或格式
"""
        return (await self._call_llm_for_deepseek_chat(prompt, temperature=0.7)).strip()
    
    async def _generate_detailed_storyboard(self, step_index: int):
        """生成详细分镜表：根据初步剪辑方向和歌词细化分镜（第{step_index + 1}步）"""
        # 1. 读取各种输入文件
        read_path = Path("creative/think_output/read.md")
        temp_dir = Path("creative/temp")
        
        # 读取用户需求总结
        user_requirements = read_path.read_text(encoding="utf-8") if read_path.exists() else ""
        
        # 读取视频分析内容
        video_output = []
        for file in Path("video/output").glob("*"):
            if file.is_file() and file.suffix == ".txt":
                video_output.append(f"## {file.name}\n{file.read_text(encoding='utf-8')}")
        
        # 读取音乐相关文件
        music_report = (temp_dir / "Background_Music_report.txt").read_text(encoding="utf-8") \
            if (temp_dir / "Background_Music_report.txt").exists() else ""
        music_subtitles = (temp_dir / "Background_Music_subtitles.txt").read_text(encoding="utf-8") \
            if (temp_dir / "Background_Music_subtitles.txt").exists() else ""
        
        # 读取初步剪辑方向
        reading_cut = Path("creative/think_output/ReadingCut.md").read_text(encoding="utf-8")

        # 获取音乐实际时长
        music_duration = await self._get_music_duration()
        print(f"[DEBUG] 音频总时长: {music_duration} 秒")

        # 2. 构建提示词
        prompt = f"""
【详细分镜生成指令 - 第{step_index + 1}模块】

现在我们已经拿到了初步剪辑的方向，现在需要按照这个方向规划的剧情方向细化第{step_index + 1}个模块的视频脚本

根据以下内容生成详细分镜表：

1. 用户需求总结：
{user_requirements}

2. 视频分析内容：
{'\n'.join(video_output)}

3. 音乐分析报告：
{music_report}

4. 音乐歌词内容：
{music_subtitles}

5. 初步剪辑方向：
{reading_cut}

6. 音频总时长：{music_duration}，单位s（秒）

【输出要求】
1. 基于初步剪辑方向，专注于第{step_index + 1}个模块的分镜细化
2. 将当前模块根据歌词拆分成小分镜，必须保证每一个小分镜都是一句完整的歌词，如果歌词时间过短，可以两三句歌词连起来作为一个小分镜，但是每一个小分镜的长度不得超过12秒
3. 每个小分镜能且只能对应一个原片素材，作为【文件名+时间码】，且【文件名+时间码】的长度必须等同于这个小分镜的时间长度
4. 强制要求:每一个【文件名+时间码】中的时间范围的长度必须与【时间轨道】中划分的时间长度完全一致：比如第一段旁白总长度是00:00:00-00:01:36（96秒），那么【文件名+时间码】中时间码划分的时间长度也必须是96秒。
5. 输出格式为Markdown表格：
| 时间轨道 | 对应歌词 | 文件名+时间码 |
|----------|----------|---------------|
| hh:mm:ss:ms~hh:mm:ss:ms | 这是一句歌词 | 文件名+时间码 |
(如果是第2个模块或者第3个模块，则不允许输出表头了)
6. 时间轨道格式：hh:mm:ss:ms
7. 使用时间转换公式计算时间：
   mm = INT(总秒数/60)
   ss = INT(MOD(总秒数,60))
   ms = (MOD(总秒数,60) - INT(MOD(总秒数,60))) * 1000
8. 【文件名+时间码】需要你标注完整的文件名与需要使用片段的开始时间~结束时间，时间格式hh:mm:ss:ms-hh:mm:ss:ms。
9.  每个模块的【时间轨道】必须覆盖到第{step_index + 1}个模块规划的时间
10. 细化的内容需要根据【初步剪辑方向】中第{step_index + 1}个模块规划的内容方向去写。
11. 只需要输出当前模块的表格即可，表格必须完整输出，不需要你节省输出
12. 不要包含其他模块的内容，只专注于当前模块
13. 不允许出现重复的原片素材，需要遵守第{step_index + 1}个模块规划的内容

输出前检查：
1. 每个小分镜能且只能对应一个原片素材，作为【文件名+时间码】，且每一个【文件名+时间码】中的时间范围的长度必须与【时间轨道】中划分的时间长度完全一致
2，【文件名+时间码】的时间码格式是否正确，必须为hh:mm:ss:ms-hh:mm:ss:ms且开始时间必须小于结束时间
"""
        ### 强制要求:【文件名+时间码】中的时间范围的长度必须与【时间轨道】中划分的时间长度完全一致：比如第一段旁白总长度是00:00:00-00:01:36（96秒），那么【文件名+时间码】划分的时间对应的长度也必须是96秒。不能多也不能少
        # 3. 调用大模型生成结果
        result = await self._call_llm(prompt, temperature=0.3)
        
        # 4. 保存结果（第一次覆写，后续追加）
        output_path = Path("creative/think_output/CuttingOutput.md")
        mode = "w" if step_index == 0 else "a"
        
        with open(output_path, mode, encoding="utf-8") as f:
            if step_index > 0:  # 从第二步开始添加分隔符
                f.write("\n")  # 添加空行分隔不同模块
            f.write(result)

    async def _generate_clip_instructions(self) -> str:
        """生成JSON剪辑指令"""
        # 读取详细分镜表
        cutting_output = Path("creative/think_output/CuttingOutput.md").read_text(encoding="utf-8")
        
        # 获取可用视频文件
        video_files = [f.name for f in Path("video/input").glob("*") if f.is_file()]
        
        # 构建提示词
        prompt = f"""
【视频剪辑指令生成】
根据剪辑脚本和可用视频文件，生成FFmpeg切割指令：

剪辑脚本：
{cutting_output}

可用视频文件：
{', '.join(video_files)}

输出要求：
1. 严格按JSON格式输出
2. 结构示例：
{{
  "clips": [
    {{"source": "视频1.mkv","start": "00:01:30.000","end": "00:01:45.500"}},
    // 更多片段...
  ]
}}
3. 时间格式必须为 HH:MM:SS.ms
4. 源文件输出名字即可
5. 只允许输出JSON内容，不要任何额外说明,也不允许出现诸如：“极速”这一类无关词语
6. 不允许出现Markdown格式的标注
7. 这只是格式整理而已，并不是真正的FFmpeg指令于工具调用
"""
        
        # 调用大模型生成结果
        result = await self._call_llm_for_deepseek_chat(prompt, temperature=0.2)
        
        # 保存JSON指令
        output_path = Path("creative/temp/cut_instructions.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        
        return result

    async def _add_subtitles_only(self):
        """只添加字幕到合并后的视频（背景音乐已在simple_video_merger中处理）"""
        root_temp = Path("temp").resolve()
        try:
            # 创建根目录temp文件夹
            root_temp.mkdir(exist_ok=True)
            
            # 复制视频到temp目录
            merged_video_path = Path("creative/temp/merged_video.mp4").resolve()
            if not merged_video_path.exists():
                raise FileNotFoundError(f"合并后的视频文件不存在: {merged_video_path}")
                
            temp_video = root_temp / "video.mp4"
            import shutil
            shutil.copy2(str(merged_video_path), str(temp_video))
            
            # 处理字幕文件
            subtitles_path = Path("creative/temp/Background_Music_subtitles.txt").resolve()
            if not subtitles_path.exists():
                raise FileNotFoundError(f"字幕文件不存在: {subtitles_path}")
                
            temp_sub = root_temp / "subtitle.srt"
            with open(temp_sub, 'w', encoding='utf-8', newline='\n') as f:
                f.write(self._convert_to_srt(subtitles_path))

            # 输出路径处理
            output_dir = Path("creative/final_output").resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "video_final.mp4"

            # 使用简单路径执行FFmpeg（与video_merger.py相同的字体样式）
            ffmpeg_cmd = [
                "ffmpeg",
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
            
            print(f"已添加字幕并输出到: {output_path}")
            
            # 复制视频到ai_output目录
            ai_output_dir = Path("ai_output").resolve()
            ai_output_dir.mkdir(parents=True, exist_ok=True)
            ai_output_path = ai_output_dir / "video_final.mp4"
            shutil.copy2(str(output_path), str(ai_output_path))
            print(f"已复制视频到: {ai_output_path}")
            
            return True
        except Exception as e:
            print(f"字幕添加异常: {str(e)}")
            return False
        finally:
            # 清理临时文件
            if 'temp_sub' in locals() and temp_sub.exists():
                temp_sub.unlink()
            if 'temp_video' in locals() and temp_video.exists():
                temp_video.unlink()

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

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """将秒数转换为SRT时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    async def _generate_friendly_response(self, video_path: Path) -> str:
        """生成友好的最终回复"""
        prompt = f"视频已成功生成，路径为：{video_path}。请用友好的语气告知用户。"
        return await self._call_llm_for_deepseek_chat(prompt, temperature=0.5)

    def _cleanup_files(self):
        """清理临时文件和输出文件内容"""
        try:
            # 1. 清理 creative\temp 文件夹内容（保留文件夹本身）
            temp_dir = Path("creative/temp")
            if temp_dir.exists():
                # 删除 temp 目录下的所有文件和子目录
                for item in temp_dir.iterdir():
                    if item.is_file():
                        item.unlink()  # 删除文件
                    elif item.is_dir():
                        shutil.rmtree(item)  # 删除目录及其内容
                # print(f"已清理 temp 文件夹内容: {temp_dir}")

            # 2. 清空 creative\think_output 目录下指定文件的内容（保留文件本身）
            think_output_files = [
                "AiAsk.md",
                "CuttingOutput.md", 
                "list.md",
                "read.md",
                "ReadingCut.md",
                "Target.md"
            ]
            
            think_output_dir = Path("creative/think_output")
            for filename in think_output_files:
                file_path = think_output_dir / filename
                if file_path.exists():
                    # 清空文件内容（写入空字符串）
                    file_path.write_text("", encoding="utf-8")
                    # print(f"已清空文件内容: {file_path}")

            # 3. 清理 creative\final_output 文件夹内容
            final_output_dir = Path("creative/final_output")
            if final_output_dir.exists():
                for item in final_output_dir.iterdir():
                    if item.is_file():
                        item.unlink()  # 删除文件
            #     print(f"已清理 final_output 文件夹内容: {final_output_dir}")

            # print("清理完成！")

        except Exception as e:
            print(f"清理文件时发生错误: {str(e)}")
            # 继续执行，不中断程序
