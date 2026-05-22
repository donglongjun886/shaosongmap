"""Pydantic 数据模型：Extractor → Geocoder → API 的数据契约。"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Faction(BaseModel):
    """参战一方。"""

    name: str = Field(description="阵营名称，如「宋军」「金军」")
    commanders: list[str] = Field(default_factory=list, description="将领列表")
    troops: Optional[str] = Field(default=None, description="兵力描述，如「三万」「十万」")


PlaceType = Literal["city", "mountain_pass", "river", "mountain", "region", "battlefield"]

MilitaryScale = Literal["tactical", "battle", "strategic"]

UnitStatus = Literal["deploying", "marching", "engaging", "retreating", "routing"]
"""部队状态：待命/列阵 → 进军/机动 → 交战/接敌 → 撤退 → 溃散"""

TroopType = Literal["infantry", "cavalry", "mixed"]
"""兵种类型：步兵 / 骑兵 / 混合"""


class Place(BaseModel):
    """文本中出现的地名。"""

    name: str = Field(description="古地名，如「汴京」「襄阳」")
    context: str = Field(default="", description="原文字段，供消歧义使用")
    place_type: Optional[PlaceType] = Field(
        default=None,
        description="地名类型：city(城池) / mountain_pass(关隘) / river(河流) / mountain(山脉) / region(行政区) / battlefield(战场)",
    )


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
    scale: Optional[MilitaryScale] = Field(
        default=None,
        description="军事行动规模：tactical(战术级,1-10km) / battle(战役级,20-200km) / strategic(战略级,200-1000km)",
    )


# ── 时间线事件类型 ──

TimelineEventType = Literal["march", "battle", "encamp", "retreat"]


class TimelineEvent(BaseModel):
    """时间线中的单个事件节点。"""

    seq: int = Field(ge=1, description="事件序号，从 1 开始")
    event_type: TimelineEventType = Field(description="事件类型：march / battle / encamp / retreat")
    description: str = Field(description="一句话中文描述，概括原文内容")
    actors: list[str] = Field(default_factory=list, description="参与的将领或部队名称")
    places_involved: list[str] = Field(default_factory=list, description="事件涉及的地名，须为 places 中的已有地名")


class ForceUnit(BaseModel):
    """从战役文本中识别出的独立军事部队实体。"""

    name: str = Field(description="部队名称，如「焦文通部」「合扎猛安」，在提取结果中保持唯一")
    faction: str = Field(description="所属阵营名称，对应 factions 中的某个阵营")
    commander: str = Field(default="", description="指挥官姓名")
    troop_type: TroopType = Field(default="mixed", description="兵种类型：infantry(步兵) / cavalry(骑兵) / mixed(混合)")
    troop_count: str = Field(default="", description="兵力描述原文，如「数千」「满员一千骑」")
    direction: Optional[str] = Field(
        default=None,
        description="进攻方向，以方位词表达（东/南/西/北/东南/西南/东北/西北），无明确方向时为 null",
    )


class UnitState(BaseModel):
    """部队在某个时间线步骤中的状态快照。"""

    seq: int = Field(ge=1, description="对应的时间线步骤序号")
    unit_name: str = Field(description="部队名称，对应 units 中某个 ForceUnit 的 name")
    status: UnitStatus = Field(description="部队当前状态")
    location: Optional[str] = Field(
        default=None,
        description="部队当前位置关联的地名，为 places 中的地名；无法关联时为 null",
    )
    direction: Optional[str] = Field(
        default=None,
        description="当前步骤的进攻方向，覆盖 ForceUnit 的默认方向",
    )
    description: str = Field(default="", description="一句话中文描述，概括该部队在此步骤的战术动作")


class CampaignTimeline(CampaignExtract):
    """时间线模式输出：继承战役提取结果，附加事件序列、部队和部队状态。"""

    events: list[TimelineEvent] = Field(default_factory=list, description="按时间顺序排列的事件序列")
    units: list[ForceUnit] = Field(default_factory=list, description="识别出的部队实体列表")
    unit_states: list[UnitState] = Field(default_factory=list, description="各部队在各步骤中的状态快照")


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
