"""OCR 清洗逻辑单元测试。"""

from __future__ import annotations

import pytest

from shaosongmap.ocr import _clean_text, ocr_main


class TestCleanText:
    def test_normal_text(self):
        """正常正文段落原样保留合并。"""
        lines = [
            "岳飞率三万兵马自襄阳渡汉水",
            "经唐州、邓州直驱汴京而去",
        ]
        result = _clean_text(lines)
        assert "岳飞" in result
        assert "襄阳" in result
        assert "汴京" in result

    def test_short_lines_removed(self):
        """短于 6 个中文字的行被丢弃。"""
        lines = [
            "第十二章",                       # 3 个中文字，应丢弃
            "岳飞率三万兵马自襄阳出发北伐",     # 足够长，保留
            "上一章",                         # UI 关键词，丢弃
        ]
        result = _clean_text(lines)
        assert "岳飞" in result
        assert "第十二章" not in result   # 中文不足 6 字
        assert "上一章" not in result     # UI 关键词

    def test_ui_keywords_removed(self):
        """起点 App 常见 UI 关键词被过滤。"""
        lines = [
            "岳飞大军抵达汴京城下",
            "加入书架 下载 目录",
            "金军完颜宗弼率五万大军迎战",
            "上一章 下一章",
        ]
        result = _clean_text(lines)
        assert "岳飞大军" in result
        assert "完颜宗弼" in result
        assert "加入书架" not in result
        assert "上一章" not in result

    def test_too_few_chinese_chars(self):
        """中文占比过低的英文/数字行被丢弃。"""
        lines = [
            "岳飞大军抵达汴京城下",
            "Chapter 312 The Northern Expedition 2024-03-15",
        ]
        result = _clean_text(lines)
        assert "岳飞大军" in result
        assert "Chapter" not in result


class TestOcrMain:
    def test_insufficient_text(self, monkeypatch):
        """清洗后文本不足 50 字时抛出 ValueError。"""
        def mock_recognize(_bytes):
            return ["岳飞", "北伐"]
        monkeypatch.setattr("shaosongmap.ocr.recognize", mock_recognize)
        with pytest.raises(ValueError, match="足够的文本"):
            ocr_main(b"fake_image")

    def test_empty_recognition(self, monkeypatch):
        """OCR 未识别到任何文字时抛出 ValueError。"""
        def mock_recognize(_bytes):
            return []
        monkeypatch.setattr("shaosongmap.ocr.recognize", mock_recognize)
        with pytest.raises(ValueError, match="任何文字"):
            ocr_main(b"fake_image")