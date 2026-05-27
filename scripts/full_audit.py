#!/usr/bin/env python3
"""全量代码审计 — 将整个项目源码发给 Qwen3.7-Max（思考模式）审查。"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=False)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 待审计文件（不含测试）
AUDIT_FILES = [
    'app.py',
    'shaosongmap/__init__.py',
    'shaosongmap/config.py',
    'shaosongmap/extractor.py',
    'shaosongmap/geocoder.py',
    'shaosongmap/models.py',
    'shaosongmap/ocr.py',
    'shaosongmap/schemas.py',
    'shaosongmap/utils.py',
    'shaosongmap/routers/__init__.py',
    'shaosongmap/routers/extract.py',
    'shaosongmap/routers/health.py',
    'shaosongmap/routers/ocr.py',
    'shaosongmap/routers/render.py',
    'shaosongmap/services/__init__.py',
    'shaosongmap/services/geo.py',
    'shaosongmap/services/geojson.py',
    'shaosongmap/services/pipeline.py',
    'shaosongmap/services/unit_banner.py',
    'static/index.html',
    'static/css/map.css',
    'static/js/app.js',
    'static/js/map.js',
    'static/js/utils.js',
    'scripts/code_review.py',
]

SYSTEM_PROMPT = """你是 ShaosongMap 项目的外部审计专家。你需要对以下完整代码库进行一次全面的代码审计。

## 项目背景

ShaosongMap 是一个「让历史小说读者边读边看地图」的工具。用户输入《绍宋》等历史小说的战役段落，系统自动生成标注双方兵力、行军路线和地形的古代地图（古中国风渲染）。

技术栈：
- 后端: Python 3.10+ / FastAPI + Pydantic / DeepSeek API（文本提取） / PaddleOCR 3.x
- 前端: Vanilla JS + MapLibre GL JS（单页应用，无框架）
- 地理: CHGIS v6（古地名→坐标）
- 质量: uv 包管理 / ruff + mypy + bandit / pytest / pre-commit
- 部署: 本地单机开发，尚未容器化

架构分层：routers (接口层) → services (业务层) → 领域模型

## 审计维度（按优先级）

### 1. 🔴 安全
- 是否有密钥/Token 硬编码或泄漏风险
- 用户输入是否有注入风险（命令注入、XSS、路径遍历）
- 文件上传是否有限制（类型、大小）
- API 是否有速率限制/鉴权缺失
- 敏感信息是否暴露在日志或响应中

### 2. 🔴 逻辑正确性
- 数据校验是否完整（Pydantic 模型、边界条件）
- 异步/同步混用是否会导致阻塞事件循环
- 异常处理：关键路径上是否有裸露的 except/finally
- 资源管理：OCR 模型、HTTP 客户端、文件句柄是否正确释放
- 竞态条件：共享状态是否线程安全

### 3. 🟡 架构与可维护性
- 分层是否清晰（router 不写业务逻辑、service 不处理 HTTP 细节）
- 配置管理是否集中（避免散落 os.getenv）
- 是否有循环导入风险
- 模块职责是否单一，是否存在 God Class / God Module
- 前端 1570 行 index.html / app.js 是否需要拆分建议

### 4. 🟡 性能与健壮性
- 重资源（PaddleOCR 模型）是否正确预热和复用
- HTTP 客户端是否有超时设置
- 地图图层数据更新是否高效（source 复用 vs 反复创建）
- SSE 连接是否正确管理（超时、清理、重连）
- 前端是否有事件监听器泄漏

### 5. 🟢 测试与质量保障
- 关键业务路径是否有测试覆盖
- CI 门禁是否覆盖 lint/type/security/test
- 错误消息对用户是否友好（中文、可理解）

## 输出格式

按维度分组，每个问题一行：`文件路径:行号: 级别: 问题描述`

级别：🔴严重 / 🟡建议 / 🟢风格

如果某个维度没有问题，直接写「该维度未发现明显问题」。

**整体评分**：在报告末尾给出 1-10 分的代码质量总评，以及 3-5 条最重要的改进建议。

## 原则
- 这是实际产品代码，不是技术演示 — 不要为"未来可能需要"提建议
- ruff 已覆盖格式化/导入排序/引号风格，不要重复报告
- 中文输出，具体到文件和行号"""

logger = logging.getLogger(__name__)


def gather_code() -> str:
    """收集所有待审计文件内容。"""
    parts: list[str] = []
    total_lines = 0

    for rel_path in AUDIT_FILES:
        full_path = PROJECT_ROOT / rel_path
        if not full_path.exists():
            logger.warning('文件不存在，跳过: %s', rel_path)
            continue
        content = full_path.read_text(encoding='utf-8')
        lines = content.splitlines()
        total_lines += len(lines)
        parts.append(f'## {rel_path} ({len(lines)} 行)\n\n```\n{content}\n```\n')

    logger.info('共收集 %d 个文件，%d 行代码', len(parts), total_lines)
    parts.insert(0, f'# ShaosongMap 全量代码审计\n\n代码总量: {total_lines} 行\n')
    return '\n'.join(parts)


def audit(code: str) -> str:
    """调用 Qwen3.7-Max 思考模式审计全量代码。"""
    api_key = os.environ.get('DASHSCOPE_API_KEY', '')
    if not api_key:
        return '❌ 未配置 DASHSCOPE_API_KEY 环境变量，无法审计'

    client = OpenAI(
        api_key=api_key,
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
        timeout=300.0,
    )

    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': code},
    ]

    print(f'→ 发送 {len(code)} 字符到 Qwen3.7-Max（思考模式）...')
    print('→ 预计耗时 3-10 分钟，请耐心等待...\n')

    try:
        response = client.chat.completions.create(
            model='qwen3.7-max',
            messages=messages,
            extra_body={
                'enable_thinking': True,
                'thinking_budget': 32000,
            },
            max_tokens=8000,
            temperature=0.1,
        )
        return response.choices[0].message.content or '⚠️ 模型返回为空'
    except Exception as exc:
        return f'❌ 审计 API 调用失败: {exc}'


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    out_path = PROJECT_ROOT / 'audit_report.md'
    code = gather_code()

    result = audit(code)

    out_path.write_text(result, encoding='utf-8')
    print(f'\n审计报告已保存到: {out_path}')


if __name__ == '__main__':
    main()
