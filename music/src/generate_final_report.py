import sys
import os

# 添加项目根目录到Python路径
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from api_client import DeepSeekClient

async def generate_final_report(client: DeepSeekClient, music_report: str, subtitles: str) -> str:
    """生成最终音乐报告
    
    参数:
        client: DeepSeek API客户端
        music_report: 音乐特征报告
        subtitles: 歌词字幕内容
        
    返回:
        str: 最终报告内容
    """
    prompt = f"""请结合音乐特征分析和歌词内容，生成一份简单的音乐报告：
    
    ## 音乐特征分析
    {music_report}
    
    ## 歌词内容
    {subtitles}
    
    报告要求：
    1. 综合音乐特征和歌词分析音乐主题
    2. 指出音乐情感走向
    3. 分析歌词与音乐风格
    4. 输出为Markdown格式
    5. 以音乐特征分析为主，歌词内容为辅助说明，不要捏造不存在的内容。
    6. 以中文输出
    7. 情感走向分析格式如下：
    ## 情感走向  
    - xxxxxxx（mm.ss.ms-mm.ss.ms）：xxxxxxxxxxxxxxxxxxxxxx

    """
    
    response = await client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response
