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
        text_det_limit_side_len=960,
        text_det_limit_type="max",
        text_det_thresh=0.3,
        text_det_box_thresh=0.5,
        text_recognition_batch_size=8,
    )


_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        _ocr = _init_ocr()
    return _ocr


def _preprocess_image(image: Image.Image) -> Image.Image:
    """对截图预处理：大图缩放到合理尺寸以加速 OCR 检测。

    阅读 App 截图的文字通常清晰大号，缩小到长边 1600px
    几乎不影响识别准确率，但可大幅减少检测耗时。
    """
    import logging
    logger = logging.getLogger(__name__)
    max_dim = 1600
    w, h = image.size
    long_side = max(w, h)
    if long_side <= max_dim:
        return image
    scale = max_dim / long_side
    new_w = int(w * scale)
    new_h = int(h * scale)
    logger.info("图片缩放: %dx%d → %dx%d (提速约 %.0f%%)",
                w, h, new_w, new_h, (1 - scale**2) * 100)
    return image.resize((new_w, new_h), Image.LANCZOS)


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
    # 预处理：大图缩放到合理尺寸，加速检测
    image = _preprocess_image(image)
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


def _longest_common_substring(s1: str, s2: str) -> tuple[int, int]:
    """在 s1 和 s2 中查找最长公共子串。

    使用动态规划，O(m*n) 复杂度。用于相邻截图文的重叠检测。

    Args:
        s1: 前一段文本的尾部（最多 200 字符）
        s2: 后一段文本的头部（最多 200 字符）

    Returns:
        (s2_start, length): 公共子串在 s2 中的起始位置和长度
    """
    m, n = len(s1), len(s2)
    if m == 0 or n == 0:
        return 0, 0

    prev = [0] * (n + 1)
    max_len = 0
    start_s2 = 0

    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                curr[j] = prev[j - 1] + 1
                if curr[j] > max_len:
                    max_len = curr[j]
                    start_s2 = j - curr[j]
        prev = curr

    return start_s2, max_len


def merge_texts(texts: list[str]) -> tuple[str, int]:
    """对多段 OCR 清洗后文本进行相邻去重拼接。

    对相邻文本段执行前后缀最长公共子串匹配，自动去除截图之间的
    重叠部分后拼接为完整文本。匹配窗口限定在 200 字符以内。

    Args:
        texts: 按截图顺序排列的 OCR 清洗后文本列表

    Returns:
        (拼接后完整文本, 去除的重复字符总数)
    """
    if not texts:
        return "", 0
    if len(texts) == 1:
        return texts[0], 0

    result = texts[0]
    total_removed = 0

    for i in range(1, len(texts)):
        next_text = texts[i]
        # 取累计结果的尾部和下一段文本的头部进行匹配
        tail = result[-200:] if len(result) > 200 else result
        head = next_text[:200] if len(next_text) > 200 else next_text

        start_s2, length = _longest_common_substring(tail, head)

        if length >= 5:
            overlap = head[start_s2:start_s2 + length]
            idx = next_text.find(overlap)
            if idx >= 0:
                next_text = next_text[idx + length:]
                total_removed += length

        result += next_text

    return result, total_removed


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
