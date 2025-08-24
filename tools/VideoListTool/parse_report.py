from mcp_server import register_tool
from pathlib import Path
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from config_loader import config

class VideoAnalyzer:
    """视频内容分析器"""
    def __init__(self):
        self.api_key = config.get_deepseek_key()
        if not self.api_key:
            raise ValueError("未配置DeepSeek API密钥，请设置config.json中的api_keys.deepseek")
        self.base_url = "https://api.deepseek.com/v1"
        self.client = httpx.Client(timeout=60.0)
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def analyze(self, prompt: str, content: str) -> str:
        """调用DeepSeek分析视频内容"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个视频内容分析助手，是ai agent的一个工具，需要遵循agent的指令来分析视频内容。输出的内容应当尽可能详细且遵循原文"},
                {"role": "user", "content": f"{prompt}\n\n视频内容:\n{content}"}
            ],
            "temperature": 0.3
        }
        try:
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"API请求失败: {str(e)}")

@register_tool(
    tool_name="video_content_analyzer",
    description="了解本项目已知的所有视频内容，所有查看视频内容的指令必须使用此工具，这是唯一了解视频内容的方式。",
    parameters={
        "prompt": {
            "type": "string",
            "description": "分析提示词，你需要编写一个简短的提示词来指导AI如何分析视频内容，例如：'请分析这些视频的主要内容和主题。"
        }
    },
    timeout=600,
    category="list"
)
def video_content_analyzer(prompt: str) -> dict:
    """AI分析视频报告内容
    
    Args:
        prompt: 分析提示词
        
    Returns:
        dict: 标准返回格式 {
            "success": bool,
            "result": {
                "analysis": "分析结果",
                "sources": ["报告文件名1", "报告文件名2"]
            },
            "error": str
        }
    """
    try:
        base_dir = Path(__file__).parent.parent.parent / "video"
        output_dir = base_dir / "output"
        
        # 读取所有报告内容
        reports = []
        sources = []
        for report_file in output_dir.glob("*_report.txt"):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    reports.append(f.read())
                    sources.append(report_file.name)
            except Exception as e:
                continue
        
        # 调用DeepSeek分析
        analyzer = VideoAnalyzer()
        analysis = analyzer.analyze(prompt, "\n\n".join(reports))
        
        return {
            "success": True,
            "result": {
                "analysis": analysis,
                "sources": sources
            },
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": str(e)
        }
