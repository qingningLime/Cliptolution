import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigLoader:
    """配置加载器"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        config_path = Path("config.json")
        if not config_path.exists():
            # 如果配置文件不存在，使用环境变量或默认值
            self._config = self._get_default_config()
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"配置文件加载失败: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "api_keys": {
                "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
                "alibaba_bailian": os.getenv("ALIBABA_BAILIAN_API_KEY", "")
            },
            "services": {
                "ollama": {
                    "host": os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
                    "timeout": int(os.getenv("OLLAMA_TIMEOUT", "300")),
                    "vision_model": os.getenv("OLLAMA_VISION_MODEL", "qwen2.5vl:3b")
                }
            },
            "tts": {
                "model": os.getenv("TTS_MODEL", "cosyvoice-v2"),
                "voice": os.getenv("TTS_VOICE", "cosyvoice-v2-prefix-ca0f5b1f8de84ee0be6d6a48ea625255")
            },
            "models": {
                "whisper_path": os.getenv("WHISPER_PATH", "video/models/Faster-Whisper"),
                "default_chat_model": os.getenv("DEFAULT_CHAT_MODEL", "deepseek-chat"),
                "default_reasoner_model": os.getenv("DEFAULT_REASONER_MODEL", "deepseek-reasoner")
            },
            "settings": {
                "max_tool_chain": int(os.getenv("MAX_TOOL_CHAIN", "15")),
                "tool_timeout": int(os.getenv("TOOL_TIMEOUT", "60")),
                "temp_dir": os.getenv("TEMP_DIR", "video/temp")
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_deepseek_key(self) -> str:
        """获取DeepSeek API密钥"""
        return self.get("api_keys.deepseek", "")
    
    def get_alibaba_key(self) -> str:
        """获取阿里百炼API密钥"""
        return self.get("api_keys.alibaba_bailian", "")
    
    def get_ollama_config(self) -> Dict[str, Any]:
        """获取Ollama配置"""
        return self.get("services.ollama", {})
    
    def get_tts_config(self) -> Dict[str, Any]:
        """获取TTS配置"""
        return self.get("tts", {})
    
    def get_model_config(self) -> Dict[str, Any]:
        """获取模型配置"""
        return self.get("models", {})
    
    def get_settings(self) -> Dict[str, Any]:
        """获取设置配置"""
        return self.get("settings", {})

# 全局配置实例
config = ConfigLoader()
