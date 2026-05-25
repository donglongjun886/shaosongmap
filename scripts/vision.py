"""视觉模型辅助工具：调用 Qwen-VL 看图并返回文字描述。

用法:
    # 通用模式：自由提问
    python scripts/vision.py screenshot.png
    python scripts/vision.py screenshot.png "旗帜标记位置偏了吗？"

    # Review 模式：结构化 UI 审查报告
    python scripts/vision.py --review screenshot.png
    python scripts/vision.py --review --model qwen-vl-max screenshot.png
    python scripts/vision.py --review screenshot.png "只看时间轴面板"

环境变量:
    DASHSCOPE_API_KEY: 阿里云百炼 API Key
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-vl-plus"
REVIEW_MODEL = "qwen-vl-max"

DEFAULT_QUESTION = (
    "请仔细观察这张截图，描述你看到的内容。"
    "如果有任何视觉问题（布局错位、颜色异常、元素重叠、缺失、文字截断等），请逐一指出。"
)

REVIEW_SYSTEM = """你是一位资深 UI/UX 审查专家，专门审查历史地图可视化应用的界面截图。
你的任务是逐像素检查截图中的视觉缺陷，输出结构化的审查报告。

## 审查维度（按优先级）

0. **运行时错误**（最高优先级）：页面顶部或任意位置是否出现红色错误提示条/弹窗/报错文字（如 "JS ERROR"、"PROMISE ERROR"、红底白字的报错信息）。出现任何运行时错误都是 🔴高 优先级，必须在报告中第一个指出。
1. **布局与对齐**：元素重叠、错位、溢出容器、间距不一致
2. **文字与可读性**：标签截断/溢出、字体大小不一、对比度不足、中文乱码
3. **颜色与风格**：配色不一致、与古地图视觉体系（宣纸色 #f2e8d5、朱砂红 #c23b22、靛青 #2b4c7e）不协调
4. **地图标记**：旗帜图标位置偏移、方向线断开、双线框单边缺失、标记与地名标签重叠
5. **交互控件**：按钮溢出、下拉框样式异常、时间轴步骤显示不全

## 输出格式

每个问题严格按以下格式输出（无问题的维度直接跳过）：

### 维度名
- [严重程度] 位置：xxx | 问题：xxx | 建议：xxx

严重程度取值：🔴高（影响使用）/ 🟡中（影响美观）/ 🟢低（微调）

总评：最后用一句话总结整体状态，指出最需要优先修复的问题。"""


def _image_to_base64(image_path: str) -> str:
    """将图片文件编码为 base64 data URL。"""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    ext = path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime = mime_map.get(ext)
    if not mime:
        raise ValueError(f"不支持的图片格式: {ext}，支持 png/jpg/jpeg/webp")

    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def analyze(
    image_path: str,
    question: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 2000,
) -> str:
    """调用 Qwen-VL 分析图片并返回文字描述。"""
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        raise ValueError("请设置环境变量 DASHSCOPE_API_KEY（阿里云百炼 API Key）")

    data_url = _image_to_base64(image_path)
    prompt = question or DEFAULT_QUESTION

    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    messages: list[dict] = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.3,
    )

    content = response.choices[0].message.content
    return content.strip() if content else "（模型返回空内容）"


def review(
    image_path: str,
    focus: str | None = None,
    model: str = REVIEW_MODEL,
) -> str:
    """Review 模式：输出结构化的 UI 审查报告。

    Args:
        image_path: 截图路径
        focus: 可选的关注区域（如「只看时间轴面板」）
        model: 模型名称，默认 qwen-vl-max
    """
    focus_line = f"\n本次审查请重点关注：{focus}" if focus else ""
    user_prompt = f"请审查这张应用截图，输出结构化审查报告。{focus_line}"

    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        raise ValueError("请设置环境变量 DASHSCOPE_API_KEY（阿里云百炼 API Key）")

    data_url = _image_to_base64(image_path)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": REVIEW_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": user_prompt},
                ],
            },
        ],
        max_tokens=3000,
        temperature=0.3,
    )

    content = response.choices[0].message.content
    return content.strip() if content else "（模型返回空内容）"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="视觉模型辅助工具：看图分析 / UI 审查",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/vision.py screenshot.png
  python scripts/vision.py --review screenshot.png
  python scripts/vision.py --review --model qwen-vl-max screenshot.png
  python scripts/vision.py --review screenshot.png "只看旗帜标记"
        """,
    )
    parser.add_argument("image", help="图片文件路径")
    parser.add_argument("question", nargs="?", default=None, help="具体问题（可选）")
    parser.add_argument(
        "--review", "-r", action="store_true", help="启用 Review 模式，输出结构化审查报告"
    )
    parser.add_argument(
        "--model", "-m", default=None, help=f"模型名称（默认: 通用模式={DEFAULT_MODEL}, Review模式={REVIEW_MODEL}）"
    )
    args = parser.parse_args()

    try:
        if args.review:
            model = args.model or REVIEW_MODEL
            result = review(args.image, focus=args.question, model=model)
        else:
            model = args.model or DEFAULT_MODEL
            result = analyze(args.image, question=args.question, model=model)
        print(result)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
