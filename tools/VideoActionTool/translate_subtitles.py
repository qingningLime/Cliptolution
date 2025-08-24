from pathlib import Path
from typing import Optional
import asyncio
import sys
import httpx
from os.path import dirname, abspath
from tenacity import retry, stop_after_attempt, wait_exponential
from mcp_server import register_tool
from config_loader import config

class Translator:
    """独立API翻译器"""
    def __init__(self):
        self.api_key = config.get_deepseek_key()
        if not self.api_key:
            raise ValueError("未配置DeepSeek API密钥，请设置config.json中的api_keys.deepseek")
        self.base_url = "https://api.deepseek.com/v1"
        self.client = httpx.AsyncClient(timeout=60.0)
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def translate(self, text: str, target_lang: str) -> str:
        """独立API翻译方法"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": f"请将以下内容翻译成{target_lang}，要求保持格式与原文一致，保留原有的时间戳信息，并且不要添加任何额外的注释或解释，翻译准则为雅信达"},
                {"role": "user", "content": text}
            ]
        }
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"API请求失败: {str(e)}")
    
    async def translate_file(self, input_path: str, output_path: Optional[str] = None):
        """翻译字幕文件
        Args:
            input_path: 输入字幕文件路径
            output_path: 输出文件路径(可选)
        Returns:
            翻译后的文件路径
        """
        # 读取原始字幕
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 按行数分批处理(每150行)
        lines = content.split('\n')
        batch_size = 150
        translated_lines = []
        
        translator = Translator()
        
        for i in range(0, len(lines), batch_size):
            batch = lines[i:i+batch_size]
            batch_content = '\n'.join(batch)
            
            # 调用独立API翻译当前批次
            translated = await translator.translate(batch_content, self.target_lang)
            translated_lines.append(translated)
        
        # 合并所有翻译结果
        full_translation = '\n'.join(translated_lines)
        
        # 确定输出路径
        if not output_path:
            input_path = Path(input_path)
            output_path = str(input_path.with_name(
                f"{input_path.stem}_translated_{self.target_lang}{input_path.suffix}"
            ))
        
        # 保存翻译结果
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_translation)
        
        return output_path

@register_tool(
    tool_name="translate_subtitles",
    description="翻译字幕文件到指定语言",
    parameters={
        "input_path": {
            "type": "string",
            "description": "输入字幕文件路径"
        },
        "target_lang": {
            "type": "string",
            "description": "目标语言代码(默认en)",
            "default": "en"
        }
    },
    timeout=600,  # 翻译可能需要较长时间
    category="action"  # 明确指定为action类工具
)
async def translate_subtitles(input_path: str, target_lang: str = "en") -> dict:
    """翻译字幕文件
    
    Args:
        input_path: 输入字幕文件路径
        target_lang: 目标语言代码(默认en)
        
    Returns:
        dict: 标准工具响应格式
    """
    try:
        translator = Translator()
        translator.target_lang = target_lang
        output_path = await translator.translate_file(input_path)
        
        return {
            "success": True,
            "result": output_path,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": f"翻译失败: {str(e)}"
        }
