import json
from api_client import DeepSeekClient

async def detect_creative_request(
    client: DeepSeekClient, 
    user_input: str
) -> bool:
    """判断用户输入是否为创意设计请求
    
    参数:
        client: DeepSeek API客户端
        user_input: 用户输入的文本
        
    返回:
        bool: 如果是创意设计请求返回True，否则False
    """
    prompt = f"""请判断用户请求是否为复杂视频创建需求（如为xxx制作一解析视频，制作一个xxx的混剪这一类需要多次交互才能确认如何制作视频的请求），如果只是简单剪辑需求则不需要（如把xx到xx的片段剪辑出来这一类简单处理的请求）。
用户请求: {user_input}
如果是创意设计请求，返回JSON格式：{{"is_creative": true}}；否则返回{{"is_creative": false}}。"""
    
    try:
        response = await client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        result = json.loads(response)
        return result.get("is_creative", False)
    except Exception:
        return False
