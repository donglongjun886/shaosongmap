#!/usr/bin/env python3
"""前端自测工具：Playwright 截图 → Qwen-VL 描述 → 输出检查结果。

用法:
    python scripts/selftest.py                     # 默认测试文本
    python scripts/selftest.py "你的战役文本"       # 自定义文本
    python scripts/selftest.py --url http://localhost:8000
"""

from __future__ import annotations

import argparse
import contextlib
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

_THIS_DIR = Path(__file__).resolve().parent


def _compress_image(path: str, max_edge: int = 1280, quality: int = 85) -> str:
    """压缩截图：缩到最长边 max_edge，输出 JPEG。返回新路径。"""
    img = Image.open(path)
    w, h = img.size
    if max(w, h) > max_edge:
        ratio = max_edge / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    new_path = str(Path(path).with_suffix('.jpg'))
    img.save(new_path, format='JPEG', quality=quality, optimize=True)
    return new_path


_TEST_TEXT = (
    '王彦令焦文通部自东坡塬北侧列阵，弓弩手居前，步卒持长矛继后。'
    '郦琼部八百人出塬东小路，沿干涸河沟隐蔽南下，欲绕击金军左翼。'
    '娄室中军千骑自塬底直冲东坡塬正面，合扎猛安三百铁骑沿塬西缓坡迂回包抄。'
    '两军接战于塬腰梯田处，郦琼部突然从侧翼杀出，金军阵脚动摇，娄室收兵退守塬底旧寨。'
)


def _screenshot(url: str, text: str, output: str) -> tuple[list[str], list[str], dict]:
    """截图并返回 (errors, warnings, checks) 列表。"""
    from playwright.sync_api import sync_playwright

    errors: list[str] = []
    warnings: list[str] = []
    checks: dict = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})

        # 收集控制台错误和警告
        page.on(
            'console',
            lambda msg: (
                errors.append(f'[console.{msg.type}] {msg.text}')
                if msg.type == 'error'
                else warnings.append(f'[console.{msg.type}] {msg.text}')
                if msg.type == 'warning'
                else None
            ),
        )
        # 收集未捕获的 JS 异常
        page.on('pageerror', lambda err: errors.append(f'[pageerror] {err}'))

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

        # 程序化检查：通过浏览器 JS 获取地图状态
        try:
            # 先前进到最后一步，确保所有部队可见
            page.evaluate("""() => {
                if (typeof currentStep !== 'undefined' && typeof totalSteps !== 'undefined') {
                    for (var i = currentStep; i < totalSteps; i++) {
                        if (typeof stepTo === 'function') stepTo(i + 1);
                    }
                }
            }""")
            time.sleep(0.5)

            checks = page.evaluate("""() => {
                var result = {};
                // 1. 时间轴信息（从 JS 全局变量读取）
                result.totalSteps = (typeof totalSteps !== 'undefined') ? totalSteps : 0;
                result.currentStep = (typeof currentStep !== 'undefined') ? currentStep : 0;
                // 2. 地图中的部队标记数量（优先 CanvasRenderer，降级 MapLibre source）
                try {
                    var unitNames = [];
                    // CanvasRenderer 接管了 tactical/battle 模式下的部队渲染
                    if (typeof CanvasRenderer !== 'undefined' && CanvasRenderer.getUnitFeatures) {
                        var feats = CanvasRenderer.getUnitFeatures();
                        unitNames = feats.map(function(f) { return (f.properties && f.properties.unit_name) || ''; }).filter(Boolean);
                    } else {
                        var src = map.getSource('unit-banners');
                        if (src && src._data && src._data.features) {
                            unitNames = src._data.features.map(function(f) { return f.properties.unit_name; });
                        }
                    }
                    var uniqueUnits = [...new Set(unitNames)].sort();
                    result.unitBannerCount = unitNames.length;
                    result.uniqueUnits = uniqueUnits;
                } catch(e) {
                    result.mapError = e.message;
                }
                // 3. 当前可见的部队（通过检查 DOM 中的 marker 元素）
                try {
                    var markers = document.querySelectorAll('.maplibregl-marker, .comic-unit-marker, [class*="unit"]');
                    result.visibleMarkers = markers.length;
                } catch(e) {
                    result.visibleMarkers = -1;
                }
                return result;
            }""")
        except Exception as e:
            checks['eval_error'] = str(e)

        page.screenshot(path=output, full_page=True)
        print(f'→ 截图已保存: {output}')
        browser.close()

    return errors, warnings, checks


def main() -> None:
    parser = argparse.ArgumentParser(description='前端自测工具')
    parser.add_argument('text', nargs='?', default=_TEST_TEXT, help='战役文本')
    parser.add_argument('--url', default='http://localhost:8000', help='应用地址')
    args = parser.parse_args()

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        screenshot_path = f.name

    try:
        errors, warnings, checks = _screenshot(args.url, args.text, screenshot_path)
        old_size = Path(screenshot_path).stat().st_size
        screenshot_path = _compress_image(screenshot_path)
        new_size = Path(screenshot_path).stat().st_size
        print(f'→ 截图压缩: {old_size / 1024:.0f}KB → {new_size / 1024:.0f}KB')
        # 清理原始 PNG
        with contextlib.suppress(OSError):
            Path(screenshot_path).with_suffix('.png').unlink(missing_ok=True)
    except Exception as e:
        print(f'❌ 截图失败: {e}')
        sys.exit(1)

    # 输出程序化检查结果
    print('\n===== 程序化检查 =====')
    all_ok = True

    if checks.get('eval_error'):
        print(f'❌ JS 执行失败: {checks["eval_error"]}')
        all_ok = False

    total_steps = checks.get('totalSteps', 0)
    current_step = checks.get('currentStep', '?')
    banner_count = checks.get('unitBannerCount', 0)
    unique_units = checks.get('uniqueUnits', [])

    print(f'时间轴: 当前 {current_step} / 共 {total_steps} 步')
    print(f'部队标记 feature 数: {banner_count}')
    print(f'独立部队: {unique_units} ({len(unique_units)} 支)')

    # 基本完整性检查
    if len(unique_units) < 2:
        print(f'❌ 部队数量异常少: {len(unique_units)} 支 (预期至少 2)')
        all_ok = False
    else:
        print(f'✅ 部队数量正常: {len(unique_units)} 支')

    if total_steps < 1:
        print('❌ 未检测到时间轴步骤')
        all_ok = False
    else:
        print(f'✅ 时间轴步骤: {total_steps}')

    if not all_ok:
        print('\n⚠️ 程序化检查未通过，继续视觉分析...')
    else:
        print('\n✅ 程序化检查全部通过')

    # 输出控制台错误和警告
    if errors:
        print(f'\n⚠️  浏览器控制台错误 ({len(errors)} 条):')
        for err in errors:
            print(f'   {err[:200]}')
    else:
        print('\n✅ 浏览器控制台无错误')

    if warnings:
        print(f'\n🔶 浏览器控制台警告 ({len(warnings)} 条):')
        for w in warnings[:10]:
            print(f'   {w[:200]}')

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

    if not all_ok:
        print('\n❌ 自测未通过（程序化检查失败）')
        sys.exit(1)
    else:
        print('\n✅ 自测通过')


if __name__ == '__main__':
    main()
