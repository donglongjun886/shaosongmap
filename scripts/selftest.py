#!/usr/bin/env python3
"""前端自测工具：Playwright 截图 → Qwen-VL 描述 → 输出检查结果。

用法:
    python scripts/selftest.py                     # 默认测试文本
    python scripts/selftest.py "你的战役文本"       # 自定义文本
    python scripts/selftest.py --url http://localhost:8000
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent

_TEST_TEXT = (
    '王彦令焦文通部自东坡塬北侧列阵，弓弩手居前，步卒持长矛继后。'
    '郦琼部八百人出塬东小路，沿干涸河沟隐蔽南下，欲绕击金军左翼。'
    '娄室中军千骑自塬底直冲东坡塬正面，合扎猛安三百铁骑沿塬西缓坡迂回包抄。'
    '两军接战于塬腰梯田处，郦琼部突然从侧翼杀出，金军阵脚动摇，娄室收兵退守塬底旧寨。'
)


def _screenshot(url: str, text: str, output: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        page.goto(url, wait_until='networkidle')
        print(f'→ 页面加载完成: {url}')

        # 填入文本
        page.fill('#text-input', text)
        # 切换时间轴模式
        page.check('#mode-timeline')
        # 点击生成
        page.click('#submit-btn')
        print('→ 已提交提取请求，等待地图渲染...')

        # 等待时间轴面板出现（说明提取完成）
        try:
            page.wait_for_selector('#timeline-wrap.active', timeout=60000)
        except Exception:
            print('⚠️ 超时：时间轴面板未出现，可能是 SSE 失败')
        else:
            # 再等一会让地图完全渲染
            time.sleep(3)

        page.screenshot(path=output, full_page=True)
        print(f'→ 截图已保存: {output}')
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description='前端自测工具')
    parser.add_argument('text', nargs='?', default=_TEST_TEXT, help='战役文本')
    parser.add_argument('--url', default='http://localhost:8000', help='应用地址')
    args = parser.parse_args()

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        screenshot_path = f.name

    try:
        _screenshot(args.url, args.text, screenshot_path)
    except Exception as e:
        print(f'❌ 截图失败: {e}')
        sys.exit(1)

    # 调用 describe.py 描述截图
    describe_script = _THIS_DIR / 'describe.py'
    print('\n→ 调用 Qwen-VL 分析截图...\n')
    result = subprocess.run(
        [
            sys.executable,
            str(describe_script),
            screenshot_path,
            '这是一张历史地图应用截图。请重点关注：1) 地图上显示了几支部队标记 2) 是否有元素重叠 3) 时间轴面板是否正常 4) 任何视觉缺陷',
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(f'❌ describe.py 失败: {result.stderr}')
        sys.exit(1)

    print(result.stdout)
    print(f'\n临时截图: {screenshot_path}')


if __name__ == '__main__':
    main()
