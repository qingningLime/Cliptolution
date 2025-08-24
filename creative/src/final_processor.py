from pathlib import Path
import subprocess
import asyncio
import json  # 新增JSON导入
from api_client import DeepSeekClient
from typing import Optional
from .script_generator import ScriptGenerator
from .no_voiceover_processor import NoVoiceoverProcessor
from config_loader import config

class FinalProcessor:
    def __init__(self, api_key: str):
        self.api_key = api_key  # 新增此行
        self.client = DeepSeekClient(api_key)
        # 初始化模型路径
        self.model_path = Path(__file__).parent.parent.parent / "video/models/Faster-Whisper"
    
    async def _needs_voiceover(self, content: str) -> bool:
        """判断是否需要口播稿（JSON格式版）"""
        prompt = (
            f"请基于用户需求判断用户希望制作的视频是否需要生成口播稿：\n"
            f"用户需求：{content}\n\n"
            "请严格按以下JSON格式回答：\n"
            "需要口播稿 → {{\"needs_voiceover\": true}}\n"
            "不需要口播稿 → {{\"needs_voiceover\": false}}"
        )
        
        try:
            response = await self.client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},  # 强制JSON格式
                temperature=0.0  # 确定性输出
            )
            result = json.loads(response)
            return result.get("needs_voiceover", False)
        except (json.JSONDecodeError, KeyError):
            return False  # 解析失败时默认返回False
    
    async def _generate_script(self) -> str:
        """生成口播稿"""
        script_generator = ScriptGenerator(self.api_key)
        return await script_generator.generate_full_script()
    
    def _read_video_output(self) -> str:
        """读取video/output所有文件内容"""
        output_dir = Path("video/output")
        content = []
        for file in output_dir.glob("*"):
            if file.is_file():
                content.append(f"## {file.name}\n{file.read_text(encoding='utf-8')}")
        return "\n\n".join(content)
    
    def _cleanup_think_output(self):
        """
        清空think_output目录下的Target.md和AiAsk.md文件
        保留文件存在但内容为空
        """
        files_to_clean = [
            "creative/think_output/Target.md",
            "creative/think_output/AiAsk.md"
        ]
        
        for file_path in files_to_clean:
            path = Path(file_path)
            if path.exists():
                path.write_text("", encoding="utf-8")
    
    async def _generate_voiceover(self, script: str):
        """生成配音和字幕"""
        # 保存口播稿
        script_path = Path("creative/think_output/read.md")
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script, encoding="utf-8")
        
        # 生成MP3
        mp3_path = Path("creative/ReadingVoice/read.mp3")
        await self._tts_generation(script, mp3_path)
        
        # 生成字幕
        txt_path = Path("creative/ReadingVoice/read.txt")
        await self._generate_subtitles(mp3_path, txt_path)
    
    async def _tts_generation(self, text: str, output_path: Path):
        """TTS语音生成（集成版），支持长文本分段处理"""
        import dashscope
        from dashscope.audio.tts_v2 import SpeechSynthesizer
        
        # 从配置读取阿里百炼API密钥
        alibaba_key = config.get_alibaba_key()
        if not alibaba_key:
            raise ValueError("未配置阿里百炼API密钥，请设置config.json中的api_keys.alibaba_bailian")
        
        # 初始化API
        dashscope.api_key = alibaba_key
        
        # 获取TTS配置
        tts_config = config.get_tts_config()
        
        # 创建临时目录
        temp_dir = output_path.parent / "tts_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 分段处理（按双换行符分割）
        segments = [p.strip() for p in text.split('\n\n') if p.strip()]
        temp_files = []
        
        # 逐段生成语音
        for i, segment in enumerate(segments, 1):
            temp_path = temp_dir / f"segment_{i}.mp3"
            synthesizer = SpeechSynthesizer(
                model=tts_config.get('model', 'cosyvoice-v2'),
                voice=tts_config.get('voice', 'cosyvoice-v2-prefix-ca0f5b1f8de84ee0be6d6a48ea625255')
            )
            audio = synthesizer.call(segment)
            with open(temp_path, 'wb') as f:
                f.write(audio)
            temp_files.append(temp_path)
        
        # 合并音频（如果有多段）
        if len(temp_files) > 1:
            await self._merge_audio_files(temp_files, output_path)
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            temp_files[0].rename(output_path)
        
        # 清理临时文件
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()
        temp_dir.rmdir()

    async def _merge_audio_files(self, input_files: list, output_path: Path):
        """使用ffmpeg合并多个音频文件（修正路径问题版本）"""
        import subprocess
        
        # 生成文件列表（使用绝对路径）
        list_file = output_path.parent / "merge_list.txt"
        with open(list_file, 'w', encoding='utf-8') as f:
            for file in input_files:
                f.write(f"file '{file.absolute()}'\n")  # 使用绝对路径
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 执行ffmpeg合并
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(list_file.absolute()),  # 使用绝对路径
            '-c', 'copy',
            str(output_path.absolute())  # 使用绝对路径
        ]
        subprocess.run(cmd, check=True)
        
        # 删除临时列表文件
        list_file.unlink()
    
    async def _generate_subtitles(self, audio_path: Path, output_path: Path) -> str:
        """生成字幕"""
        from faster_whisper import WhisperModel
        
        model = WhisperModel(str(self.model_path), device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(audio_path), beam_size=5)
        
        subtitles = []
        for segment in segments:
            subtitles.append(f"[{segment.start:.2f}-{segment.end:.2f}]: {segment.text}")
        
        # 保存字幕
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(subtitles), encoding="utf-8")
        return "\n".join(subtitles)
    
    async def generate_final_response(self, target_content: str) -> str:
        """重构的主入口方法"""
        needs_script = await self._needs_voiceover(target_content)
        
        if needs_script:
            # 口播稿处理流程
            script = await self._generate_script()
            await self._generate_voiceover(script)
            
            # 使用新的CuttingProcessor处理后续流程
            from .cutting_processor import CuttingProcessor
            processor = CuttingProcessor(self.api_key)
            await processor.generate_reading_cut()
            await processor.generate_cutting_output()
            response = await processor.generate_final_response()
            
            # 生成回复后清空指定文件
            self._cleanup_think_output()
            return response
        else:
            # 使用NoVoiceoverProcessor处理无口播稿情况
            processor = NoVoiceoverProcessor(self.api_key)
            return await processor.process(target_content)
