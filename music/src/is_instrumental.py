import json
from api_client import DeepSeekClient

async def detect_instrumental(
    client: DeepSeekClient, 
    report_content: str
) -> bool:
    """检测是否为纯音乐
    
    参数:
        client: DeepSeek API客户端
        report_content: 音乐分析报告内容
        
    返回:
        bool: 纯音乐返回True，否则False
    """
    prompt = f"""根据音乐分析报告判断是否为纯音乐（无歌词或歌词极少的器乐演奏）。
报告内容: {report_content}
如果是纯音乐返回JSON格式：{{"is_instrumental": true}}；否则返回{{"is_instrumental": false}}。"""
    
    try:
        response = await client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        result = json.loads(response)
        return result.get("is_instrumental", False)
    except Exception:
        return False
