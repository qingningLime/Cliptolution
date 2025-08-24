import subprocess
import shutil
import uuid
import ollama
import sys
from pathlib import Path
from openai import OpenAI
import traceback
import time
from config_loader import config


# 临时文件目录配置 (统一到video目录下)
TEMP_DIR = Path(__file__).parent.parent / "temp"
TEMP_DIR.mkdir(exist_ok=True, parents=True)
CHUNK_REPORT_DIR = TEMP_DIR / "chunk_reports"
CHUNK_REPORT_DIR.mkdir(exist_ok=True)
FRAME_DIR = TEMP_DIR / "frames"
FRAME_DIR.mkdir(exist_ok=True)

def save_temp_file(content, prefix=""):
    """保存临时文件到指定子目录"""
    temp_path = CHUNK_REPORT_DIR / f"{prefix}{uuid.uuid4().hex}.tmp"
    temp_path.write_text(content, encoding="utf-8")
    return temp_path

def cleanup_temp_files():
    """清理所有临时文件"""
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


# 配置常量
MODEL_PATH = str(Path(__file__).parent.parent / "models" / "Faster-Whisper")
OUTPUT_DIR = str(Path(__file__).parent.parent / "output")
SUPPORTED_VIDEO_EXTS = [".mp4", ".mkv", ".avi", ".mov"]

# 初始化客户端
deepseek_api_key = config.get_deepseek_key()
if not deepseek_api_key:
    print("错误: 未配置DeepSeek API密钥，请设置config.json中的api_keys.deepseek")
    exit(1)
client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")

def time_str_to_seconds(time_str):
    """将时间字符串(格式为HH:MM:SS)转换为秒数"""
    parts = time_str.split(':')
    if len(parts) == 3:  # HH:MM:SS
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:  # MM:SS
        return int(parts[0]) * 60 + float(parts[1])
    else:  # SS
        return float(parts[0])

def extract_audio(video_path):
    """从视频中提取音频为WAV格式"""
    Path(TEMP_DIR).mkdir(exist_ok=True, parents=True)
    audio_path = Path(TEMP_DIR) / f"{Path(video_path).stem}.wav"
    
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-vn', 
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        '-y',  # 覆盖已存在文件
        str(audio_path)
    ]
    
    # 使用DEVNULL避免编码问题
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败")
    
    return audio_path

def transcribe_audio(audio_path):
    """转录音频为字幕"""
    from faster_whisper import WhisperModel
    
    print(f"开始语音识别: {audio_path}")
    model = WhisperModel(MODEL_PATH, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), beam_size=5)
    
    # 准备字幕内容
    subtitles = []
    subtitles.append(f"检测语言: {info.language}")
    subtitles.append(f"概率: {info.language_probability:.2f}\n")
    
    for segment in segments:
        start = segment.start
        end = segment.end
        text = segment.text
        subtitles.append(f"[{start:.2f}-{end:.2f}]: {text}")
    
    return "\n".join(subtitles)

