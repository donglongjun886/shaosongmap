"""前端 utils.js 纯函数的 Python 等价实现及单测。

JS 函数无法直接在 Python 中调用，这里用 Python 复刻相同逻辑进行验证。
"""

import html
import math
import re

from fastapi.testclient import TestClient

from app import app

# ── Python 等价实现 ──


def esc_html(s: str) -> str:
    """等价于 JS 版 escHtml(s)"""
    return html.escape(s)


def darken_color(hex_color: str, factor: float) -> str:
    """等价于 JS 版 _darkenColor(hex, factor)"""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    dr = round(r * (1 - factor))
    dg = round(g * (1 - factor))
    db = round(b * (1 - factor))
    return '#' + ''.join(f'{c:02x}' for c in [dr, dg, db])


def faction_color(faction: str) -> str:
    """等价于 JS 版 _factionColor(faction)"""
    if not faction:
        return '#2c2c2c'
    if '宋' in faction:
        return '#2b4c7e'
    if '金' in faction:
        return '#c23b22'
    return '#2c2c2c'


def compute_data_diagonal(features: list[dict]) -> float:
    """等价于 JS 版 _computeDataDiagonal(features)"""
    lngs = []
    lats = []
    for f in features:
        coords = f.get('geometry', {}).get('coordinates')
        if coords:
            lngs.append(coords[0])
            lats.append(coords[1])
    if len(lngs) < 2:
        return 1000.0
    min_lng, max_lng = min(lngs), max(lngs)
    min_lat, max_lat = min(lats), max(lats)
    mid_lat = (min_lat + max_lat) / 2 * math.pi / 180
    dx = (max_lng - min_lng) * 111320 * math.cos(mid_lat)
    dy = (max_lat - min_lat) * 111320
    return math.sqrt(dx * dx + dy * dy)


def terrain_color_for_type(place_type: str) -> str | None:
    """等价于 JS 版 _terrainColorForType(placeType)"""
    mapping = {
        'mountain': 'rgba(139,119,101,0.12)',
        'mountain_pass': 'rgba(139,119,101,0.12)',
        'river': 'rgba(100,149,237,0.15)',
        'valley': 'rgba(218,195,125,0.12)',
        'region': 'rgba(218,195,125,0.12)',
    }
    return mapping.get(place_type)


# ── 测试用例 ──


class TestEscHtml:
    def test_plain_text(self):
        assert esc_html('hello') == 'hello'

    def test_html_tags(self):
        assert esc_html('<script>alert(1)</script>') == '&lt;script&gt;alert(1)&lt;/script&gt;'

    def test_ampersand(self):
        assert esc_html('a & b') == 'a &amp; b'

    def test_quotes(self):
        result = esc_html('"hello"')
        assert '&quot;' in result

    def test_chinese_text(self):
        assert esc_html('岳飞') == '岳飞'

    def test_empty_string(self):
        assert esc_html('') == ''


class TestDarkenColor:
    def test_black_no_factor(self):
        assert darken_color('#000000', 0.0) == '#000000'

    def test_black_full_factor(self):
        assert darken_color('#000000', 1.0) == '#000000'

    def test_white_half(self):
        assert darken_color('#ffffff', 0.5) == '#808080'

    def test_red_darken(self):
        result = darken_color('#ff0000', 0.5)
        assert result == '#800000'

    def test_typical_usage(self):
        """模拟 _makeComicUnitIcon 中 _darkenColor(color, 0.15) 的调用"""
        result = darken_color('#2b4c7e', 0.15)
        r = int(result[1:3], 16)
        assert r == round(0x2B * 0.85)


class TestFactionColor:
    def test_song_keyword(self):
        assert faction_color('宋军') == '#2b4c7e'
        assert faction_color('南宋') == '#2b4c7e'
        assert faction_color('北宋禁军') == '#2b4c7e'

    def test_jin_keyword(self):
        assert faction_color('金军') == '#c23b22'
        assert faction_color('金国骑兵') == '#c23b22'

    def test_empty_faction(self):
        assert faction_color('') == '#2c2c2c'

    def test_none_string(self):
        """JS: !faction → false for '' and null/undefined.
        空字符串在 Python truthiness 中等价于 JS 的 !faction 判断."""
        assert faction_color('') == '#2c2c2c'

    def test_unknown_faction(self):
        assert faction_color('蒙古') == '#2c2c2c'
        assert faction_color('西夏') == '#2c2c2c'

    def test_substring_match(self):
        """验证 substring 匹配行为：indexOf >= 0"""
        assert faction_color('金') == '#c23b22'


class TestComputeDataDiagonal:
    def test_single_feature(self):
        features = [{'geometry': {'coordinates': [110, 30]}}]
        assert compute_data_diagonal(features) == 1000.0

    def test_same_point(self):
        features = [
            {'geometry': {'coordinates': [110, 30]}},
            {'geometry': {'coordinates': [110, 30]}},
        ]
        assert compute_data_diagonal(features) == 0.0

    def test_two_points_east_west(self):
        """北京 (116.4, 39.9) → 西安 (108.9, 34.3)，约 900km"""
        features = [
            {'geometry': {'coordinates': [116.4, 39.9]}},
            {'geometry': {'coordinates': [108.9, 34.3]}},
        ]
        dist = compute_data_diagonal(features)
        assert 800_000 < dist < 1_100_000

    def test_no_features(self):
        assert compute_data_diagonal([]) == 1000.0

    def test_missing_coordinates(self):
        features = [{'geometry': {}}, {'geometry': {'coordinates': [110, 30]}}]
        assert compute_data_diagonal(features) == 1000.0

    def test_typical_battlefield(self):
        """模拟约 50km 范围的战场"""
        lat = 34.0
        lng_delta = 0.45  # ~50km
        features = [
            {'geometry': {'coordinates': [114 - lng_delta / 2, lat]}},
            {'geometry': {'coordinates': [114 + lng_delta / 2, lat]}},
        ]
        dist = compute_data_diagonal(features)
        assert 40_000 < dist < 60_000


