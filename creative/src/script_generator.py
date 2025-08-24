from pathlib import Path
import json
import re
from typing import Optional
from api_client import DeepSeekClient

class ScriptGenerator:
    def __init__(self, api_key: str):
        self.client = DeepSeekClient(api_key)
        self.total_steps = 0
        self.current_step = 0
        self.reading_cut_path = Path("creative/think_output/ReadingCut.md")
    
    async def generate_structure(self, user_need: str) -> str:
        """生成文案结构大纲并保存到ReadingCut.md"""
        prompt = f"""
        【用户请求内容】
        {user_need}

        【系统指令】
        你是一个专业的文案结构规划AI，请根据用户请求制定行文结构大纲：
        1. 只需列出主要板块，每个板块最后用括号注明需要多少字，每一步不低于700字，不超过1300字
        2. 严格禁止输出除了板块和字数以外的任何内容
        3. 保持简洁专业的风格
        4. 如果原始要求的字数低于2000字就只分一步即可
        5. 分步必须根据用户的核心需求来

        【输出格式要求】
        用户原始请求: xxxxxxxxxx
        1. xxxxxxxxxxxxxx(xx字)
        2. xxxxxxxxxxxxxx(xx字)
        """

        structure = await self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        # 保存结构大纲
        self.reading_cut_path.parent.mkdir(parents=True, exist_ok=True)
        self.reading_cut_path.write_text(structure, encoding="utf-8")
        return structure
    
    async def analyze_steps(self) -> int:
        """分析步骤数量并返回总步数"""
        if not self.reading_cut_path.exists():
            raise FileNotFoundError("ReadingCut.md not found")
            
        content = self.reading_cut_path.read_text(encoding="utf-8")
        prompt = (
            f"请分析以下内容中的步骤数量，只返回一个JSON格式的结果：\n"
            f"{content}\n\n"
            f"输出格式：{{\"total_steps\": x}}"
        )
        
        response = await self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        result = json.loads(response)
        self.total_steps = result.get("total_steps", 0)
        return self.total_steps
    
    async def generate_step_content(self, video_output_dir: str = "video/output") -> str:
        """生成当前步骤的文案内容"""
        if self.current_step >= self.total_steps:
            return ""
            
        # 读取视频分析内容
        video_output = self._read_video_output(video_output_dir)
        reading_cut = self.reading_cut_path.read_text(encoding="utf-8")
        
        # 读取历史记录(如果存在)
        history = ""
        read_md_path = Path("creative/think_output/read.md")
        if read_md_path.exists():
            history = read_md_path.read_text(encoding="utf-8")
        
        prompt = f"""
        【结构大纲】
        {reading_cut}

        【视频分析】
        {video_output}
        【系统指令】
        你是一个专业的视频文章的撰写AI
        请根据以下信息编写第{self.current_step + 1}步的文案内容：
        你编写的用户原始请求需要制作视频的文章内容，我们分成多步完成，在写文章的时候，需要结合用户原始请求
        【输出要求】
        1. 严格遵循结构大纲中第{self.current_step + 1}步的要求
        2. 不允许任何使用'（画面：××）'等用括号描述内容的格式，所有的内容需要来自视频分析，不允许自己添加细节和情节，不允许直接表述第几集xxx分钟到xxx分钟。
        3. 不要有任何标题、章节或格式标记
        4. 保持专业且流畅的写作风格
        5. 内容长度应超出结构大纲中第{self.current_step + 1}步的字数，不要超出太多
        6. 需要专注于当前步骤要求写以及用户原始请求的内容
        7. 创作文章时所有的英文单词生成不允许使用大写，即使是专有名词也不允许，例如“MYGO”必须写为“mygo”，“CRYCHIC”必须写成“crychic”
        """

        
        content = await self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        # 写入当前步骤内容到read.md
        read_md_path = Path("creative/think_output/read.md")
        read_md_path.parent.mkdir(parents=True, exist_ok=True)
        with open(read_md_path, "a", encoding="utf-8") as f:
            f.write(content + "\n\n")
        
        self.current_step += 1
        return content
    
    def _read_video_output(self, output_dir: str) -> str:
        """读取视频分析输出目录所有文件内容"""
        output_path = Path(output_dir)
        content = []
        for file in output_path.glob("*"):
            if file.is_file():
                content.append(f"## {file.name}\n{file.read_text(encoding='utf-8')}")
        return "\n\n".join(content)
    
    async def generate_full_script(self, user_need_path: str = "creative/think_output/list.md") -> str:
        """执行完整的分步生成流程"""
        # 读取用户需求
        user_need = Path(user_need_path).read_text(encoding="utf-8")
        
        # 生成结构大纲
        await self.generate_structure(user_need)
        
        # 分析步骤数量
        await self.analyze_steps()
        
        # 分步生成内容
        full_script = ""
        while self.current_step < self.total_steps:
            full_script += await self.generate_step_content()
        
        # 清空ReadingCut.md
        self.reading_cut_path.write_text("", encoding="utf-8")
        
        return full_script