def analyze_subtitles(subtitles, is_chunk=False):
    """分析字幕内容，判断是否需要视觉识别
    Args:
        subtitles: 要分析的字幕内容
        is_chunk: 是否为分批处理的片段(会调整提示词)
    """
    # 统计字符数
    char_count = len(subtitles.encode('utf-8'))
    print(f"[字幕分析] 字符数: {char_count:,}")
    
    if char_count > 64000 and not is_chunk:
        raise ValueError(f"字幕过长({char_count:,}字符)，请先分割处理")

    system_prompt = """
你是一个专业的剪辑脚本设计师，需要根据视频字幕内容完成以下任务：
1. 判断视频类型（如MV、动画、剧情片、影视剧等）
2. 按时间片段分析内容
输出要求（请严格按照以下格式输出，不能输出格式以外的其他内容。）：
- 如果整个片段都不需要调用视觉识别模型，则输出"视频类型为XXXX，不需要调用视觉识别模型"这段话即可。
- 如果需要调用视觉识别模型，则输出"视频类型为XXXX，需要调用视觉识别模型，分析表格如下"并且附带分析表格，表格格式如下所示：
- 尽可能把每个事件给出一个时间段，时间段格式为HH:MM:SS-HH:MM:SS，要尽可能分析出不同的事件，因为用于指导剪辑的分析报告，
    时间段|核心事件|是否需要调用视觉识别模型进一步分析
    00:00:00-00:01:30 |片头曲歌词（一般的动漫片头长度为90秒）	|否
    00:01:31-00:02:56 |小孩的年回忆（收集石子、回避社交）	|是
    00:02:57-00:04:20 |字幕没有提及的大量空白部分	|是
    00:04:21-00:05:45 |小孩的成长旁白	|否
视觉识别调用原则（需要先分析视频类型，如果认为该视频的类型为不需要调用视觉模型即可了解全部内容的视频，则需要把所有片段都标记为否，通常认为动画，影视剧等需要演出传递内容的视频需要视觉辅助，而口播，电台，发布会等重点在文字内容的视频则不需要视觉辅助）：
   • 需要调用：涉及重点内容，演出，复杂场景等画面关键信息，以及某些文字没有提及的空白部分、画面描述可以辅助理解剧情细节的影视作品等。
   • 不需要调用：纯对话、影视作品的片头片尾曲（特别是片尾曲）、旁白讲解、口播、电台节目等文字信息为主的内容等。例如动漫或者影视作品通常有明确的剧情发展并且由片头曲和片尾曲，那么片头曲和片尾曲有可能对视频内容分析产生干扰，需要你无视。而插入曲则有可能与情节产生关联，而口播视频、发布会视频则通常是直接表达观点或信息，视觉内容可能不那么重要。演唱会视频则需要关注演出和表演细节，歌曲内容可能只是演出内容，你只需要分析有多少个歌曲即可
   • 视觉模型仅能用输出画面描述辅助对视频内容的理解，无法用于文字识别。
"是否需要调用视觉识别模型进一步分析"这一项若需要输出，则必须严格按照"是"或"否"输出，不能输出其他内容。
每个片段应该独立成段，有具体的与有意义的情节，至少要有1-2分钟的长度（这并不意味着每一段都必须是这个长度，长度可以更长），且片段之间不能有重叠。
"""

    # 调用DeepSeek-R1模型
    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下视频字幕内容：\n\n{subtitles}"}
        ],
        temperature=0.7,
        stream=False
    )

    return response.choices[0].message.content

def extract_keyframes(video_path, time_segment):
    """提取时间段内的所有关键帧"""
    from PIL import Image
    
    # 创建时间段目录
    segment_name = time_segment.replace(':', '_').replace('-', '_')
    segment_dir = FRAME_DIR / segment_name
    segment_dir.mkdir(exist_ok=True, parents=True)
    
    # 提取所有关键帧
    cmd = [
        'ffmpeg',
        '-ss', time_segment.split('-')[0],
        '-to', time_segment.split('-')[1],
        '-i', str(video_path),
        '-vf', "select='eq(pict_type,I)',scale=360:-1",
        '-vsync', 'vfr',
        '-q:v', '2',
        str(segment_dir / 'frame_%03d.jpg'),
        '-y'
    ]
    
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 验证并返回帧列表
    frames = []
    for frame in sorted(segment_dir.glob('frame_*.jpg')):
        try:
            with Image.open(frame) as img:
                img.verify()
            frames.append(str(frame))
        except Exception as e:
            print(f"无效帧: {frame} - {str(e)}")
    
    return frames

def check_ollama_connection():
    """简化版Ollama连接检查"""
    ollama_config = config.get_ollama_config()
    client = ollama.Client(host=ollama_config.get('host', 'http://127.0.0.1:11434'), 
                          timeout=ollama_config.get('timeout', 300.0))
    max_retries = 3
    for i in range(max_retries):
        try:
            client.list()  # 简单API调用测试连接
            return client
        except Exception as e:
            if i < max_retries - 1:
                time.sleep(2)
                continue
            raise ConnectionError(f"无法连接到Ollama服务: {str(e)}")

