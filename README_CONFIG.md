# 项目配置说明

## 配置文件设置

本项目使用 `config.json` 文件来集中管理所有API密钥和配置信息。请按照以下步骤进行配置：

### 1. 配置API密钥

编辑 `config.json` 文件，填入您的API密钥：

```json
{
  "api_keys": {
    "deepseek": "您的实际DeepSeek API密钥",
    "alibaba_bailian": "您的实际阿里百炼API密钥"
  },
  // ... 其他配置保持不变
}
```

### 2. 必需配置项

- **DeepSeek API密钥**: 用于AI对话和内容分析
- **阿里百炼API密钥**: 用于TTS语音生成

### 3. 可选配置项

- **Ollama服务**: 用于视觉分析，默认使用本地服务
- **TTS配置**: 语音合成模型和声音设置
- **模型路径**: 语音识别模型位置
- **系统设置**: 工具链长度、超时时间等

### 4. 环境变量支持

您也可以通过环境变量设置配置：

```bash
# DeepSeek API密钥
export DEEPSEEK_API_KEY="您的密钥"

# 阿里百炼API密钥  
export ALIBABA_BAILIAN_API_KEY="您的密钥"

# Ollama配置
export OLLAMA_HOST="http://127.0.0.1:11434"
export OLLAMA_TIMEOUT="300"
export OLLAMA_VISION_MODEL="qwen2.5vl:3b"

# TTS配置
export TTS_MODEL="cosyvoice-v2"
export TTS_VOICE="kabuleshen_v2"
```

### 5. 配置优先级

1. `config.json` 文件配置（最高优先级）
2. 环境变量配置
3. 默认配置

### 6. 验证配置

运行以下命令验证配置是否正确：

```bash
python -c "from config_loader import config; print('DeepSeek密钥:', '已设置' if config.get_deepseek_key() else '未设置'); print('阿里密钥:', '已设置' if config.get_alibaba_key() else '未设置')"
```

### 7. 安全提示

- 不要将包含真实API密钥的 `config.json` 文件提交到版本控制
- 将 `config.json` 添加到 `.gitignore` 文件中
- 使用环境变量在生产环境中管理敏感信息

## 使用说明

1. 编辑 `config.json` 填入您的实际API密钥
2. 运行项目，系统将自动使用配置中的设置

## 支持的API服务

1. **DeepSeek**: 用于AI对话、内容分析和推理
2. **阿里百炼**: 用于语音合成(TTS)
3. **Ollama**: 用于视觉内容分析（可选）

## 故障排除

如果遇到配置问题，请检查：
- API密钥是否正确
- 网络连接是否正常
- 服务端点是否可访问
- 配置文件格式是否正确（JSON格式）
