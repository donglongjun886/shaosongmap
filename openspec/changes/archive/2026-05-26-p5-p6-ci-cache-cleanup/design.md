## Context

当前 CI 工作流（`.github/workflows/test.yml`）仅在 Python 3.10 单版本运行，mypy 的类型错误被 `continue-on-error: true` 静默忽略，且缺少对依赖包已知漏洞的扫描。CHGIS 数据加载每次调用都重新解析 CSV 文件，无内存缓存。CLAUDE.md 仍描述已删除的持久化层。

## Goals / Non-Goals

**Goals:**
- CI 覆盖 Python 3.10 / 3.11 / 3.12 三个版本，确保多版本兼容
- mypy 类型检查改为强制通过，提升类型安全
- 新增 pip-audit 扫描依赖 CVE，阻断已知漏洞引入
- CHGIS CSV 加载增加 LRU 缓存，同进程复用
- CLAUDE.md 移除持久化层残留描述

**Non-Goals:**
- 不引入数据库/ORM 持久化
- 不增加部署流水线（CD）
- 不改造 CHGIS 数据管线逻辑

## Decisions

### CI 矩阵：astral-sh/setup-uv@v5 原生 matrix

使用 GitHub Actions 的 `strategy.matrix` 在 `python-version` 维度展开 3.10 / 3.11 / 3.12。`astral-sh/setup-uv@v5` 的 `python-version` 参数直接接收矩阵值，无需手动管理 Python 安装。

**替代方案**：使用 tox 在单 job 内测多版本。不采用——tox 与 uv 生态重叠，增加配置复杂度，且 GitHub Actions 矩阵天然并行，CI 耗时更短。

### pip-audit：独立 job，不阻塞 test

pip-audit 作为独立的 `audit` job 运行，失败时报告漏洞但不阻塞其他验证。这样在紧急修复时不会被已知低危 CVE 卡住，同时保持可见性。

**替代方案**：集成到 security job。不采用——bandit 扫描代码级漏洞，pip-audit 扫描依赖级漏洞，关注点和修复策略不同，分开更清晰。

### CHGIS 缓存：`@functools.lru_cache(maxsize=1)`

`_load_chgis_data()` 是纯函数（无参数，读文件），适合 `lru_cache`。`maxsize=1` 即可——CHGIS 数据在进程生命周期内不变。无需 TTL 过期，因为数据文件只在重启时更新。

**替代方案**：模块级全局变量缓存。不采用——lru_cache 更简洁，标准库内置，无需手动管理状态。

## Risks / Trade-offs

- [mypy 强制] 现有代码可能有类型错误被 continue-on-error 掩盖 → 在实施前先 `mypy app.py shaosongmap/` 确认已无错误
- [pip-audit] 可能报告暂无修复方案的低危 CVE → audit job 设为 informational（不设 required check），人工判断
- [CHGIS 缓存] 同一进程多次调用共享缓存，热更新数据文件不生效 → 当前无热更新需求，重启即生效