def analyze_keyframes(frame_paths):
    """使用video_analyzer.py的优化方法分析关键帧"""
    print(f"开始视觉分析: {len(frame_paths)}个关键帧")
    
    try:
        client = check_ollama_connection()
        prompt = "这是5张连续的动漫视频截图，请尽可能简略描述这个片段的内容，必须使用中文返回结果"

        descriptions = []
        frame_paths = sorted(frame_paths)

        for i in range(0, len(frame_paths), 5):
            batch = frame_paths[i:i+5]
            try:
                ollama_config = config.get_ollama_config()
                response = client.generate(
                    model=ollama_config.get('vision_model', 'qwen2.5vl:3b'),
                    prompt=prompt,
                    images=batch,
                    options={'num_thread': 2}
                )
                desc = response['response']
                
                # 获取时间范围
                first_frame = Path(batch[0]).stem.replace('frame_', '')
                last_frame = Path(batch[-1]).stem.replace('frame_', '')
                time_range = f"{first_frame}-{last_frame}"
                
                descriptions.append(f"[{time_range}]\n{desc}")
            except Exception as e:
                print(f"分析失败: {str(e)}")
                descriptions.append(f"[{time_range}]\n分析失败")
        
        return "\n\n".join(descriptions)
    except Exception as e:
        print(f"视觉分析失败: {str(e)}")
        return "视觉分析失败: Ollama服务异常"

