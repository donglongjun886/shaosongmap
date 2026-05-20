"""截图 OCR 模块：通过 PaddleOCR 识别截图文字并清洗为连续文本。"""

from __future__ import annotations

import io
import re

import numpy as np
from PIL import Image

_UI_KEYWORDS = {
    "上一章", "下一章", "目录", "书架", "设置", "评论", "分享",
    "打赏", "投票", "推荐票", "月票", "订阅", "加入书架",
    "下载", "听书", "全文搜索", "书签", "笔记", "本章说",
    "发表评论", "查看更多", "举报", "催更", "加更", "追书",
    "夜间", "白天", "字体", "字号", "亮度",
    "讨论热烈", "本章含", "条段评", "段评", "起点中文网",
}

# 起点 App 顶部信息栏正则：匹配 "书名 作者 品X字 日期 时间" 格式
_BOOK_INFO_PATTERN = re.compile(
    r"品?\d+字\d{4}年\d{1,2}月\d{1,2}日\d{1,2}[:：]\d{2}"
)

# 评论区噪音正则：如 "?讨论热烈：本章含2672条段评"
_COMMENT_HEADER_PATTERN = re.compile(
    r"讨论热烈.*本章含\d+条段评"
)

_MIN_TEXT_LENGTH = 50


def _init_ocr():
    """延迟初始化 PaddleOCR（首次调用时加载模型）。"""
    from paddleocr import PaddleOCR
    return PaddleOCR(
        lang="ch",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        _ocr = _init_ocr()
    return _ocr


def _clean_text(raw_lines: list[str]) -> str:
    """清洗 OCR 识别结果。

    规则：
    1. 移除长度 < 6 个中文字符的行
    2. 移除匹配 UI 关键词的行
    3. 非中文占比过高的行丢弃
    4. 合并连续段落行

    Args:
        raw_lines: OCR 识别的原始文本行列表

    Returns:
        清洗合并后的连续文本
    """
    cleaned: list[str] = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue

        # 统计中文字符数
        chinese_chars = len(re.findall(r"[一-鿿]", line))
        total_chars = len(line.replace(" ", ""))

        # 太短的行跳过
        if chinese_chars < 6:
            continue

        # 中文占比太低的行跳过（可能是 URL、代码等）
        if total_chars > 0 and chinese_chars / total_chars < 0.3:
            continue

        # 匹配 UI 关键词
        line_clean = line.strip()
        is_ui = False
        for keyword in _UI_KEYWORDS:
            if keyword in line_clean:
                is_ui = True
                break
        if is_ui:
            continue

        # 匹配起点 App 信息栏和评论区噪音
        if _BOOK_INFO_PATTERN.search(line_clean):
            continue
        if _COMMENT_HEADER_PATTERN.search(line_clean):
            continue

        cleaned.append(line_clean)

    # 合并为连续段落
    text = "".join(cleaned)
    return text


def recognize(image_bytes: bytes) -> list[str]:
    """对图片进行 OCR 识别，返回原始文本行列表。

    Args:
        image_bytes: PNG 或 JPEG 图片的字节数据

    Returns:
        OCR 识别的每行文本
    """
    # 将 bytes 转换为 numpy array（PaddleOCR 3.x 要求）
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert("RGB")
    image_np = np.array(image)

    ocr = _get_ocr()
    results = ocr.predict(image_np)
    if not results or not results[0]:
        return []

    result = results[0]
    # PaddleOCR 3.x 返回 dict-like OCRResult，识别的文本在 rec_texts 中
    rec_texts = result["rec_texts"]
    lines: list[str] = []
    for text in rec_texts:
        if text.strip():
            lines.append(text.strip())

    return lines


def ocr_main(image_bytes: bytes) -> tuple[str, int]:
    """OCR 识别 + 清洗的主入口。

    接收截图字节数据，返回清洗后的连续文本和原始识别行数。
    清洗后文本不足 50 字符时抛出异常。

    Args:
        image_bytes: 截图图片字节数据

    Returns:
        (清洗后的连续文本段落, OCR 原始识别行数)

    Raises:
        ValueError: 识别或清洗后文本不足 50 字符
    """
    raw_lines = recognize(image_bytes)

    if not raw_lines:
        raise ValueError("未能识别到任何文字，请检查截图是否清晰")

    text = _clean_text(raw_lines)

    if len(text) < _MIN_TEXT_LENGTH:
        raise ValueError(
            f"未能从截图中提取到足够的文本（仅 {len(text)} 字符），"
            "请确保截图包含正文内容"
        )

    return text, len(raw_lines)
