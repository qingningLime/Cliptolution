from openai import OpenAI

class DeepSeekClient:
    """DeepSeek API客户端封装"""
    
    def __init__(self, api_key: str):
        """初始化API客户端
        Args:
            api_key: DeepSeek API密钥
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
    
    async def chat_completion(self, messages: list, response_format: dict = None, **kwargs):
        """统一DeepSeek聊天API调用
        Args:
            messages: 消息列表
            response_format: 响应格式要求
            **kwargs: 其他API参数
        Returns:
            API响应内容
        """
        params = {
            "model": "deepseek-chat",
            "messages": messages,
            **kwargs
        }
        if response_format:
            params["response_format"] = response_format
            
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content