def generate_chunk_report(video_path, subtitles, analysis_result, visual_analysis, chunk_num=None):
    """生成分段报告"""
    video_name = Path(video_path).stem
    suffix = f"_chunk{chunk_num}" if chunk_num else ""
    temp_path = CHUNK_REPORT_DIR / f"{video_name}{suffix}_temp_report.txt"
    Path(CHUNK_REPORT_DIR).mkdir(exist_ok=True, parents=True)
    
    # 如果有视觉分析内容，先进行整合推理
    integrated_summary = ""
    if visual_analysis and "需要调用视觉识别模型" in analysis_result:
        print("\n=== 开始整合推理 ===")
        print(f"字幕长度: {len(subtitles)}字符") 
        print(f"视觉分析段落数: {visual_analysis.count('##')}")
        
        # 整合推理提示词
        integrate_prompt = """
你是一个专业的视频内容推理师，请根据以下材料：
1. 视频字幕文本（包含时间戳）以视频字幕为主
2. 视觉分析结果（画面描述） 视觉作为辅助，因为不是所有内容都需要视觉识别的

推理出整个视频内容的核心情节和重要细节，要思考整个内容的结构和逻辑关系，思考整个视频内容的核心情节和重要细节，生成一段自然语言描述。
要求：
- 结合字幕和视觉分析结果，生成一段自然语言描述，用一段直白的语言描述视频内容
- 需要考虑视频的整体结构和逻辑关系
- 要讲清楚一个完整的故事

注意事项：
1. 视觉分析结果仅作为辅助，不能完全依赖视觉内容
2. 我们调高温度，期望你能推理出更具体的内容，所以你可以结合你模型本身的知识库优化回答，但要确保内容连贯且易于理解。
3. 输出的内容需要完整且能够清晰地表达视频内容，用于让大模型了解视频内容
4. 你是推理模型，所以在思考前请你推理出视频的整体内容和结构，思考视频的核心情节和重要细节，
5. 初步分析结果是对视频类别的初步分析，需要你根据类别进行推理，要知道不同类别的视频内容结构和逻辑关系是不同的。
例如动漫或者影视作品通常有明确的剧情发展并且由片头曲和片尾曲，那么片头曲和片尾曲有可能对视频内容分析产生干扰，需要你标注并无视。而插入曲则有可能与情节产生关联
而口播视频、发布会视频则通常是直接表达观点或信息，视觉内容可能不那么重要。演唱会视频则需要关注演出和表演细节，歌曲内容可能只是演出内容，你只需要分析有多少个歌曲即可

输出要求：
最终只输出一段话，清楚一个完整的故事，3000字以内.
"""
        try:
            integrate_response = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": integrate_prompt},
                    {"role": "user", "content": f"字幕内容：\n{subtitles}\n\n视觉分析：\n{visual_analysis}\n\n初步分析结果：\n{analysis_result}"}
                ],
                temperature=1.0
            )
            integrated_summary = integrate_response.choices[0].message.content
            print("\n=== 整合推理结果 ===")
            print(integrated_summary)  # 输出完整内容
            print(f"完整结果长度: {len(integrated_summary)}字符") 
            print("=== 整合完成 ===\n")
        except Exception as e:
            print(f"整合推理失败: {str(e)}")
            integrated_summary = "整合推理失败"

    # 报告生成提示词
    system_prompt = """
你是一个专业的视频内容分析师，需要根据提供的材料生成详细的视频内容分析报告。
材料包括：
1. 由字幕生成模型生成原始字幕内容
2. 初步分析结果（那些部分需要视觉识别模型分析）
3. 视觉分析结果（如果有）
4. 整合后的内容概述（如果有）

报告输出格式：
## 文件名
## 视频内容描述
（这里用自然语言描述视频的整体内容，比如整个动漫讲的故事，口播表达的内容等，不大于300字）
## 分段分析表格
| 时间段 | 片段描述 | 片段核心内容 |
必须严格按照此格式输出，不能输出其他内容。

生成规则：
1. 时间段格式为HH:MM:SS-HH:MM:SS
2. 片段核心内容要用自然语言描述片段的内容，要直白的讲解该片段的故事
3. 片段应该尽可能细化描述，大概一两分钟一个片段为佳
4. 以中文输出，整个表格内容需要完整且能够清晰地表达视频内容，用于让大模型了解视频内容
5. 片段描述需要输出对对应时间段视频内容的简要描述。
6. 片段核心内容需要你结合字幕内容和视觉分析结果（如果有），用一段自然语音描述视频画面的内容，输出的内容要综合，不能把文字和视觉分开描述，需要连贯且易于理解
7. 不同类别的视频内容结构和逻辑关系是不同的。
8. 每个片段应该独立成段，有具体的与有意义的情节，标注的片段需要是有意义的，可以是三四十秒，也可以是一两分钟，甚至稍微长一点，但是片段之间不能有重叠或空缺
例如动漫或者影视作品通常有明确的剧情发展并且由片头曲和片尾曲，那么片头曲和片尾曲有可能对视频内容分析产生干扰，需要你标注并无视。而插入曲则有可能与情节产生关联，要把片头曲和片尾曲单独列出片段
而口播视频、发布会视频则通常是直接表达观点或信息，视觉内容可能不那么重要。演唱会视频则需要关注演出和表演细节，歌曲内容可能只是演出内容，你只需要分析有多少个歌曲即可
"""
    
    user_content = f"""
# 视频文件名: {video_name}
    
## 原始字幕内容[权重45%]:
{subtitles}
    
## 初步分析结果[权重5%]:
{analysis_result}

整合概述内容[权重15%]：
{integrated_summary if integrated_summary else "无整合概述"}

## 视觉分析结果[权重35%]:
{visual_analysis if visual_analysis else "无视觉分析"}
"""
    
    # 调用模型生成报告
    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.7,
        stream=False
    )
    
    # 保存临时报告
    report = response.choices[0].message.content
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    return temp_path

