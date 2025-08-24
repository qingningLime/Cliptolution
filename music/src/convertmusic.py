from pydub import AudioSegment
import os
import logging
import traceback

def convert_to_mp3(input_path, output_dir):
    """
    将任意音频文件转换为MP3格式
    :param input_path: 输入文件路径
    :param output_dir: 输出目录
    :return: 成功返回输出路径，失败返回None
    """
    try:
        # 配置日志
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名(保持兼容)
        filename = "PendingMusic.mp3"
        output_path = os.path.join(output_dir, filename)
        
        logger.info(f"开始转换: {input_path} -> {output_path}")
        
        # 读取并转换音频(自动检测输入格式)
        audio = AudioSegment.from_file(input_path)
        
        # 统一导出参数
        audio.export(output_path, 
                    format="mp3",
                    bitrate="128k",
                    parameters=["-ac", "2", "-ar", "44100"])  # 立体声, 44.1kHz采样率
        
        logger.info("转换成功")
        return output_path
        
    except Exception as e:
        logger.error(f"转换失败: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

def is_audio_file(filepath):
    """检查文件是否是支持的音频格式"""
    try:
        AudioSegment.from_file(filepath)
        return True
    except:
        return False
