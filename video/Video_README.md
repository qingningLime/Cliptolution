# Video 处理模块

## 功能概述
这是应该独立的视频内容分析模块，与agent无关。
本模块提供自动化的视频内容分析处理流水线，主要功能包括：
- 音频提取与语音转字幕
- 视频内容智能分析
- 自动生成结构化报告
- 实时监控输入目录处理新视频

## 目录结构
```
video/
├── input/          # 待处理视频存放目录
├── output/         # 分析报告输出目录
├── subtitles/      # 生成的字幕文件
├── models/         # 模型文件
│   └── Faster-Whisper/  # 语音识别模型
├── src/            # 源代码
│   ├── main.py          # 主处理逻辑
│   └── video_monitor.py # 监控服务
└── README.md       # 本文件
```

## 处理流程
1. **音频提取**  
   使用FFmpeg从视频中提取16kHz单声道WAV音频

2. **语音转字幕**  
   使用Faster-Whisper模型生成带时间戳的字幕

3. **内容分析**  
   - 判断视频类型(发布会/动画/影视剧等)
   - 识别需要视觉分析的片段

4. **视觉分析** (可选)  
   对关键片段提取帧并使用qwen2.5vl模型分析

5. **报告生成**  
   整合文字和视觉分析生成结构化报告

## 输出格式
示例报告见`output/nioin_final_report.txt`，包含：
- 视频类型判断
- 分段内容分析表(时间段|描述|核心内容)
- 视觉分析结果(如适用)

## 依赖模型
- **Faster-Whisper**: 语音识别
- **qwen2.5vl**: 视觉内容分析 
- **deepseek-reasoner**: 内容理解

## 使用方式
### 单视频处理
```bash
python src/main.py input/视频文件名.mp4
```

### 监控服务
```bash
python src/video_monitor.py
```
服务将自动监控`input/`目录并处理新视频

## 注意事项
1. 确保已安装FFmpeg并加入PATH
2. 模型文件需放置在`models/`目录
3. 输出报告会覆盖同名文件
4. 日志记录在`video_processor.log`
