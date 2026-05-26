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
    mode: str | None = Field(
        default=None,
        description='提取模式：timeline（返回事件序列）或 static（默认，仅静态结构）',
    )


class ExtractResponse(BaseModel):
    """提取响应体（非 SSE 模式下使用）。"""

    extract_id: str = Field(description='提取唯一标识')
    campaign_name: str | None
    factions: list[dict]
    features: list[dict]
    routes: list[dict]
    geojson: dict = Field(description='GeoJSON FeatureCollection，用于前端地图渲染')
    scale: str | None = Field(
        default=None, description='军事行动规模：tactical / battle / strategic'
    )


class RenderRequest(BaseModel):
    """重新渲染请求体：用户修正后的提取数据。"""

    campaign_name: str | None = Field(default=None, description='战役名称')
    factions: list[dict] = Field(default_factory=list, description='阵营列表')
    places: list[dict] = Field(default_factory=list, description='地名列表 [{name, context}]')
    routes: list[dict] = Field(default_factory=list, description='行军路线 [{from, to, via}]')
    dynasty: str | None = Field(default=None, description='朝代提示')
    scale: str | None = Field(default=None, description='军事行动规模')


class OcrResponse(BaseModel):
    """OCR 响应体。"""

    text: str = Field(description='清洗后的连续文本段落')
    raw_lines: int = Field(description='OCR 原始识别行数')
    elapsed_ms: float = Field(description='OCR 耗时（毫秒）')
