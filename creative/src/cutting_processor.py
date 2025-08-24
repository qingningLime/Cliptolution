from pathlib import Path
import asyncio
import json
from typing import Optional
from api_client import DeepSeekClient

class CuttingProcessor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = DeepSeekClient(api_key)
    
    async def _call_llm(self, prompt: str) -> str:
        """调用大语言模型的通用方法"""
        response = await self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="deepseek-reasoner",
            temperature=0.7
        )
        return response

    async def generate_reading_cut(self) -> str:
        """
        步骤1：生成ReadingCut.md
        读取read.md和read.txt，生成剪辑脚本表格
        """
        try:
            subtitles = Path("creative/ReadingVoice/read.txt").read_text(encoding="utf-8")
            
            prompt = f"""
            【任务说明】
            需要将口播稿和字幕内容整理为剪辑脚本表格

            【输入内容】
            字幕内容：
            {subtitles}

            我们需要你结合已经配音好的旁白（以字幕形式），编写视频剪辑脚本，并且按照如下格式输出：
            | 时间轨道 | 旁白内容 |
            |--------|----------|
            必须严格按照要求，事关剪辑自动化：
            1，将旁白内容分成一个一个由几个句子组成的片段（比如整一段话作为一个片段，需要把相邻的句子连起来，输出时【旁白内容】必须缩写，缩写成头一句尾一句即可，每一段不得低于16秒）
            注意，如果字幕时长大于15分钟，你可以分为1到2分钟一段
            2，【时间轨道】必须连贯，且必须与旁白内容对应，不允许在句子中间断开。
            3，输入的时间格式是秒的格式，你必须对时间进行转换，比如227.42(s)需要转换成03:47:42(mm:ss:ms)
            时间转换公式：
            mm = INT(227.42/60)
            ss = INT(MOD(227.42,60))
            ms = (MOD(227.42,60) - INT(MOD(227.42,60))) * 1000
            4. 必须确保时间轨道总时长=字幕总时长，不多不少
            5. 只输出表格即可，必须确保表格完整性

            格式：
            | 时间轨道 | 旁白内容 |
            |--------|----------|
            |00:00:00-00:12:36|当镜头扫过...社交天赋|
            """
            
            response = await self._call_llm(prompt)
            output_path = Path("creative/think_output/ReadingCut.md")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(response, encoding="utf-8")
            return response
        except Exception as e:
            print(f"生成ReadingCut.md失败: {str(e)}")
            raise

    async def generate_cutting_output(self) -> str:
        """
        步骤2：生成CuttingOutput.md
        整合多个文件生成详细剪辑脚本
        """
        try:
            # 读取所有输入文件
            reading_cut = Path("creative/think_output/ReadingCut.md").read_text(encoding="utf-8")
            script = Path("creative/think_output/read.md").read_text(encoding="utf-8")
            list_md = Path("creative/think_output/list.md").read_text(encoding="utf-8")
            
            # 读取video/output下所有文本文件
            video_output = []
            for file in Path("video/output").glob("*"):
                if file.is_file() and file.suffix == ".txt":
                    video_output.append(f"## {file.name}\n{file.read_text(encoding='utf-8')}")
            
            prompt = f"""
【任务说明】
需要整合多方内容生成详细剪辑脚本

【输入内容】
1. 初稿剪辑脚本：
{reading_cut}

2. 原始口播稿：
{script}

3. 用户需求：
{list_md}

4. 视频分析：
{'\n'.join(video_output)}

【输出要求】
我们需要你结合已经配音好的旁白（以字幕形式），用户期望制作的视频的需求，以及原视频素材的视频分析，编写视频剪辑脚本，并且按照如下格式输出：
   | 时间轨道 | 旁白内容 | 文件名+时间码 | 画面对应的内容|
   |--------|----------|-----------------------|----------|
必须严格按照要求，事关剪辑自动化：
1，可以将旁白内容分成一个一个片段（比如整一段话作为一个片段，输出时可以缩写），但是【文件名+时间码】所指向的片段时长必须与【时间轨道】的实际长度相同。一个【时间轨道】只能对应一个【文件名+时间码】。
2，画面对应内容应当是【文件名+时间码】片段所指向的内容，要求必须实事求是对应，可以只是简单描述
3，【时间轨道】必须连贯，且必须与旁白内容对应，不允许在句子中间断开。
4. 每一个【文件名+时间码】上的划分的时间长度必须与【时间轨道】的时长相同，比如第一段旁白总长度是00:00:00-00:01:36（96秒），那么【文件名+时间码】划分的时间对应的长度也必须是96秒。
4，所有的时间刻度都应该是hh:mm:ss:ms
5. 只输出表格内容，不要任何额外说明和内容
6. 【时间轨道】总长度必须与【初稿剪辑脚本】的轨道和旁白总时长相同


下面是格式示例：
| 时间轨道              | 旁白内容                                     | 文件名+时间码                     | 画面对应的内容                  |

| 00:00:00:00-00:00:07:36 | 当镜头扫过羽丘女...最引人注目的存在。        | mygo1集 00:04:23:00-00:04:30:36 | 爱音作为转学生在讲台上鞠躬自我介绍 |
| 00:00:07:36-00:00:16:36 | 转学第一天就...请求共进午餐的模样，像只狡黠的狐狸。    | mygo1集 00:05:42:00-00:05:51:00    | 爱音双手合十请求同学共进午餐     |
"""
            
            response = await self._call_llm(prompt)
            output_path = Path("creative/think_output/CuttingOutput.md")
            output_path.write_text(response, encoding="utf-8")
            return response
        except Exception as e:
            print(f"生成CuttingOutput.md失败: {str(e)}")
            raise

    async def generate_clip_instructions(self) -> str:
        """生成JSON剪辑指令"""
        cutting_output = Path("creative/think_output/CuttingOutput.md").read_text(encoding="utf-8")
        video_files = [f.name for f in Path("video/input").glob("*") if f.is_file()]
        
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
    {{
      "source": "视频1.mkv",
      "start": "00:01:30.000",
      "end": "00:01:45.500"
    }},
    // 更多片段...
  ]
}}
3. 时间格式必须为 HH:MM:SS.ms
4. 源文件输出名字即可
5. 只允许输出JSON内容，不要任何额外说明
"""
        return await self._call_llm(prompt)

    async def _generate_friendly_response(self, video_path: Path) -> str:
        """生成最终回复"""
        prompt = f"视频已成功生成，路径为：{video_path}。请用友好的语气告知用户。"
        return await self._call_llm(prompt)

    def _clean_temp_resources(self):
        """清理临时资源（保留文件本体）"""
        # 清空文件内容
        for file_path in [
            "creative/ReadingVoice/read.txt",
            "creative/think_output/AiAsk.md",
            "creative/think_output/CuttingOutput.md",
            "creative/think_output/list.md",
            "creative/think_output/read.md",
            "creative/think_output/ReadingCut.md",
            "creative/think_output/Target.md"
        ]:
            path = Path(file_path)
            if path.exists():
                path.write_text("", encoding="utf-8")
        
        # 清空ReadingVoice文件夹内容
        reading_voice_dir = Path("creative/ReadingVoice")
        if reading_voice_dir.exists():
            for item in reading_voice_dir.iterdir():
                if item.is_file():
                    item.unlink()
        
        # 删除临时目录内容
        temp_dirs = [
            Path("creative/temp/video"),
            Path("creative/temp"),
            Path("creative/temp/Background_Music"),
            Path("temp")
        ]
        for temp_dir in temp_dirs:
            if temp_dir.exists():
                for item in temp_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                if temp_dir != Path("creative/temp"):  # 保留creative/temp目录结构
                    try:
                        temp_dir.rmdir()  # 尝试删除空目录
                    except OSError:
                        pass  # 目录非空则跳过

    async def generate_final_response(self) -> str:
        """
        完整视频处理流程：
        1. 处理背景音乐（原步骤3）
        2. 生成剪辑指令
        3. 执行视频切割
        4. 合并视频和音频
        5. 清理临时资源

        步骤3详细说明：
        1. 选择最合适的音乐文件
        2. 转码为MP3格式
        3. 输出到creative/temp/Background_Music
        """
        try:
            # 1. 处理背景音乐
            music_path = Path("creative/temp/Background_Music")
            if not music_path.exists():
                content = Path("creative/think_output/list.md").read_text(encoding="utf-8")
                cutting_output = Path("creative/think_output/CuttingOutput.md").read_text(encoding="utf-8")
                
                music_files = [f.name for f in Path("music/MusicInput").glob("*") if f.is_file()]
                prompt = f"""
