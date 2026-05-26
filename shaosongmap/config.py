"""应用配置中心：通过 pydantic-settings 在启动时校验所有必需配置项。"""

from __future__ import annotations

from pydantic_settings import BaseSettings
from slowapi import Limiter
from slowapi.util import get_remote_address


class Settings(BaseSettings):
    """ShaosongMap 应用配置，从环境变量或 .env 文件加载。"""

    model_config = {'env_file': '.env', 'env_file_encoding': 'utf-8'}

    deepseek_api_key: str
    deepseek_base_url: str = 'https://api.deepseek.com'
    dashscope_api_key: str = ''
    cors_origins: list[str] = ['*']
    log_level: str = 'INFO'
    log_format: str = 'text'


# 全局配置单例，在 app.py 启动时由 _lifespan 初始化
settings: Settings | None = None

# 全局速率限制器，由 app.py 在启动时注册到 app.state
limiter = Limiter(key_func=get_remote_address)
