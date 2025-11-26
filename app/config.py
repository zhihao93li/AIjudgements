"""配置管理模块"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """系统配置"""
    
    # LLM Gateway 配置
    llm_gateway_base_url: str = "https://api.openai.com/v1"
    llm_gateway_api_key: str = ""
    
    # 模型配置
    model_chatgpt5: str = "gpt-4o"
    model_grok: str = "grok-beta"
    model_gemini: str = "gemini-2.0-flash-exp"
    model_doubao: str = "doubao-pro-32k"
    model_qwen: str = "qwen-max"
    model_selector: str = "gpt-4o-mini"
    
    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///./ai_judge.db"
    
    # 服务器配置
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    # 讨论配置
    max_debate_messages: int = 20
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()