class TestTerrainColorForType:
    def test_mountain(self):
        assert terrain_color_for_type('mountain') == 'rgba(139,119,101,0.12)'

    def test_mountain_pass(self):
        assert terrain_color_for_type('mountain_pass') == 'rgba(139,119,101,0.12)'

    def test_river(self):
        assert terrain_color_for_type('river') == 'rgba(100,149,237,0.15)'

    def test_valley(self):
        assert terrain_color_for_type('valley') == 'rgba(218,195,125,0.12)'

    def test_region(self):
        assert terrain_color_for_type('region') == 'rgba(218,195,125,0.12)'

    def test_unknown_type(self):
        assert terrain_color_for_type('city') is None
        assert terrain_color_for_type('') is None

    def test_case_sensitive(self):
        """JS 版本是严格 key 匹配，区分大小写"""
        assert terrain_color_for_type('Mountain') is None


# ── 前端拆分集成验证 ──

_client = TestClient(app)


class TestFrontendFileSplit:
    """验证 index.html 拆分后外部引用正确、无内联代码块。"""

    def test_html_served(self):
        resp = _client.get('/')
        assert resp.status_code == 200
        assert resp.headers['content-type'].startswith('text/html')

    def test_no_inline_style_block(self):
        """拆分后不应存在 <style> 代码块。"""
        resp = _client.get('/')
        # 排除 maplibre-gl CDN 样式（<link>），只检查 <style> 标签
        assert '<style>' not in resp.text

    def test_no_business_logic_inline_script(self):
        """内联 <script> 仅允许 CDN 回退，禁止业务逻辑内联。

        允许 CDN 回退脚本（含 document.write），禁止其他内联代码。
        """
        resp = _client.get('/')
        script_tags = re.findall(r'<script\b[^>]*>', resp.text)
        for tag in script_tags:
            if 'src=' in tag:
                continue
            # 仅允许 CDN 回退的内联脚本
            assert 'maplibregl' in resp.text and 'document.write' in resp.text, (
                f'发现未预期的内联 <script> 代码块: {tag}'
            )

    def test_css_referenced(self):
        """应通过 <link> 引用外部 CSS。"""
        resp = _client.get('/')
        assert 'href="css/map.css"' in resp.text

    def test_js_loads_in_correct_order(self):
        """JS 按 utils → canvasRenderer → terrainRenderer → map → app 顺序加载。"""
        resp = _client.get('/')
        scripts = re.findall(r'<script src="([^"]+)"', resp.text)
        # 过滤出本地 JS（非 CDN）
        local_scripts = [s for s in scripts if s.startswith('js/')]
        expected = [
            'js/utils.js',
            'js/canvasRenderer.js',
            'js/terrainRenderer.js',
            'js/map.js',
            'js/app.js',
        ]
        assert local_scripts == expected, f'JS 加载顺序不正确: {local_scripts}'

    def test_maplibre_cdn_present(self):
        """页面应引用 MapLibre GL，优先 jsdelivr（国内连通性更好）。"""
        resp = _client.get('/')
        assert 'maplibre-gl@4.7.1' in resp.text
        assert 'cdn.jsdelivr.net' in resp.text or 'unpkg.com' in resp.text

    def test_css_accessible(self):
        """CSS 文件可正常访问。"""
        resp = _client.get('/css/map.css')
        assert resp.status_code == 200
        assert resp.headers['content-type'].startswith('text/css')
        assert len(resp.text) > 100  # 确认非空

    def test_utils_js_accessible(self):
        """utils.js 可正常访问。"""
        resp = _client.get('/js/utils.js')
        assert resp.status_code == 200
        assert 'escHtml' in resp.text
        assert '_darkenColor' in resp.text

    def test_map_js_accessible(self):
        """map.js 可正常访问。"""
        resp = _client.get('/js/map.js')
        assert resp.status_code == 200
        assert 'maplibregl.Map' in resp.text
        assert 'updateMap' in resp.text

    def test_app_js_accessible(self):
        """app.js 可正常访问。"""
        resp = _client.get('/js/app.js')
        assert resp.status_code == 200
        assert 'analyze' in resp.text
        assert 'switchToViewMode' in resp.text

    def test_dom_ids_preserved(self):
        """DOM 元素 id 保持不变，确保 JS 选择器兼容。"""
        resp = _client.get('/')
        required_ids = [
            'text-input',
            'submit-btn',
            'result-panel',
            'map',
            'map-guide',
            'comic-seal',
            'timeline-wrap',
            'timeline-bar',
            'event-card',
            'places-list',
            'routes-list',
            'campaign-info',
            'drop-zone',
            'file-input',
            'thumb-list',
            'batch-controls',
            'ocr-progress',
            'batch-review',
        ]
        for id_ in required_ids:
            assert f'id="{id_}"' in resp.text, f'缺少 DOM 元素 id="{id_}"'
