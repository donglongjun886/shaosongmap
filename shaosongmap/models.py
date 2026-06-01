"""Pydantic 数据模型：Extractor → Geocoder → API 的数据契约。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Place(BaseModel):
    """文本中出现的地名。"""

    name: str = Field(description='古地名，如「汴京」「襄阳」')
    context: str = Field(default='', description='原文字段，供消歧义使用')
    lng: float | None = Field(default=None, description='经度（编辑面板传回）')
    lat: float | None = Field(default=None, description='纬度（编辑面板传回）')
    source: str | None = Field(default=None, description='数据来源：chgis / llm_infer / unknown')
    modern_name: str | None = Field(default=None, description='现代地名')
    confidence: str | None = Field(default=None, description='LLM 推断可信度：high / medium / low')


class Boundary(BaseModel):
    """边界/疆域描述。"""

    name: str = Field(description='边界名称，如「宋金边界」')
    description: str = Field(default='', description='边界描述，如「西起秦岭，东至淮河」')


class PersonPlace(BaseModel):
    """人物与地点的关联。"""

    person: str = Field(description='人物名，如「岳飞」')
    place: str = Field(description='关联地名，如「襄阳」')
    relation: str = Field(default='', description='关系类型，如「驻扎」「出生」「战死」')


class GeoEntityExtract(BaseModel):
    """Extractor 输出：从历史文本提取的地理实体数据。"""

    event_name: str | None = Field(default=None, description='事件/战役名称')
    dynasty: str | None = Field(default=None, description='朝代，如「南宋」「北宋」')
    boundaries: list[Boundary] = Field(default_factory=list, description='边界/疆域')
    person_places: list[PersonPlace] = Field(default_factory=list, description='人物→地点关联')
    places: list[Place] = Field(default_factory=list, description='地名列表')
    scale: Literal['tactical', 'battle', 'strategic'] | None = Field(
        default=None, description='地图尺度: tactical/battle/strategic'
    )


class GeoFeature(BaseModel):
    """单个地名的地理坐标特征。"""

    name: str = Field(description='地名')
    lng: float | None = Field(default=None, description='经度', ge=-180, le=180)
    lat: float | None = Field(default=None, description='纬度', ge=-90, le=90)
    source: Literal['chgis', 'llm_infer', 'unknown'] = Field(
        default='unknown',
        description='数据来源：chgis / llm_infer / unknown',
    )
    modern_name: str | None = Field(default=None, description='现代地名')
    confidence: Literal['high', 'medium', 'low'] | None = Field(
        default=None, description='LLM 推断时的可信度：high / medium / low'
    )
    place_type: Literal['city', 'mountain', 'river', 'pass', 'region', 'unknown'] | None = Field(
        default=None,
        description='地名类型',
    )


class GeoEntityMap(BaseModel):
    """API 最终输出：地理实体数据 + 地图要素。"""

    extract: GeoEntityExtract = Field(description='原始提取结果')
    features: list[GeoFeature] = Field(description='地名坐标特征列表')
