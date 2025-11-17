"""
配置模块

定义自动化测试工具的所有配置项
"""

import os
from dataclasses import dataclass, replace
from functools import partial
from typing import Callable, Dict

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

# 加载环境变量
load_dotenv()


# ============================================================================
# 基础配置
# ============================================================================

class LLMSettings(BaseSettings):
    """LLM 配置"""

    model: str = Field(
        default="openai/gpt-4o-mini",
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


# ============================================================================
# Agent 模型配置（参考 initial_evaluation 的动态配置）
# ============================================================================

@dataclass
class Model:
    """模型配置数据类"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 8192
    num_retries: int = 3


# 类型别名
AgentName = str
EnvName = str


def _set_agent_model(base: Model, **overrides) -> Callable[[], Model]:
    """创建模型配置工厂函数"""
    return lambda: replace(base, **overrides)


# 基础模型配置
_base_flash_model = Model(
    model=LLMConfig.model,
    temperature=LLMConfig.temperature,
    max_tokens=LLMConfig.max_tokens,
    num_retries=LLMConfig.num_retries,
)

_base_pro_model = Model(
    model="openai/gpt-4o",
    temperature=0.7,
    max_tokens=8192,
    num_retries=3,
)


# Agent 模型配置映射
_agent_model_factories: Dict[AgentName, Dict[EnvName, Callable[[], Model]]] = {
    "entrepreneur": {
        "default": _set_agent_model(_base_flash_model, max_tokens=8192),
        "dev": _set_agent_model(_base_flash_model, max_tokens=8192),
        "staging": _set_agent_model(_base_pro_model, max_tokens=8192),
        "production": _set_agent_model(_base_pro_model, max_tokens=8192),
    },
}

# 默认工厂
_fallback_factory = _set_agent_model(_base_flash_model, max_tokens=8192)


def _default_model_factory(agent: str) -> Dict:
    """
    根据环境和 Agent 名称获取模型配置
    
    Args:
        agent: Agent 名称
        
    Returns:
        Dict: 模型配置字典
    """
    env = AppConfig.env
    agent_factories = _agent_model_factories.get(agent, {})
    factory = agent_factories.get(env) or agent_factories.get("default")
    
    if factory is None:
        factory = _fallback_factory
    
    model = factory()
    
    # 转换为字典格式（兼容 LlmAgent 参数）
    return {
        "model": model.model,
        "temperature": model.temperature,
        "max_tokens": model.max_tokens,
        "num_retries": model.num_retries,
    }


def _role_field_default(role: str) -> Callable[[], Dict]:
    """创建角色配置的默认工厂"""
    return partial(_default_model_factory, role)


# ============================================================================
# Agent 配置类
# ============================================================================

class Config(BaseModel):
    """Agent 配置管理"""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Agent 模型配置
    entrepreneur: Dict = Field(default_factory=_role_field_default("entrepreneur"))
    
    # 记忆管理配置
    max_short_term_rounds: int = 8
    compress_rounds: int = 5
    
    # RAG 配置
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 100
    rag_persist_dir: str = "./chroma_db"
    
    # 存储配置
    storage_base_dir: str = "./sessions"
