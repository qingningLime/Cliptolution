# creative/src/creative_processor.py
import os
import json
import asyncio
from pathlib import Path
from api_client import DeepSeekClient
from memory.short_term import ShortTermMemory


# 从 creative_utils.py 合并的函数
def load_target(target_path: Path) -> str:
    """加载Target.md内容"""
    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    return ""

def save_target(target_path: Path, content: str):
    """保存内容到Target.md"""
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)

async def generate_project_plan(
    client: DeepSeekClient, 
    user_input: str,
    video_output_content: str = "无视频分析内容"
) -> str:
    """生成初始项目计划（增强版）"""
        # 加载短期记忆上下文
    short_term_memory = ShortTermMemory().get_context()

    prompt = f"""
    【短期记忆上下文】
    {short_term_memory}

    【视频分析内容】
    {video_output_content}
    
    【用户请求】
    {user_input}

    【系统指令】
        你是一个专业的视频制作人员，这是你唯一向用户询问的机会，所以每个问题你都必须经过深思熟虑，请你编写问题向用户提问，要求是用户回答完所有问题后就会清楚了解到视频设计的具体方向
        严格遵循：
            1. 输出必须是以"第1步"、"第2步"开头的编号列表，列表之前要求写原始用户请求，步骤控制在5步左右
            2. 每步仅保留核心问题描述（不超过30字）
            3. 必须结合视频分析内容与用户的要求进行问题设计
            4. 绝对禁止添加任何解释、破折号或技术细节
            5. 分析后的问题是需要传递给其他模型使用，所以输出的问题应当尽可能让ai能够逆向分辨用户原有的需求
            6. 如果是要求制作偏向解析的视频，必须明确询问用户是否需要解析文章的字数长度

        例子：请你制作一个xxx动漫的解析视频

        ai回复：
        用户原始请求: 请你制作一个xxx动漫的解析视频
        第1步 确认用户究竟想要制作一个什么样的视频（应为ai对视频形式的认知可能与用户真实意图有偏差）
        第2步 确认解析内容的方向和文案写作角度,以及对于视频内容的了解
        第3步 期望解析文章的字数长度和叙事节奏  （遇到需要编写文案的视频必须询问字数）
        第4步 确认视频风格
        第5步 确认视频的目标受众和传播渠道
    """
    
    response = await client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response

class CreativeProcessor:
    """创意设计请求处理器"""
    
    def __init__(self, api_key: str):
        self.client = DeepSeekClient(api_key)
        self.target_path = Path("creative/think_output/Target.md")
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
        self.video_output_path = Path("video/output")
    
    def _read_video_output(self) -> str:
        """读取video/output目录下的文本文件内容"""
        content = []
        for file in self.video_output_path.glob("*.txt"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content.append(f.read())
            except Exception:
                continue
        return "\n".join(content) if content else "无视频分析内容"
    
    async def _generate_step_interaction(self, plan: str) -> str:
        """生成第一步的交互问题（使用完整计划上下文）"""
        video_content = self._read_video_output()
        
        prompt = f"""
        你正在帮助用户完成视频制作的第一步。请根据以下完整计划和视频分析内容，生成一个友好、易懂的问题：
        
        【完整计划】
        {plan}
        
        【视频分析内容】
        {video_content}
        
        ### 要求：
        1. 只关注计划中的第一步（即"第1步"描述的内容）并且输出引导内容前需要先输出第一步的内容
        2. 问题应能引导用户思考如何具体执行第一步， 绝对不要提及"第二步"或后续步骤
        3. 问题应引导用户提供更多细节或确认方向，可以提供选项
        4. 保持自然语言风格，并且提出的问题需要让用户易于回答
        5. 不要使用技术术语或复杂表达，尽量使用带有专业性但是简单明了的语言，如果可以，提出的问题要让用户可以用简短的语言就完成回答，比如"我们按照xxxx方向制作可以吗？"
        6. 问题应由你提出对第一步的思考内容，然后向用户确认其可行性，并且不能输出除了问题之外的任何内容。
        7. 问题应能引导用户提供更多细节或确认方向，甚至可以提供选项，但是编写问题时应该考虑用户原始请求。
        """
        
        try:
            return await self.client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
        except Exception as e:
            print(f"交互问题生成失败: {str(e)}")
            return f"关于视频制作的第一步，您有什么具体想法？"
    
    async def handle_request(self, user_input: str) -> str:
        """处理创意设计请求"""
        # 读取视频分析内容
        video_content = self._read_video_output()
        # print(f"[创意模式] 视频分析内容: {video_content[:100]}...")
        
        # 生成初始项目计划（使用增强版）
        plan = await generate_project_plan(
            self.client,
            user_input,
            video_content
        )
        
        # 保存原始计划
        save_target(self.target_path, plan)
        
        # 生成第一步交互问题
        interaction = await self._generate_step_interaction(plan)
        
        # 存储到AiAsk.md
        ai_ask_path = self.target_path.parent / "AiAsk.md"
        with open(ai_ask_path, "w", encoding="utf-8") as f:
            f.write(interaction)
        
        # 存储用户原始请求到list.md
        list_path = self.target_path.parent / "list.md"
        with open(list_path, "w", encoding="utf-8") as f:
            f.write(f"用户原始请求:\n{user_input}\n\n")
        
        return interaction
