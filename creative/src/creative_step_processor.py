import asyncio
from pathlib import Path
from typing import Optional
from api_client import DeepSeekClient
from creative.src.final_processor import FinalProcessor

class CreativeStepProcessor:
    """处理创意工作流中的步骤交互"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = DeepSeekClient(api_key)
        self.ai_ask_path = Path("creative/think_output/AiAsk.md")
        self.list_path = Path("creative/think_output/list.md")
        self.video_output_dir = Path("video/output")
    
    def _read_video_output(self) -> str:
        """读取video/output目录下的所有文本内容"""
        content = []
        for txt_file in self.video_output_dir.glob("*.txt"):
            try:
                content.append(txt_file.read_text(encoding="utf-8"))
            except Exception:
                continue
        return "\n".join(content) if content else "无视频分析内容"
    
    async def _ask_deepseek_reasoner(self, prompt: str) -> dict:
        """专用方法调用deepseek-reasoner模型，返回JSON格式结果"""
        response = await self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="deepseek-reasoner",
            response_format={"type": "json_object"},
            temperature=0.0
        )
        try:
            import json
            return json.loads(response)
        except:
            return {"is_final": False}

    async def _is_last_step(self) -> bool:
        """使用deepseek-reasoner判断是否处于最后一步(JSON格式)"""
        if not self.ai_ask_path.exists() or not Path("creative/think_output/Target.md").exists():
            return False
            
        target_content = Path("creative/think_output/Target.md").read_text(encoding="utf-8")
        ai_ask_content = self.ai_ask_path.read_text(encoding="utf-8")
        
        prompt = f"""
        【系统指令】
        请判断【当前步骤】是否是【完整计划】中的最后一步，返回JSON格式：
        {{"is_final": true/false}}

        【完整计划】
        {target_content}

        【当前步骤】
        {ai_ask_content}
        """
        
        response = await self._ask_deepseek_reasoner(prompt)
        return response.get("is_final", False)

    async def process_step_response(self, user_input: str) -> str:
        """处理用户对步骤的响应"""
        try:
            # 1. 读取AiAsk内容
            ai_ask_content = self.ai_ask_path.read_text(encoding="utf-8")
            
            # 2. 读取视频分析内容
            video_content = self._read_video_output()
            
            # 3. 生成详细制作清单
            list_content = await self._generate_list_content(
                ai_ask_content,
                user_input,
                video_content
            )
            # 追加模式写入，保留历史记录
            with open(self.list_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n{list_content}")

            
            # 4. 判断是否是最后一步
            if await self._is_last_step():
                final_processor = FinalProcessor(self.api_key)
                return await final_processor.generate_final_response(
                    Path("creative/think_output/Target.md").read_text(encoding="utf-8")
                )
            
            # 不是最后一步则继续原有流程
            return await self._generate_friendly_response(list_content)
            
        except Exception as e:
            print(f"步骤处理错误: {e}")
            return f"处理步骤时出错，请稍后再试。错误: {str(e)}"
    
    async def _generate_list_content(
        self,
        ai_ask: str,
        user_input: str,
        video_content: str
    ) -> str:
        """生成详细制作清单"""
        # 读取list.md内容
        list_content = ""
        if self.list_path.exists():
            try:
                list_content = self.list_path.read_text(encoding="utf-8")
            except Exception as e:
                print(f"读取list.md失败: {str(e)}")
        
        prompt = f"""
        【当前步骤】{ai_ask}
        【用户指定需求】{user_input}
        【需使用的视频内容分析】{video_content}
        【历史步骤记录】{list_content}
        
        请你根据当前步骤对用户的要求与视频的内容详细分析，总结用户期望实现的内容
        要求：
        1. 能总结用户期望实现的目标，以用户指定的需求为主，如果用户的需求于问题冲突，以用户最主
        2. 结合用户的目标与视频内容通过自己的理解，描述用户需求
        3. 不允许使用Markdown格式与代码块，
        4. 内容应尽可能言简意赅但逻辑清晰，控制在50字左右。
        5. 参考【历史步骤记录】中的内容辅助回答

        格式要求：
        例如：第x步：xxxxxxxxxxxx（把【当前步骤】中第一句话搬过来）/n
        xxxxxxxxxxxxxxxxxxx（这是你回答的内容）
        """
        response = await self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=8000
        )
        return response
    
    async def _generate_friendly_response(self, list_content: str) -> str:
        """生成下一步交互的友好响应（含AiAsk.md更新）"""
        # 1. 读取完整计划(Target.md)
        target_path = Path("creative/think_output/Target.md")
        full_plan = ""
        if target_path.exists():
            try:
                full_plan = target_path.read_text(encoding="utf-8")
            except Exception as e:
                print(f"读取Target.md失败: {str(e)}")
                full_plan = "无完整计划内容"
        
        # 2. 读取视频分析内容
        video_content = self._read_video_output()
        
        # 3. 读取当前AiAsk内容
        ai_ask_content = ""
        if self.ai_ask_path.exists():
            try:
                ai_ask_content = self.ai_ask_path.read_text(encoding="utf-8")
            except Exception as e:
                print(f"读取AiAsk.md失败: {str(e)}")
        
        # 4. 构建增强提示词
        prompt = f"""
        你正在帮助用户完成视频制作的下一步。请根据以下内容生成友好、易懂的响应：
        
        【完整计划】
        {full_plan}

        【历史步骤记录】
        {list_content}

        【当前步骤问题】
        {ai_ask_content}
        
        【视频分析内容】
        {video_content}
        
        ### 要求：
        1. 只关注计划中【当前步骤问题】的下一步（即"第x步"描述的内容），并且输出引导内容前需要先输出【当前步骤问题】的下一步的内容，
        2. 问题应能引导用户思考如何具体执行下一步，问题应引导用户提供更多细节或确认方向，可以提供选项
        3. 保持自然语言风格，并且提出的问题需要让用户易于回答
        4. 不要使用技术术语或复杂表达，尽量使用带有专业性但是简单明了的语言，如果可以，提出的问题要让用户可以用简短的语言就完成回答，比如"我们按照xxxx方向制作可以吗？"
        5. 问题应由你提出对第一步的思考内容，然后向用户确认其可行性，并且不能输出除了问题之外的任何内容。
        6. 问题应能引导用户提供更多细节或确认方向，甚至可以提供选项，甚至可以是你自己确认方向，用户直接回答是否即可，编写问题时应该考虑用户原始请求。
        7. 历史步骤中有已经完成的步骤辅助判断下一步内容，并且请不要询问已经解答的内容了。

        请你务必准确判断下一步是指那一步，这非常重要！！！
        格式第x步：xxxxxxxxxxxx/n
        xxxxxxxxxxxxxxxxxxx（这是你的提问的内容）
        """
        
        # 5. 生成响应并直接覆写AiAsk.md
        response = await self.client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        # 直接覆写AiAsk.md（核心移植功能）
        self.ai_ask_path.write_text(response, encoding="utf-8")
        
        return response

def in_creative_workflow() -> bool:
    """检查是否处于创意工作流中"""
    ai_ask_path = Path("creative/think_output/AiAsk.md")
    return ai_ask_path.exists() and ai_ask_path.stat().st_size > 0
