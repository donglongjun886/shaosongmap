"""OCR 清洗逻辑单元测试。"""

from __future__ import annotations

import pytest

from shaosongmap.ocr import _clean_text, _remove_comment_markers, ocr_main


class TestRemoveCommentMarkers:
    """起点评论区上标数字清洗测试。"""

    def test_unicode_superscript_removed(self):
        """Unicode 上标数字被移除。"""
        text = '诸葛亮率军北伐¹²魏延提出子午谷奇谋³诸葛亮不从'
        result = _remove_comment_markers(text)
        assert '¹' not in result
        assert '²' not in result
        assert '³' not in result
        assert result == '诸葛亮率军北伐魏延提出子午谷奇谋诸葛亮不从'

    def test_bracket_comment_removed(self):
        """方括号评论编号 [n] 被移除。"""
        text = '岳飞率军[1]进攻襄阳[23]金军大败[3,4,5]而逃'
        result = _remove_comment_markers(text)
        assert '[1]' not in result
        assert '[23]' not in result
        assert '[3,4,5]' not in result
        assert result == '岳飞率军进攻襄阳金军大败而逃'

    def test_legitimate_numbers_preserved(self):
        """正文中的合法数字不受影响。"""
        text = '斩首三千级，缴获战马五百匹，行军二百余里'
        result = _remove_comment_markers(text)
        assert '三千' in result
        assert '五百' in result
        assert '二百' in result

    def test_clean_text_integration(self):
        """_clean_text 整体流程中包含评论标记清洗。"""
        lines = [
            '岳飞率三万兵马自襄阳¹²渡汉水[1]',
            '经唐州、邓州直驱汴京而去[2,3]',
        ]
        result = _clean_text(lines)
        assert '¹' not in result
        assert '²' not in result
        assert '[1]' not in result
        assert '[2,3]' not in result
        assert '岳飞' in result
        assert '襄阳' in result
        assert '汴京' in result

    def test_no_markers_unchanged(self):
        """没有评论标记的文本原样返回。"""
        text = '岳飞率三万兵马自襄阳渡汉水，经唐州、邓州直驱汴京而去。'
        result = _remove_comment_markers(text)
        assert result == text

    def test_post_punctuation_digits_removed(self):
        """句号后紧跟的孤立数字被移除。"""
        text = '宋军大振。14相对应来说，王彦放弃了督战。'
        result = _remove_comment_markers(text)
        assert '14' not in result
        assert '宋军大振。相对应来说' in result

    def test_ellipsis_post_digits_removed(self):
        """省略号后的评论数字被移除。"""
        text = '以成奇功的......5但完颜娄室不可能给他机会。'
        result = _remove_comment_markers(text)
        assert '5' not in result
        assert '以成奇功的......但完颜娄室' in result

    def test_real_text_snippet(self):
        """真实起点文本片段：14和5被移除，122因后接「两」受数量词保护保留。

        122不被移除是可接受的：宁可漏删也不误删正文数字。
        后续如果同模式的误漏增多，再考虑放宽排除条件。
        """
        text = (
            '心照不宣了。14相对应来说，王彦也就早已经放弃了督战'
            '以成奇功的。5但完颜娄室不可能给他这个机会'
            '重甲骑兵的碾压。122两支从阿骨打时代就精选设立的合扎猛安'
        )
        result = _remove_comment_markers(text)
        assert '14' not in result
        assert '5' not in result
        # 122 因后接「两」受数量词保护，未移除（已知局限）

    def test_quantity_number_preserved(self):
        """句号后数字紧跟数量词（如5万）时保留，不误删。"""
        text = '金军势大。5万铁骑从侧翼杀出。'
        result = _remove_comment_markers(text)
        assert '5万' in result

    def test_shi_yu_number_preserved(self):
        """句号后'10余'保留不误删。"""
        text = '宋军溃散。10余人被俘。'
        result = _remove_comment_markers(text)
        assert '10余' in result
        result = _remove_comment_markers(text)
        assert result == text


class TestCleanText:
    def test_normal_text(self):
        """正常正文段落原样保留合并。"""
        lines = [
            '岳飞率三万兵马自襄阳渡汉水',
            '经唐州、邓州直驱汴京而去',
        ]
        result = _clean_text(lines)
        assert '岳飞' in result
        assert '襄阳' in result
        assert '汴京' in result

    def test_short_lines_removed(self):
        """短于 6 个中文字的行被丢弃。"""
        lines = [
            '第十二章',  # 3 个中文字，应丢弃
            '岳飞率三万兵马自襄阳出发北伐',  # 足够长，保留
            '上一章',  # UI 关键词，丢弃
        ]
        result = _clean_text(lines)
        assert '岳飞' in result
        assert '第十二章' not in result  # 中文不足 6 字
        assert '上一章' not in result  # UI 关键词

    def test_ui_keywords_removed(self):
        """起点 App 常见 UI 关键词被过滤。"""
        lines = [
            '岳飞大军抵达汴京城下',
            '加入书架 下载 目录',
            '金军完颜宗弼率五万大军迎战',
            '上一章 下一章',
        ]
        result = _clean_text(lines)
        assert '岳飞大军' in result
        assert '完颜宗弼' in result
        assert '加入书架' not in result
        assert '上一章' not in result

    def test_too_few_chinese_chars(self):
        """中文占比过低的英文/数字行被丢弃。"""
        lines = [
            '岳飞大军抵达汴京城下',
            'Chapter 312 The Northern Expedition 2024-03-15',
        ]
        result = _clean_text(lines)
        assert '岳飞大军' in result
        assert 'Chapter' not in result


class TestOcrMain:
    def test_insufficient_text(self, monkeypatch):
        """清洗后文本不足 50 字时抛出 ValueError。"""

        def mock_recognize(_bytes):
            return ['岳飞', '北伐']

        monkeypatch.setattr('shaosongmap.ocr.recognize', mock_recognize)
        with pytest.raises(ValueError, match='足够的文本'):
            ocr_main(b'fake_image')

    def test_empty_recognition(self, monkeypatch):
        """OCR 未识别到任何文字时抛出 ValueError。"""

        def mock_recognize(_bytes):
            return []

        monkeypatch.setattr('shaosongmap.ocr.recognize', mock_recognize)
        with pytest.raises(ValueError, match='任何文字'):
            ocr_main(b'fake_image')
