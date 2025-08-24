import os
import base64
from openai import OpenAI
from config_loader import config

# 从配置读取阿里百炼API密钥
alibaba_key = config.get_alibaba_key()
if not alibaba_key:
    raise ValueError("未配置阿里百炼API密钥，请设置config.json中的api_keys.alibaba_bailian")

client = OpenAI(
    api_key=alibaba_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def analyze_music(audio_path):
    def encode_audio(audio_path):
        with open(audio_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    base64_audio = encode_audio(audio_path)
    
    completion = client.chat.completions.create(
        model="qwen-omni-turbo",
        messages=[{
            "role": "user",
            "content": [
                {"type": "input_audio", "input_audio": {"data": f"data:;base64,{base64_audio}", "format": "mp3"}},
                {"type": "text", "text": "分析这首歌曲的流派、情感、节奏、乐器、调性、拍号，风格以及是否有歌词。"}
            ]
        }],
        modalities=["text"],
        stream=True,
        stream_options={"include_usage": True},
    )
    
    result = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            result += chunk.choices[0].delta.content
    
    return result
