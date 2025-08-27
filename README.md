# Cilptolution 剪辑进化 - AI视频处理类的Ai Agent Demo

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![DeepSeek](https://img.shields.io/badge/DeepSeek-API-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

这是一个基于DeepSeek和多种AI技术的视频处理类ai agent，集成了视频内容分析、创意工作流、音乐处理、ai agent自动调用工具编辑视频等功能，旨在简化视频编辑和创作过程。只需要你一句话，ai就可以帮你完成复杂的视频处理任务。比如：
1. 给视频添加字幕、翻译、剪辑、配音、生成创意脚本等。
2. 分析视频内容，生成结构化报告。
3. 识别纯音乐，生成音乐内容分析等。
4. 通过多步骤交互式工作流，完成复杂的创意视频创作任务，比如制作影视作品的人物解析视频，给动漫制作mad视频等。


## 写在前面
本项目的所有剪辑效果和功能演示可以本人的bilibili账户中查看：[bilibili:清咛lime](https://space.bilibili.com/356616145)
演示效果和介绍请前往[免费开源的AI剪辑工具介绍](https://www.bilibili.com/video/BV1RDe9z2Esa)中查看

- warning: 该项目目前仅支持终端交互，并且给予ai的权限极高，可能会对你的文件进行不可逆的修改，且不保证生成结果的准确性，需要你有一定的技术基础和风险意识，以及基本的大模型使用经验，必要时需要修改系统中内置的提示词和工具实现，才能达到理想的效果，请谨慎评估风险。

我是本项目的开发者qingning，本项目的设计初衷是寄希望于通过ai agent的方式，探索LLM在视频创作和agent中的能力边界，让agent不是一个只能输出一份没啥用报告的玩具机器人，而是可以在user的提示下输出观点，制作相对有用的内容。而剪辑视频就意味着需要解决视频内容识别，声音内容识别，剪辑工具调用与剧本构思的问题。在本项目中提出了以下解决方案：
1. 通过LLM分析视频语音内容，判断是否需要用视觉二次判断视频内容，从而了解视频全部内容，并制作视频分析报告，详细请看 [video/Video_README.md](./video/Video_README.md)

2. 得益于qwen的全模态模型，让ai理解音乐成为可能，将音乐输入给全模态模型，可以详细分析音乐风格、内容、意向等，我们可以将分析结果再喂给LLM二次分析，即可得出音乐的分析报告，详细请看 [music/src/Music_README.md](./music/src/Music_README.md)



## ✨ 核心特性

- 🎯 **智能对话代理** - 基于DeepSeek的AI对话系统
- 🎥 **视频内容分析** - 语音识别+视觉理解完整流水线
- 🎨 **创意工作流** - 多步骤交互式视频创作
- 🎵 **音乐智能处理** - 音频分析和内容识别
- 🛠️ **工具生态系统** - 模块化工具管理和调度
- 💾 **记忆管理系统** - 短期对话记忆+长期知识存储

## 🏗️ 系统架构

```
VideoAgent/
├── 🤖 AI Agent系统 (agent.py)
│   ├── 对话管理
│   ├── 工具规划
│   └── 记忆系统
├── 🎥 视频处理模块 (video/)
│   ├── 语音识别 (Faster-Whisper)
│   ├── 视觉分析 (Ollama + Qwen2.5VL)
│   └── 内容报告生成
├── 🎨 创意工作流 (creative/)
│   ├── 创意检测
│   ├── 脚本生成
│   └── TTS语音合成
├── 🎵 音乐分析 (music/)
│   ├── 音频处理
│   ├── 音乐识别
│   └── 字幕生成
├── 🛠️ 工具系统 (tools/)
│   ├── 文件工具
│   ├── 视频动作工具
│   └── 视频列表工具
└── ⚙️ 配置系统 (config.json)
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- FFmpeg (音频处理)
- Ollama (视觉分析，可选)
- GPU支持 (推荐，用于加速处理)

### 安装步骤

1. **安装FFmpeg（必须先安装）**
   
   **Windows (使用Chocolatey):**
   ```bash
   choco install ffmpeg
   ```
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```
   
   **macOS:**
   ```bash
   brew install ffmpeg
   ```
   
   **验证安装:**
   ```bash
   ffmpeg -version
   ```

2. **创建虚拟环境（推荐）**
   ```bash
   # 创建虚拟环境
   python -m venv venv
   
   # 激活虚拟环境
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

3. **克隆项目**
   ```bash
   git clone <项目地址>
   cd VideoAgent
   ```

4. **安装Python依赖**
   ```bash
   pip install -r requirements.txt
   ```

5. **配置API密钥**
   编辑 `config.json` 文件：
   ```json
   {
     "api_keys": {
       "deepseek": "您的DeepSeek API密钥",
       "alibaba_bailian": "您的阿里百炼API密钥"
     }
   }
   ```

6. **下载模型**
   确保Faster-Whisper模型位于 `video/models/Faster-Whisper/`

### 运行项目

**启动AI Agent**
```bash
python agent.py
```

**处理视频**
```bash
python video/src/main.py video/input/您的视频.mp4
```

**启动视频监控服务**
```bash
python video/src/video_monitor.py
```

**处理音频文件**
```bash
python music/src/music_processor.py music/input/您的音频.mp3
```

**启动音频监控服务**
```bash
python music/src/music_processor.py
```

## ⚙️ 配置说明

### 配置文件结构

```json
{
  "api_keys": {
    "deepseek": "sk-...",           // DeepSeek API密钥
    "alibaba_bailian": "sk-..."     // 阿里百炼API密钥
  },
  "services": {
    "ollama": {
      "host": "http://127.0.0.1:11434",
      "timeout": 300,
      "vision_model": "qwen2.5vl:3b"
    }
  },
  "tts": {
    "model": "cosyvoice-v2",
    "voice": "cosyvoice-v2-prefix-..."
  },
  "models": {
    "whisper_path": "video/models/Faster-Whisper",
    "default_chat_model": "deepseek-chat",
    "default_reasoner_model": "deepseek-reasoner"
  },
  "settings": {
    "max_tool_chain": 15,
    "tool_timeout": 60,
    "temp_dir": "video/temp"
  }
}
```

### 环境变量支持

```bash
# DeepSeek配置
export DEEPSEEK_API_KEY="您的密钥"

# 阿里百炼配置
export ALIBABA_BAILIAN_API_KEY="您的密钥"

# Ollama配置
export OLLAMA_HOST="http://127.0.0.1:11434"
export OLLAMA_TIMEOUT="300"
export OLLAMA_VISION_MODEL="qwen2.5vl:3b"

# TTS配置
export TTS_MODEL="cosyvoice-v2"
export TTS_VOICE="cosyvoice-v2-prefix-..."
```

## 🎯 功能模块详解

### 1. AI Agent系统

核心对话代理，支持：
- 智能工具规划和执行
- 多轮对话管理
- 短期和长期记忆
- 创意工作流处理

```python
# 示例：启动Agent
from agent import AIAgent
agent = AIAgent()
await agent.start()
```

### 2. 视频处理流水线

完整的视频分析流程：
1. **音频提取** - 使用FFmpeg提取音频
2. **语音识别** - Faster-Whisper生成字幕
3. **内容分析** - DeepSeek分析视频内容
4. **视觉识别** - Ollama分析关键帧（可选）
5. **报告生成** - 生成结构化分析报告

### 3. 创意工作流

交互式视频创作系统：
- 创意需求分析
- 多步骤项目规划
- 脚本自动生成
- TTS语音合成
- 智能剪辑处理

### 4. 音乐分析模块

音频内容处理：
- 音频格式转换
- 音乐特征分析
- 纯音乐检测
- 歌词字幕生成

### 5. 工具生态系统

基于MCP服务器的工具管理：

**文件工具**
- 目录列表
- 文件读写
- 内容搜索

**视频动作工具**
- 颜色分级
- 字幕添加
- 视频剪辑
- 格式转换

**视频列表工具**
- 元数据读取
- 字幕解析
- 报告分析

## 🛠️ 开发指南

### 项目结构

```
VideoAgent/
├── agent.py              # 主AI Agent
├── api_client.py         # API客户端封装
├── mcp_server.py         # 工具管理服务器
├── config_loader.py      # 配置加载器
├── config.json           # 配置文件
├── memory/               # 记忆系统
├── creative/             # 创意处理模块
├── music/                # 音乐处理模块
├── tools/                # 工具系统
├── video/                # 视频处理模块
└── README.md             # 项目文档
```

### 添加新工具

1. 在 `tools/` 目录下创建工具文件
2. 使用 `@register_tool` 装饰器注册工具
3. 遵循工具设计规范

```python
from mcp_server import register_tool

@register_tool(
    tool_name="example_tool",
    description="工具描述",
    parameters={"param1": {"type": "string"}},
    timeout=30
)
def example_tool(param1: str) -> dict:
    return {"success": True, "result": f"处理结果: {param1}"}
```

### API开发规范

- 使用统一的响应格式
- 包含完整的错误处理
- 支持超时配置
- 提供详细的元数据

## 🚢 部署运维

### 生产环境部署

1. **环境配置**
```bash
# 设置生产环境变量
export ENV=production
export LOG_LEVEL=INFO
```

2. **进程管理** (使用PM2)
```bash
# 安装PM2
npm install -g pm2

# 启动服务
pm2 start agent.py --name "video-agent"
```

3. **监控日志**
```bash
# 查看日志
pm2 logs video-agent

# 监控状态
pm2 monit
```

### 性能优化建议

1. **GPU加速**
   - 启用CUDA支持
   - 使用GPU版本的深度学习模型

2. **内存管理**
   - 调整工具超时时间
   - 优化大文件处理

3. **缓存策略**
   - 实现结果缓存
   - 使用Redis存储频繁访问数据

## 🔧 故障排除

### 常见问题

1. **API密钥错误**
   ```bash
   # 验证配置
   python -c "from config_loader import config; print('DeepSeek:', bool(config.get_deepseek_key()))"
   ```

2. **编码问题**
   - 确保系统使用UTF-8编码
   - 检查文件编码格式

3. **依赖问题**
   ```bash
   # 重新安装依赖
   pip install -r requirements.txt
   ```

4. **模型加载失败**
   - 确认模型路径正确
   - 检查模型文件完整性

### 日志调试

启用详细日志：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 性能指标

- **处理速度**: 5-10分钟/视频（取决于长度和复杂度）
- **内存占用**: 2-4GB（视频处理时）
- **API调用**: 支持并发处理
- **扩展性**: 模块化设计，易于扩展

## 🤝 贡献指南

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

### 开发规范

- 遵循PEP8代码风格
- 使用类型注解
- 编写单元测试
- 更新文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [深度求索](https://www.deepseek.com/) - 提供强大的LLM服务，让一切拥有可能
- [阿里百炼平台/qwen](https://bailian.aliyun.com/) - 优质的TTS语音服务、全模态模型以及强大的视觉模型
- [Ollama](https://ollama.ai/) - 本地AI模型运行环境
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - 高效的语音识别
- [ffmpeg](https://ffmpeg.org/) - 强大的视频处理能力


## 📞 联系方式

如果您有任何问题、建议或合作意向，欢迎通过以下方式联系：

- 📧 **邮箱**: 3447131904@qq.com
- 🐧 **qq**: 3447131904
- 📺 **Bilibili**: [清咛lime](https://space.bilibili.com/356616145)

或者通过GitHub Issues提交问题。

---

**Cliptolution** - 让视频处理更智能，让创意无限可能！ 🚀