【背景音乐选择指令】
根据视频需求和剪辑脚本，从可用音乐中选择最合适的背景音乐

【输入内容】
1. 用户视频需求：
{content}

2. 剪辑脚本内容：
{cutting_output}

3. 可用音乐文件：
{', '.join(music_files)}

【输出要求】
1. 直接输出最合适的音乐文件名（仅文件名，不要路径）
2. 不要任何额外说明或格式
3. 示例：
04、毛不易-小王.flac
"""
                selected_music = (await self._call_llm(prompt)).strip()
                
                src_path = Path("music/MusicInput") / selected_music
                if not src_path.exists():
                    raise FileNotFoundError(f"音乐文件不存在: {src_path}")
                
                Path("creative/temp").mkdir(parents=True, exist_ok=True)
                from music.src.convertmusic import convert_to_mp3
                convert_to_mp3(str(src_path), str(music_path))
            
            # 2. 生成剪辑指令
            instructions_json = await self.generate_clip_instructions()
            instructions_path = Path("creative/temp/cut_instructions.json")
            instructions_path.write_text(instructions_json, encoding="utf-8")
            
            # 3. 执行视频切割
            from .tools.video_cutter import VideoCutter
            cutter = VideoCutter()
            video_clips_dir = Path("creative/temp/video")
            video_clips_dir.mkdir(parents=True, exist_ok=True)
            cutter.cut_video(instructions_path, video_clips_dir)
            
            # 4. 视频合并
            from .tools.video_merger import VideoMerger
            merger = VideoMerger()
            if not merger.merge():
                raise RuntimeError("视频合并失败")
            
            # 5. 生成友好回复
            final_response = await self._generate_friendly_response(merger.final_path)
            
            # 6. 清理临时资源
            self._clean_temp_resources()
            
            return final_response
        except Exception as e:
            print(f"视频处理失败: {str(e)}")
            raise
