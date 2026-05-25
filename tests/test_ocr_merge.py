"""测试多截图文本去重拼接功能。"""

from shaosongmap.ocr import merge_texts


class TestMergeTexts:
    """merge_texts 函数的单元测试。"""

    def test_single_text(self):
        """单段文本直接返回原文本。"""
        text, removed = merge_texts(['这是唯一的一段文本内容'])
        assert text == '这是唯一的一段文本内容'
        assert removed == 0

    def test_empty_list(self):
        """空列表返回空字符串。"""
        text, removed = merge_texts([])
        assert text == ''
        assert removed == 0

    def test_no_overlap(self):
        """无重叠的相邻文本直接拼接。"""
        text, removed = merge_texts(
            [
                '第一章开始了新的征程',
                '第二章讲述了不同的故事',
            ]
        )
        assert '第一章开始了新的征程第二章讲述了不同的故事' in text
        assert removed == 0

    def test_with_overlap(self):
        """有尾部/头部重叠的情况。"""
        text, removed = merge_texts(
            [
                '刘备率军西进，于建安二十四年抵达汉中。',
                '于建安二十四年抵达汉中。诸葛亮在帐中献策。',
            ]
        )
        expected = '刘备率军西进，于建安二十四年抵达汉中。诸葛亮在帐中献策。'
        assert text == expected
        assert removed > 0

    def test_three_texts_pairwise_overlap(self):
        """三张图两两之间有重叠。"""
        text, removed = merge_texts(
            [
                '第一段文本的结尾部分这里是重叠内容',
                '这里是重叠内容第二段正文继续讲述更多',
                '继续讲述更多第三段的开头部分在这里结束',
            ]
        )
        expected = (
            '第一段文本的结尾部分这里是重叠内容第二段正文继续讲述更多第三段的开头部分在这里结束'
        )
        assert text == expected
        assert removed > 0

    def test_short_overlap_ignored(self):
        """重叠少于5字符时忽略不去重。"""
        text, removed = merge_texts(
            [
                '这是一段完整的文本内容。',
                '。另一段文本开始',
            ]
        )
        # 只有句号重叠（2字符），不应去重
        assert text == '这是一段完整的文本内容。。另一段文本开始'
        assert removed == 0

    def test_complete_duplicate(self):
        """两段完全相同的文本（同一张图传了两次）。"""
        text, removed = merge_texts(
            [
                '完全相同的文本内容被重复上传了',
                '完全相同的文本内容被重复上传了',
            ]
        )
        assert text == '完全相同的文本内容被重复上传了'
        assert removed == len('完全相同的文本内容被重复上传了')

    def test_overlap_at_boundary(self):
        """重叠恰好在200字符窗口边界。"""
        # 构建一个刚好在200字符前后的重叠场景
        prefix = '前' * 150 + '开始重叠部分ABC'
        suffix = '开始重叠部分ABC' + '后' * 100
        text, removed = merge_texts([prefix, suffix])
        assert '前' * 150 in text
        assert '后' * 100 in text
        assert removed >= len('开始重叠部分ABC')
        # 重叠部分不应重复出现
        assert text.count('开始重叠部分ABC') == 1