def merge_reports(video_path, chunk_reports):
    """合并所有分块报告为最终报告"""
    video_name = Path(video_path).stem
    # 移除可能存在的_final后缀
    if video_name.endswith('_final'):
        video_name = video_name[:-6]
    
    final_path = Path(OUTPUT_DIR) / f"{video_name}_report.txt"
    Path(OUTPUT_DIR).mkdir(exist_ok=True, parents=True)
    
    with open(final_path, "w", encoding="utf-8") as f:
        f.write(f"=== 最终合并报告 ===\n\n")
        for report in chunk_reports:
            with open(report, "r", encoding="utf-8") as rf:
                f.write(rf.read())
                f.write("\n\n")
            # 立即删除临时文件
            Path(report).unlink()
    
    return final_path

def split_subtitles(subtitles, max_chars=40000):
    """分割字幕为多个不超过max_chars的部分"""
    lines = subtitles.split('\n')
    chunks = []
    current_chunk = []
    current_size = 0
    
    for line in lines:
        line_size = len(line.encode('utf-8'))
        if current_size + line_size > max_chars and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(line)
        current_size += line_size
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

def clean_temp_files():
    """清理临时文件"""
    if Path(TEMP_DIR).exists():
        shutil.rmtree(TEMP_DIR)
        print(f"已清理临时目录: {TEMP_DIR}")

