import os
import re
import time
import queue
import threading
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from datetime import datetime

# 配置参数
SCRIPT_DIR = Path(__file__).parent.parent
INPUT_DIR = str(SCRIPT_DIR / "input")
OUTPUT_DIR = str(SCRIPT_DIR / "output")
SUBTITLES_DIR = str(SCRIPT_DIR / "subtitles")
SUPPORTED_EXTS = [".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ""]  # 空字符串表示无后缀
REPORT_SUFFIXES = ["_report.txt"]
SUBTITLE_SUFFIX = "_subtitles.txt"
LOG_FILE = str(SCRIPT_DIR / "video_processor.log")

class VideoProcessor:
    def __init__(self):
        self.queue = queue.PriorityQueue()  # (timestamp, video_path)
        self.lock = threading.Lock()
        self.running = True
        self.currently_processing = None
        self.processed_files = set()
        
        # 初始化时扫描已有文件
        self.initial_scan()
        # 启动时立即清理孤儿报告
        self.log("Performing initial cleanup...")
        self.clean_orphaned_reports()

    def initial_scan(self):
        """初始化时扫描input目录"""
        for video_path in Path(INPUT_DIR).glob("*"):
            video_path = Path(video_path)  # 确保Path对象
            if video_path.suffix.lower() in SUPPORTED_EXTS:
                self.add_to_queue(video_path)

    def add_to_queue(self, video_path):
        """添加视频到处理队列"""
        if not self.should_process(video_path):
            return
            
        timestamp = os.path.getctime(video_path)
        with self.lock:
            if str(video_path) not in self.processed_files:
                self.queue.put((timestamp, str(video_path)))
                self.log(f"Added to queue: {video_path.name}")

    def should_process(self, video_path):
        """检查是否需要处理该视频"""
        # 检查文件扩展名
        if video_path.suffix.lower() not in SUPPORTED_EXTS:
            return False
            
        # 检查是否已有报告
        video_stem = video_path.stem
        for suffix in REPORT_SUFFIXES:
            report_path = Path(OUTPUT_DIR) / f"{video_stem}{suffix}"
            if report_path.exists():
                self.processed_files.add(str(video_path))
                return False
                
        return True

    def process_next(self):
        """处理队列中的下一个视频"""
        while self.running:
            try:
                _, video_path = self.queue.get_nowait()
                self.currently_processing = video_path
                
                try:
                    self.log(f"Start processing: {Path(video_path).name}")
                    subprocess.run(
                        ["python", str(SCRIPT_DIR/"src"/"main.py"), video_path],
                        check=True
                    )
                    self.processed_files.add(video_path)
                    self.log(f"Finished processing: {Path(video_path).name}")
                except subprocess.CalledProcessError as e:
                    self.log(f"Error processing {video_path}: {str(e)}")
                except Exception as e:
                    self.log(f"Unexpected error: {str(e)}")
                    
                self.currently_processing = None
                self.clean_orphaned_reports()
                
            except queue.Empty:
                time.sleep(5)  # 队列空时短暂等待

    def clean_orphaned_reports(self):
        """清理没有对应视频的报告文件和字幕文件"""
        self.log("Starting orphaned files cleanup...")
        report_count = 0
        removed_count = 0
        

        for report_path in Path(OUTPUT_DIR).glob("*_report.txt"):
            report_path = Path(report_path)  # 确保Path对象
            report_count += 1
            
            # 统一文件名匹配逻辑
            video_stem = re.sub(r'_report(\.txt)?$', '', report_path.stem)
            # 保留常见标点符号(!?'等)但不转义
            video_stem = re.sub(r'([^\w\s\[\]!?\'])', r'\\\1', video_stem)
            # 处理路径中的空格
            video_stem = video_stem.replace('\\ ', ' ')
            
            self.log(f"Processing report: {report_path.name}")
            self.log(f"Raw video stem: {report_path.stem}")
            self.log(f"Cleaned video stem: {video_stem}")
            
            video_exists = False
            for ext in SUPPORTED_EXTS:
                video_path = Path(INPUT_DIR) / f"{video_stem}{ext}"
                # 规范化路径处理
                try:
                    normalized_path = video_path.resolve()
                    self.log(f"Checking normalized path: {normalized_path}")
                    if normalized_path.exists():
                        video_exists = True
                        self.log(f"Video exists at: {normalized_path}")
                        break
                except Exception as e:
                    self.log(f"Path resolution error: {str(e)}")
            
            if not video_exists:
                try:
                    report_path.unlink()
                    removed_count += 1
                    self.log(f"Removed orphaned report: {report_path.name}")
                except PermissionError as e:
                    self.log(f"Permission denied when removing {report_path.name}: {str(e)}")
                except FileNotFoundError:
                    pass  # 文件已被其他进程删除
                except Exception as e:
                    self.log(f"Unexpected error removing {report_path.name}: {str(e)}")

        # 清理字幕文件
        for subtitle_path in Path(SUBTITLES_DIR).glob(f"*{SUBTITLE_SUFFIX}"):
            subtitle_path = Path(subtitle_path)
            report_count += 1
            
            video_stem = subtitle_path.stem.replace(SUBTITLE_SUFFIX.replace(".txt", ""), "")
            # 统一文件名处理逻辑
            video_stem = re.sub(r'_final$', '', video_stem)
            # 保留常见标点符号(!?'等)但不转义
            video_stem = re.sub(r'([^\w\s\[\]!?\'])', r'\\\1', video_stem)
            # 处理路径中的空格
            video_stem = video_stem.replace('\\ ', ' ')
            
            self.log(f"Processing subtitle: {subtitle_path.name}")
            self.log(f"Raw video stem: {subtitle_path.stem}")
            self.log(f"Cleaned video stem: {video_stem}")
            
            video_exists = False
            for ext in SUPPORTED_EXTS:
                video_path = Path(INPUT_DIR) / f"{video_stem}{ext}"
                # 规范化路径处理
                try:
                    normalized_path = video_path.resolve()
                    self.log(f"Checking normalized path: {normalized_path}")
                    if normalized_path.exists():
                        video_exists = True
                        self.log(f"Video exists at: {normalized_path}")
                        break
                except Exception as e:
                    self.log(f"Path resolution error: {str(e)}")
            
            if not video_exists:
                try:
                    subtitle_path.unlink()
                    removed_count += 1
                    self.log(f"Removed orphaned subtitle: {subtitle_path.name}")
                except PermissionError as e:
                    self.log(f"Permission denied when removing {subtitle_path.name}: {str(e)}")
                except FileNotFoundError:
                    pass
                except Exception as e:
                    self.log(f"Unexpected error removing {subtitle_path.name}: {str(e)}")
        
        self.log(f"Cleanup completed. Scanned {report_count} files, removed {removed_count} orphaned files.")

    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(log_entry.strip())

class VideoHandler(FileSystemEventHandler):
    def __init__(self, processor):
        self.processor = processor

    def on_created(self, event):
        if not event.is_directory:
            self.processor.add_to_queue(Path(event.src_path))

    def on_deleted(self, event):
        if not event.is_directory:
            self.processor.clean_orphaned_reports()
            
    def on_modified(self, event):
        if not event.is_directory and Path(event.src_path).parent == Path(SUBTITLES_DIR):
            self.processor.clean_orphaned_reports()

def main():
    processor = VideoProcessor()
    
    # 启动文件监控
    event_handler = VideoHandler(processor)
    observer = Observer()
    observer.schedule(event_handler, INPUT_DIR, recursive=True)
    observer.schedule(event_handler, SUBTITLES_DIR, recursive=True)
    observer.start()
    
    # 启动处理线程
    process_thread = threading.Thread(target=processor.process_next)
    process_thread.daemon = True
    process_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        processor.running = False
        observer.stop()
        process_thread.join()
        observer.join()
        print("Processor stopped gracefully")

if __name__ == "__main__":
    main()
