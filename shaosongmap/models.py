"""Pydantic 数据模型：Extractor → Geocoder → API 的数据契约。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Faction(BaseModel):
    """参战一方。"""

    name: str = Field(description="阵营名称，如「宋军」「金军」")
    commanders: list[str] = Field(default_factory=list, description="将领列表")
    troops: Optional[str] = Field(default=None, description="兵力描述，如「三万」「十万」")


class Place(BaseModel):
    """文本中出现的地名。"""

    name: str = Field(description="古地名，如「汴京」「襄阳」")
    context: str = Field(default="", description="原文字段，供消歧义使用")


class Route(BaseModel):
    """行军路线段。"""

    model_config = {"populate_by_name": True}

    from_place: str = Field(alias="from", description="起点地名")
    to_place: str = Field(alias="to", description="终点地名")
    via: list[str] = Field(default_factory=list, description="途经地点")


class CampaignExtract(BaseModel):
    """Extractor 输出：从战役文本提取的结构化数据。"""

    campaign_name: Optional[str] = Field(default=None, description="战役名称")
    factions: list[Faction] = Field(default_factory=list, description="参战方")
    places: list[Place] = Field(default_factory=list, description="地名列表")
    routes: list[Route] = Field(default_factory=list, description="行军路线")


class GeoFeature(BaseModel):
    """单个地名的地理坐标特征。"""

    name: str = Field(description="地名")
    lng: Optional[float] = Field(default=None, description="经度")
    lat: Optional[float] = Field(default=None, description="纬度")
    source: str = Field(
        default="unknown",
        description="数据来源：chgis / llm_infer / unknown",
    )
    modern_name: Optional[str] = Field(default=None, description="现代地名")
    confidence: Optional[str] = Field(
        default=None, description="LLM 推断时的可信度：high / medium / low"
    )


class RouteLine(BaseModel):
    """行军路线的 GeoJSON LineString 片段。"""

    from_place: str
    to_place: str
    coordinates: list[list[float]] = Field(
        description="GeoJSON 坐标数组 [[lng, lat], [lng, lat]]"
    )


class CampaignMap(BaseModel):
    """API 最终输出：战役数据 + 地图要素。"""

    extract: CampaignExtract = Field(description="原始提取结果")
    features: list[GeoFeature] = Field(description="地名坐标特征列表")
    routes: list[RouteLine] = Field(description="行军路线 GeoJSON 坐标")
