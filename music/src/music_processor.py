import os
import shutil
import sys

# 添加项目根目录到Python路径
# 获取项目根目录的绝对路径
current_file = os.path.abspath(__file__)
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)  # 插入到开头确保优先搜索

from makemusic import process_audio
from knowmusic import analyze_music
from config_loader import config

def process_music(input_path):
    try:
        # 使用全局项目根目录
        temp_dir = os.path.normpath(os.path.join(base_dir, "music", "temp"))
        os.makedirs(temp_dir, exist_ok=True)
        
        from convertmusic import convert_to_mp3
        pending_path = convert_to_mp3(input_path, temp_dir)
        if not pending_path:
            raise Exception("音频转码失败")
        
        # 2. 处理音频(切割或直接复制)
        processed_path = os.path.join(temp_dir, "ProcessedMusic.mp3")
        if not process_audio(pending_path, processed_path):
            raise Exception("音频处理失败")
        
        # 3. 分析音乐
        analysis_result = analyze_music(processed_path)
        
        # 4. 生成报告(使用原文件名前缀)
        report_name = f"{os.path.splitext(os.path.basename(input_path))[0]}_report.txt"
        report_path = os.path.join(temp_dir, report_name)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(analysis_result)
        
        # 5. 纯音乐检测与后续处理
        from is_instrumental import detect_instrumental
        from generate_final_report import generate_final_report
        from api_client import DeepSeekClient
        import asyncio
        
        # 确保输出目录存在（使用Windows兼容路径）
        report_output_dir = os.path.normpath(os.path.join(base_dir, "music", "report_output"))
        os.makedirs(report_output_dir, exist_ok=True)
        subtitle_dir = os.path.normpath(os.path.join(base_dir, "music", "MucicSubtitles"))
        os.makedirs(subtitle_dir, exist_ok=True)
        
        # 读取临时报告内容
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
        
        try:
            # 从配置读取DeepSeek API密钥
            deepseek_key = config.get_deepseek_key()
            if not deepseek_key:
                raise ValueError("未配置DeepSeek API密钥，请设置config.json中的api_keys.deepseek")
            
            client = DeepSeekClient(api_key=deepseek_key)
            is_pure = asyncio.run(detect_instrumental(client, report_content))
            
            final_report_path = os.path.join(report_output_dir, report_name)
            
            if is_pure:
                # 纯音乐：直接复制报告
                shutil.copy2(report_path, final_report_path)
                print(f"纯音乐报告已保存: {final_report_path}")
            else:
                # 非纯音乐处理
                print("检测到非纯音乐，开始生成字幕...")
                
                # a. 生成字幕（使用完整转码文件）
                from video.src.main import transcribe_audio
                subtitles = transcribe_audio(pending_path)  # 使用完整转码文件而非片段
                
                # 保存字幕
                subtitle_path = os.path.join(subtitle_dir, 
                    f"{os.path.splitext(os.path.basename(input_path))[0]}_subtitles.txt")
                with open(subtitle_path, "w", encoding="utf-8") as f:
                    f.write(subtitles)
                
                # b. 生成最终报告
                final_content = asyncio.run(generate_final_report(client, report_content, subtitles))
                with open(final_report_path, "w", encoding="utf-8") as f:
                    f.write(final_content)
                print(f"最终报告已生成: {final_report_path}")
        
        except Exception as e:
            print(f"第五步处理出错: {str(e)}")
        
        print(f"处理完成: {os.path.basename(input_path)} -> {report_name}")
        
        # 处理完成后清空临时文件夹
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"删除临时文件失败 {file_path}: {e}")
        print(f"已清空临时文件夹: {temp_dir}")
        
        return True
    except Exception as e:
        print(f"处理失败 {os.path.basename(input_path)}: {str(e)}")
        return False

def process_all_music():
    # 使用全局项目根目录
    input_dir = os.path.normpath(os.path.join(base_dir, "music", "MusicInput"))
    
    # 清理不匹配的输出文件
    output_dirs = [
        os.path.normpath(os.path.join(base_dir, "music", "MucicSubtitles")),
        os.path.normpath(os.path.join(base_dir, "music", "report_output"))
    ]
    clean_orphaned_files(input_dir, output_dirs)
    
    temp_dir = os.path.normpath(os.path.join(base_dir, "music", "temp"))
    
    print(f"输入目录: {input_dir}")
    print(f"临时目录: {temp_dir}")
    
    # 确保目录存在
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    # 获取所有音频文件
    audio_files = [f for f in os.listdir(input_dir) 
                 if f.lower().endswith(('.mp3', '.wav', '.m4a', '.flac'))]
    
    if not audio_files:
        print(f"在目录 {input_dir} 中没有找到音频文件")
        return
    
    print(f"找到 {len(audio_files)} 个音频文件，开始处理...")
    success = 0
    
    # 获取报告输出目录
    report_output_dir = os.path.normpath(os.path.join(base_dir, "music", "report_output"))
    
    for filename in audio_files:
        # 检查报告是否已存在
        report_name = f"{os.path.splitext(filename)[0]}_report.txt"
        report_path = os.path.join(report_output_dir, report_name)
        
        if os.path.exists(report_path):
            print(f"报告已存在，跳过: {filename}")
            continue  # 跳过已处理的文件
            
        input_path = os.path.join(input_dir, filename)
        if process_music(input_path):
            success += 1
    
    print(f"\n处理完成: {success}/{len(audio_files)} 成功")

def clean_orphaned_files(input_dir, output_dirs):
    """
    清理输出目录中与输入文件不匹配的文件
    :param input_dir: 输入目录（MusicInput）
    :param output_dirs: 输出目录列表（字幕和报告目录）
    """
    # 获取输入文件基本名（不含扩展名）
    input_files = [os.path.splitext(f)[0] for f in os.listdir(input_dir) 
                  if f.lower().endswith(('.mp3', '.wav', '.m4a', '.flac'))]
    
    # 清理所有输出目录
    for output_dir in output_dirs:
        if not os.path.exists(output_dir):
            continue
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            
            # 检查是否匹配任何输入文件基本名
            if not any(base_name in filename for base_name in input_files):
                try:
                    os.remove(file_path)
                    print(f"删除不匹配文件: {filename}")
                except Exception as e:
                    print(f"删除失败 {filename}: {str(e)}")

if __name__ == "__main__":
    process_all_music()
