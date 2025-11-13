"""
配置模块

定义自动化测试工具的所有配置项
"""

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# 加载环境变量
load_dotenv()


class LLMSettings(BaseSettings):
    """LLM 配置"""

    model: str = Field(
        default="openrouter/google/gemini-2.5-flash",
        description="LLM 模型名称",
    )
    base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="LLM API 基础 URL",
    )
    api_key: str = Field(default="", description="LLM API 密钥")
    temperature: float = Field(default=0.7, description="生成温度")
    max_tokens: int = Field(default=8192, description="最大 token 数量")
    num_retries: int = Field(default=3, description="重试次数")

    class Config:
        env_prefix = "LLM_"


class AppSettings(BaseSettings):
    """应用配置"""

    env: str = Field(default="dev", description="运行环境: dev/test/prod")
    log_level: str = Field(default="INFO", description="日志级别")
    agent_service_port: int = Field(default=8001, description="Agent Service 端口")

    class Config:
        env_prefix = "APP_"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.env == "prod"


# 实例化配置
LLMConfig = LLMSettings()
AppConfig = AppSettings()