def main():
    """主函数"""
    # 从命令行参数获取视频路径
    if len(sys.argv) < 2:
        print("Usage: python main.py <video_path>")
        return
        
    video_path = Path(sys.argv[1])
    
    # 验证文件
    if not video_path.exists():
        print(f"文件不存在: {video_path}")
        return
    
    if video_path.suffix.lower() not in SUPPORTED_VIDEO_EXTS:
        print(f"不支持的视频格式: {video_path.suffix}")
        return
    
    try:
        # 1. 提取音频
        print("步骤1/5: 提取音频...")
        audio_path = extract_audio(video_path)
        
        # 2. 生成字幕
        print("步骤2/5: 生成字幕...")
        subtitles = transcribe_audio(audio_path)
        
        # 保存临时字幕
        subtitle_path = Path(TEMP_DIR) / f"{video_path.stem}_subtitles.txt"
        with open(subtitle_path, "w", encoding="utf-8") as f:
            f.write(subtitles)
        
        # 同时拷贝到subtitles目录
        subtitles_dir = Path(__file__).parent.parent / "subtitles"
        subtitles_dir.mkdir(exist_ok=True, parents=True)
        dest_path = subtitles_dir / f"{video_path.stem}_subtitles.txt"
        shutil.copy2(subtitle_path, dest_path)
        
        # 3. 分析字幕
        print("步骤3/5: 分析字幕内容...")
        char_count = len(subtitles.encode('utf-8'))
        reports = []
        visual_analysis = ""
        
        if char_count > 60000:
            print(f"[警告] 字幕过长({char_count:,}字符)，将分批处理")
            chunks = split_subtitles(subtitles)
            print(f"已分割为 {len(chunks)} 个部分，每个分段约{char_count//len(chunks):,}字符")
            
            # 创建临时报告目录
            temp_reports_dir = Path(TEMP_DIR) / "reports"
            temp_reports_dir.mkdir(exist_ok=True)
            
            for i, chunk in enumerate(chunks, 1):
                print(f"\n=== 处理分段 {i}/{len(chunks)} ===")
                print(f"分段长度: {len(chunk.encode('utf-8')):,}字符")
                try:
                    chunk_analysis = analyze_subtitles(chunk, is_chunk=True)
                    print(f"分段分析完成")
                    
                    if "需要调用视觉识别模型" in chunk_analysis:
                        # 解析需要视觉识别的时间段
                        visual_segments = []
                        lines = chunk_analysis.split('\n')
                        table_start = next((i for i, line in enumerate(lines) if "时间段|核心事件|" in line), -1)
                        if table_start != -1:
                            for line in lines[table_start+1:]:
                                if "|" in line and "是" in line:
                                    parts = [p.strip() for p in line.split('|') if p.strip()]
                                    if len(parts) >= 3:
                                        time_range = parts[0]
                                        if '-' in time_range:
                                            visual_segments.append(time_range)
                        
                        chunk_visual = ""
                        if visual_segments:
                            print(f"需要视觉识别的片段: {len(visual_segments)}个")
                            for segment in visual_segments:
                                try:
                                    frame_paths = extract_keyframes(video_path, segment)
                                    if frame_paths:
                                        try:
                                            segment_visual = analyze_keyframes(frame_paths)
                                            chunk_visual += f"\n\n## {segment}\n{segment_visual}"
                                        except Exception as e:
                                            print(f"视觉分析失败: {str(e)}")
                                            chunk_visual += f"\n\n## {segment}\n分析失败"
                                except Exception as e:
                                    print(f"提取关键帧失败 {segment}: {str(e)}")
                                    chunk_visual += f"\n\n## {segment}\n关键帧提取失败"
                        else:
                            print("没有需要视觉识别的片段")
                            chunk_visual = ""
                        
                        # 生成临时分段报告
                        temp_report = generate_chunk_report(
                            video_path,
                            chunk,
                            chunk_analysis,
                            chunk_visual,
                            chunk_num=i
                        )
                        reports.append(temp_report)
                    else:
                        # 不需要视觉识别的片段也生成临时报告
                        temp_report = generate_chunk_report(
                            video_path,
                            chunk,
                            chunk_analysis,
                            "",
                            chunk_num=i
                        )
                        reports.append(temp_report)
                except Exception as e:
                    print(f"分段分析失败: {str(e)}")
                    continue
            # 合并所有临时报告
            if reports:
                final_report = merge_reports(video_path, reports)
                print(f"最终报告已生成: {final_report}")
            else:
                print("没有生成任何报告")
        else:
            # 单次处理流程
            analysis_result = analyze_subtitles(subtitles)
            print("初步分析结果:\n", analysis_result)
            
            if "需要调用视觉识别模型" in analysis_result:
                print("步骤4/5: 提取并分析关键帧...")
                # 解析需要视觉识别的时间段
                visual_segments = []
                lines = analysis_result.split('\n')
                table_start = next((i for i, line in enumerate(lines) if "时间段|核心事件|" in line), -1)
                if table_start != -1:
                    for line in lines[table_start+1:]:
                        if "|" in line and "是" in line:
                            parts = [p.strip() for p in line.split('|') if p.strip()]
                            if len(parts) >= 3:
                                time_range = parts[0]
                                if '-' in time_range:
                                    visual_segments.append(time_range)
                
                visual_analysis = ""
                if visual_segments:
                    print(f"需要视觉识别的片段: {len(visual_segments)}个")
                    for segment in visual_segments:
                        try:
                            frame_paths = extract_keyframes(video_path, segment)
                            if frame_paths:
                                try:
                                    segment_visual = analyze_keyframes(frame_paths)
                                    visual_analysis += f"\n\n## {segment}\n{segment_visual}"
                                except Exception as e:
                                    print(f"视觉分析失败: {str(e)}")
                                    visual_analysis += f"\n\n## {segment}\n分析失败"
                        except Exception as e:
                            print(f"提取关键帧失败 {segment}: {str(e)}")
                            visual_analysis += f"\n\n## {segment}\n关键帧提取失败"
                else:
                    print("没有需要视觉识别的片段")
                    visual_analysis = ""
            else:
                visual_analysis = ""
            
            # 5. 生成最终报告
            print("步骤5/5: 生成报告...")
            report_path = generate_chunk_report(
                video_path,
                subtitles,
                analysis_result,
                visual_analysis
            )
            # 移动报告到output目录
            final_path = Path(OUTPUT_DIR) / f"{video_path.stem}_report.txt"
            Path(OUTPUT_DIR).mkdir(exist_ok=True, parents=True)
            shutil.move(report_path, final_path)
            print(f"最终报告已生成: {final_path}")
        return
    except Exception as e:
        print(f"处理失败: {str(e)}")
        traceback.print_exc()
    finally:
        # 清理临时文件
        clean_temp_files()

if __name__ == "__main__":
    main()
