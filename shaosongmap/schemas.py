"""ShaosongMap API 请求/响应 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    """提取请求体。"""

    text: str = Field(description='战役文本内容')
    dynasty: str | None = Field(
        default=None,
        description='朝代提示（如「宋」「北宋」「南宋」），用于 CHGIS 时间过滤',
    )


class ExtractResponse(BaseModel):
    """提取响应体。"""

    extract_id: str = Field(description='提取唯一标识')
    event_name: str | None
    dynasty: str | None = Field(default=None, description='朝代')
    boundaries: list[dict]
    person_places: list[dict]
    places: list[dict] = Field(default_factory=list, description='原始地名列表 [{name, context}]')
    features: list[dict]
    geojson: dict = Field(description='GeoJSON FeatureCollection，用于前端地图渲染')
    scale: str | None = Field(default=None, description='地图尺度: tactical/battle/strategic')
    elapsed: dict | None = Field(default=None, description='各阶段耗时(ms)')


class RenderRequest(BaseModel):
    """重新渲染请求体：用户修正后的提取数据。"""

    event_name: str | None = Field(default=None, description='事件/战役名称')
    boundaries: list[dict] = Field(default_factory=list, description='边界/疆域列表')
    places: list[dict] = Field(default_factory=list, description='地名列表 [{name, context}]')
    person_places: list[dict] = Field(
        default_factory=list, description='人物→地点关联 [{person, place, relation}]'
    )
    dynasty: str | None = Field(default=None, description='朝代提示')
    scale: str | None = Field(default=None, description='地图尺度: tactical/battle/strategic')


class ErrorDetail(BaseModel):
    """统一错误体结构。"""

    code: str = Field(description='错误码，大写下划线格式（如 INVALID_INPUT）')
    message: str = Field(description='面向用户的中文简述')
    detail: str = Field(default='', description='技术细节（可选）')


class ErrorResponse(BaseModel):
    """统一错误响应外层。"""

    error: ErrorDetail
