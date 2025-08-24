from pydub import AudioSegment
import os
import logging

def process_audio(input_path, output_path):
    """处理音频文件，根据长度进行压缩"""
    try:
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # 创建输出目录
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 读取音频文件
        logger.info(f"正在处理文件: {input_path}")
        audio = AudioSegment.from_file(input_path)
        duration = len(audio) / 1000  # 转换为秒
        logger.info(f"音频时长: {duration:.2f}秒")
        
        # 根据时长处理
        if duration > 180:  # 大于3分钟
            logger.info("音频大于3分钟，提取中间3分钟")
            middle = duration // 2
            start = max(0, middle - 90) * 1000  # 中间3分钟
            end = min(len(audio), middle + 90) * 1000
            audio = audio[start:end]
        else:
            logger.info("音频小于等于3分钟，直接压缩")
        
        # 压缩音频（保持听感的参数）
        logger.info("正在压缩音频...")
        audio.export(output_path, format="mp3", bitrate="128k")
        logger.info(f"处理完成，输出文件: {output_path}")
        
        return True
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 示例用法
    input_file = "input/01. 往欄印.m4a"
    output_file = "output/processed.mp3"
    process_audio(input_file, output_file)
