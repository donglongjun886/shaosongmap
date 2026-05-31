"""services/geojson.py 单元测试：GeoJSON 构建。"""

from shaosongmap.models import GeoFeature, RouteLine
from shaosongmap.services.geojson import build_routes, make_geojson


class TestBuildRoutes:
    def test_single_route(self):
        from shaosongmap.models import Route

        routes_places = [Route(from_place='汴京', to_place='襄阳', via=[])]
        features = [
            GeoFeature(name='汴京', lng=114.0, lat=34.0),
            GeoFeature(name='襄阳', lng=112.0, lat=32.0),
        ]
        result = build_routes(routes_places, features)
        assert len(result) == 1
        assert result[0].from_place == '汴京'
        assert result[0].to_place == '襄阳'
        assert len(result[0].coordinates) == 2

    def test_route_with_via(self):
        from shaosongmap.models import Route

        routes_places = [Route(from_place='汴京', to_place='襄阳', via=['许昌'])]
        features = [
            GeoFeature(name='汴京', lng=114.0, lat=34.0),
            GeoFeature(name='许昌', lng=113.5, lat=33.5),
            GeoFeature(name='襄阳', lng=112.0, lat=32.0),
        ]
        result = build_routes(routes_places, features)
        assert len(result) == 1
        assert len(result[0].coordinates) == 3

    def test_missing_coord_drops_route(self):
        from shaosongmap.models import Route

        routes_places = [Route(from_place='汴京', to_place='襄阳', via=[])]
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0)]  # 襄阳无坐标
        result = build_routes(routes_places, features)
        assert len(result) == 0  # 只有起点不够

    def test_empty_routes(self):
        assert build_routes([], []) == []

    def test_feature_with_null_coords_skipped(self):
        from shaosongmap.models import Route

        routes_places = [Route(from_place='汴京', to_place='襄阳', via=[])]
        features = [
            GeoFeature(name='汴京', lng=114.0, lat=34.0),
            GeoFeature(name='襄阳', lng=None, lat=None),
        ]
        result = build_routes(routes_places, features)
        assert len(result) == 0


class TestMakeGeojson:
    def test_basic_feature_collection(self):
        features = [GeoFeature(name='汴京', lng=114.0, lat=34.0, source='chgis')]
        result = make_geojson(features, [])
        assert result['type'] == 'FeatureCollection'
        assert len(result['features']) == 1
        feat = result['features'][0]
        assert feat['type'] == 'Feature'
        assert feat['geometry']['type'] == 'Point'
        assert feat['properties']['name'] == '汴京'

    def test_feature_with_null_coords_excluded(self):
        features = [GeoFeature(name='未知地', lng=None, lat=None)]
        result = make_geojson(features, [])
        assert len(result['features']) == 0

    def test_route_lines_included(self):
        features = [
            GeoFeature(name='汴京', lng=114.0, lat=34.0),
            GeoFeature(name='襄阳', lng=112.0, lat=32.0),
        ]
        routes = [
            RouteLine(
                from_place='汴京', to_place='襄阳', coordinates=[[114.0, 34.0], [112.0, 32.0]]
            )
        ]
        result = make_geojson(features, routes)
        assert len(result['features']) == 3  # 2 points + 1 line

    def test_route_with_single_coord_excluded(self):
        routes = [RouteLine(from_place='汴京', to_place='襄阳', coordinates=[[114.0, 34.0]])]
        result = make_geojson([], routes)
        assert len(result['features']) == 0

    def test_empty_features_and_routes(self):
        result = make_geojson([], [])
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
        result = make_geojson(features, [])
        props = result['features'][0]['properties']
        assert props['name'] == '汴京'
        assert props['source'] == 'llm_infer'
        assert props['modern_name'] == '开封'
        assert props['confidence'] == 'high'
        assert props['place_type'] == 'city'
