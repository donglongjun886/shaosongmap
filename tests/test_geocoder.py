"""Geocoder 模块单元测试。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from shaosongmap.geocoder import (
    _fuzzy_match,
    geocode,
    infer_with_llm,
    match_chgis,
)
from shaosongmap.models import GeoFeature, Place


class TestFuzzyMatch:
    def test_exact_match(self):
        assert _fuzzy_match("汴京", "汴京") == 1.0

    def test_partial_match(self):
        assert _fuzzy_match("汴梁", "汴京") > 0.4

    def test_no_match(self):
        assert _fuzzy_match("汴京", "长安") < 0.3


class TestMatchChgis:
    def test_exact_match(self):
        result = match_chgis("汴京")
        assert result is not None
        assert result.name == "汴京"
        assert result.source == "chgis"
        assert result.lng == pytest.approx(114.35, rel=0.01)
        assert result.lat == pytest.approx(34.80, rel=0.01)

    def test_dynasty_filter(self):
        """北宋「东京」应匹配到对应记录。"""
        result = match_chgis("东京", dynasty_beg_yr=960, dynasty_end_yr=1127)
        assert result is not None
        assert result.name == "东京"

    def test_fictional_place_returns_none(self):
        assert match_chgis("鹰愁涧") is None

    def test_approximate_match_with_low_threshold(self):
        result = match_chgis("汴梁", threshold=0.5)
        assert result is not None
        assert result.source == "chgis"


class TestInferWithLlm:
    @patch("shaosongmap.geocoder.OpenAI")
    def test_llm_infer_success(self, mock_openai: MagicMock):
        choice = MagicMock()
        choice.message.content = json.dumps([
            {"name": "鹰愁涧", "lng": 112.5, "lat": 32.3, "confidence": "low"}
        ])
        mock_openai.return_value.chat.completions.create.return_value = MagicMock(choices=[choice])

        results = infer_with_llm(["鹰愁涧"], "途经鹰愁涧向襄阳")
        assert len(results) == 1
        assert results[0].name == "鹰愁涧"
        assert results[0].source == "llm_infer"
        assert results[0].confidence == "low"

    @patch("shaosongmap.geocoder.OpenAI")
    def test_llm_empty_response(self, mock_openai: MagicMock):
        choice = MagicMock()
        choice.message.content = None
        mock_openai.return_value.chat.completions.create.return_value = MagicMock(choices=[choice])

        results = infer_with_llm(["未知山"], "无上下文")
        assert len(results) == 1
        assert results[0].source == "unknown"

    def test_empty_input(self):
        assert infer_with_llm([], "text") == []


class TestGeocode:
    def test_mixed_sources(self):
        """CHGIS 命中 + 未命中混排。"""
        places = [
            Place(name="汴京", context=""),
            Place(name="鹰愁涧", context=""),
        ]
        with patch(
            "shaosongmap.geocoder.infer_with_llm",
            return_value=[GeoFeature(name="鹰愁涧", source="unknown")],
        ):
            results = geocode(places)
            assert len(results) == 2
            sources = {r.name: r.source for r in results}
            assert sources["汴京"] == "chgis"
            assert sources["鹰愁涧"] == "unknown"

    def test_all_chgis(self):
        """全部命中 CHGIS。"""
        results = geocode([
            Place(name="汴京", context=""),
            Place(name="襄阳", context=""),
        ])
        assert len(results) == 2
        assert all(r.source == "chgis" for r in results)
