"""pytest 共享 fixture：初始化测试配置。"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _init_test_config(monkeypatch):
    """为所有测试自动注入最小配置并重置速率限制。

    测试环境不走 FastAPI lifespan，需手动初始化 config.settings。
    通过 monkeypatch 设置环境变量让 pydantic-settings 加载。
    每次测试前重置 slowapi 速率限制计数器，避免测试间互相影响。
    """
    import shaosongmap.config as config_mod
    from shaosongmap.config import Settings, limiter

    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')
    monkeypatch.setenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

    config_mod.settings = Settings()

    # 重置速率限制器状态，确保测试间独立
    limiter.reset()
