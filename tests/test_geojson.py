"""services/geojson.py 单元测试：GeoJSON 构建（仅 Point 类型）。"""

from shaosongmap.models import GeoFeature
from shaosongmap.services.geojson import make_geojson


class TestMakeGeojson:
    def test_basic_feature_collection(self):
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0, source='chgis')]
        result = make_geojson(features)
        assert result['type'] == 'FeatureCollection'
        assert len(result['features']) == 1
        feat = result['features'][0]
        assert feat['type'] == 'Feature'
        assert feat['geometry']['type'] == 'Point'
        assert feat['geometry']['coordinates'] == [114.0, 34.0]
        assert feat['properties']['name'] == '汴京'

    def test_feature_with_null_coords_excluded(self):
        """双坐标均为 null 时要素被排除。"""
        features = [GeoFeature(name='未知地', lng=None, lat=None)]
        result = make_geojson(features)
        assert len(result['features']) == 0

    def test_single_null_lng_excluded(self):
        """仅经度为 null 时要素也被排除（单边 null 不可生成有效坐标）。"""
        features = [GeoFeature(name='半未知', lng=None, lat=34.0)]
        result = make_geojson(features)
        assert len(result['features']) == 0

    def test_single_null_lat_excluded(self):
        """仅纬度为 null 时要素也被排除。"""
        features = [GeoFeature(name='半未知', lng=114.0, lat=None)]
        result = make_geojson(features)
        assert len(result['features']) == 0

    def test_empty_features(self):
        result = make_geojson([])
        assert result['type'] == 'FeatureCollection'
        assert result['features'] == []

    def test_properties_include_all_fields(self):
        features = [
            GeoFeature(
                name='汴京',
                lng=114.0,
                lat=34.0,
                source='llm_infer',
                modern_name='开封',
                confidence='high',
                place_type='city',
            )
        ]
        result = make_geojson(features)
        props = result['features'][0]['properties']
        assert props['name'] == '汴京'
        assert props['source'] == 'llm_infer'
        assert props['modern_name'] == '开封'
        assert props['confidence'] == 'high'
        assert props['place_type'] == 'city'

    def test_multiple_points(self):
        features = [
            GeoFeature(name='汴京', lng=114.0, lat=34.0),
            GeoFeature(name='襄阳', lng=112.0, lat=32.0),
        ]
        result = make_geojson(features)
        assert len(result['features']) == 2
        names = []
        for feat in result['features']:
            assert feat['geometry']['type'] == 'Point'
            assert len(feat['geometry']['coordinates']) == 2
            names.append(feat['properties']['name'])
        assert set(names) == {'汴京', '襄阳'}
        # 验证坐标值：经纬度顺序 [lng, lat]
        coords_by_name = {
            f['properties']['name']: f['geometry']['coordinates'] for f in result['features']
        }
        assert coords_by_name['汴京'] == [114.0, 34.0]
        assert coords_by_name['襄阳'] == [112.0, 32.0]
