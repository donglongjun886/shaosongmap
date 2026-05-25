"""自动化视觉审查：Playwright 驱动浏览器 → 填入文本 → 截图 → Qwen-VL Review。

用法:
    python scripts/automate_review.py
    python scripts/automate_review.py "你的战术文本"
    python scripts/automate_review.py --text "文本" --output report.md
    python scripts/automate_review.py --headless=false  # 可见浏览器调试

依赖:
    pip install playwright && playwright install chromium
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_TEST_TEXT = (
    "王贵率三千步卒据守黄龙岭。"
    "金军完颜宗弼遣两谋克骑兵从岭北仰攻。"
    "宋军张宪部自岭南迂回包抄，以弩手封锁山谷隘口。"
    "双方在岭腰松林激战。"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="自动化视觉审查")
    parser.add_argument("text", nargs="?", default=_TEST_TEXT, help="战役文本（可选，有默认战术级文本）")
    parser.add_argument("--output", "-o", default=None, help="审查报告输出文件（默认打印到终端）")
    parser.add_argument("--headless", default="true", choices=["true", "false"], help="是否无头模式（默认 true）")
    parser.add_argument("--url", default="http://localhost:8000", help="应用地址")
    parser.add_argument("--model", default="qwen-vl-max", help="Qwen-VL 模型")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("请先安装 playwright: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)

    print(f"📝 测试文本: {args.text[:60]}...")
    print(f"🌐 启动浏览器 (headless={args.headless})...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless == "true")
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # 1. 打开页面
        print("→ 打开页面...")
        page.goto(args.url, wait_until="networkidle")

        # 2. 等待 MapLibre 地图加载完毕
        print("→ 等待地图初始化...")
        page.wait_for_function("() => document.querySelector('#map canvas') !== null", timeout=15000)

        # 3. 填入文本
        print("→ 填入战役文本...")
        page.fill("#text-input", args.text)

        # 4. 勾选时间轴模式
        print("→ 勾选时间轴模式...")
        page.check("#mode-timeline")

        # 5. 点击生成地图
        print("→ 点击生成地图...")
        page.click("#submit-btn")

        # 6. 等待 SSE 返回 + 地图渲染完毕（mode-view 类出现即表示进入结果视图）
        print("→ 等待地图渲染...")
        page.wait_for_function("() => document.body.classList.contains('mode-view')", timeout=30000)

        # 额外等待动画/图层渲染稳定
        time.sleep(2)

        # 7. 检查是否有报错条
        error_visible = page.evaluate("() => document.getElementById('error-toast').classList.contains('show')")
        if error_visible:
            error_text = page.evaluate("() => document.getElementById('error-toast').innerText")
            print(f"⚠️  页面报错: {error_text}")

        # 8. 截图
        print("→ 截图...")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            screenshot_path = tmp.name
        page.screenshot(path=screenshot_path, full_page=True)
        browser.close()

    print(f"📸 截图: {screenshot_path}")

    # 9. 调用 vision.py --review
    print(f"🔍 调用 Qwen-VL 审查 ({args.model})...\n")
    vision_script = Path(__file__).parent / "vision.py"
    result = subprocess.run(
        [sys.executable, str(vision_script), "--review", "--model", args.model, screenshot_path],
        capture_output=True, text=True, timeout=120,
    )

    if result.returncode != 0:
        print(f"vision.py 出错: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    report = result.stdout

    # 清理临时文件
    Path(screenshot_path).unlink(missing_ok=True)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"✅ 报告已写入: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()