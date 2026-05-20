"""ShaosongMap FastAPI 应用入口。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from shaosongmap.extractor import extract
from shaosongmap.geocoder import geocode
from shaosongmap.models import CampaignMap, GeoFeature, RouteLine
from shaosongmap.ocr import ocr_main

app = FastAPI(
    title="ShaosongMap",
    description="让历史小说读者「边读边看地图」——输入战役段落，生成古代地图",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExtractRequest(BaseModel):
    """提取请求体。"""

    text: str = Field(description="战役文本内容")
    dynasty: str | None = Field(
        default=None,
        description="朝代提示（如「宋」「北宋」「南宋」），用于 CHGIS 时间过滤",
    )


class ExtractResponse(BaseModel):
    """提取响应体。"""

    extract_id: str = Field(description="提取唯一标识")
    campaign_name: str | None
    factions: list[dict]
    features: list[dict]
    routes: list[dict]
    geojson: dict = Field(description="GeoJSON FeatureCollection，用于前端地图渲染")


class OcrResponse(BaseModel):
    """OCR 响应体。"""

    text: str = Field(description="清洗后的连续文本段落")
    raw_lines: int = Field(description="OCR 原始识别行数")


_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg"}
_MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


@app.post("/api/ocr", response_model=OcrResponse)
async def ocr_image(file: UploadFile = File(...)):
    """接收截图上传，OCR 识别后返回清洗文本。

    支持 PNG 和 JPEG 格式，最大 10MB。
    返回的文本可直接用于 /api/extract。
    """
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="仅支持 PNG 和 JPEG 格式",
        )

    image_bytes = await file.read()
    if len(image_bytes) > _MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"图片大小不能超过 {_MAX_IMAGE_SIZE // 1024 // 1024}MB",
        )

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="图片不能为空")

    try:
        text, raw_lines = ocr_main(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return OcrResponse(text=text, raw_lines=raw_lines)


# 朝代时间范围映射
_DYNASTY_YEARS: dict[str, tuple[int, int]] = {
    "北宋": (960, 1127),
    "南宋": (1127, 1279),
    "宋": (960, 1279),
    "唐": (618, 907),
    "明": (1368, 1644),
    "清": (1644, 1911),
}


def _make_geojson(features: list[GeoFeature], routes: list[RouteLine]) -> dict:
    """将 GeoFeature 和 RouteLine 列表转换为 GeoJSON FeatureCollection。"""
    geojson_features = []

    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            geojson_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [feat.lng, feat.lat],
                },
                "properties": {
                    "name": feat.name,
                    "source": feat.source,
                    "modern_name": feat.modern_name,
                    "confidence": feat.confidence,
                },
            })

    for route in routes:
        if len(route.coordinates) >= 2:
            geojson_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": route.coordinates,
                },
                "properties": {
                    "type": "route",
                    "from": route.from_place,
                    "to": route.to_place,
                },
            })

    return {
        "type": "FeatureCollection",
        "features": geojson_features,
    }


def _build_routes(
    campaign,
    features: list[GeoFeature],
) -> list[RouteLine]:
    """根据提取的行军路线和地标坐标构建 GeoJSON 路线线段。

    将相邻路标坐标两两连接，形成行军路线折线。
    """
    # 建立地名 → 坐标映射
    coord_map: dict[str, list[float]] = {}
    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            coord_map[feat.name] = [feat.lng, feat.lat]

    route_lines: list[RouteLine] = []
    for route in campaign.routes:
        coords = []
        start_coord = coord_map.get(route.from_place)
        if start_coord:
            coords.append(start_coord)

        for via_place in route.via:
            via_coord = coord_map.get(via_place)
            if via_coord:
                coords.append(via_coord)

        end_coord = coord_map.get(route.to_place)
        if end_coord:
            coords.append(end_coord)

        if len(coords) >= 2:
            route_lines.append(RouteLine(
                from_place=route.from_place,
                to_place=route.to_place,
                coordinates=coords,
            ))

    return route_lines


@app.post("/api/extract", response_model=ExtractResponse)
async def extract_campaign(request: ExtractRequest):
    """从战役文本中提取结构化数据并返回地图要素。

    核心链路：Extractor → Geocoder → GeoJSON。
    """
    import uuid

    # 1. 提取
    try:
        campaign = extract(request.text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # 2. 地名坐标匹配
    dyn_beg = None
    dyn_end = None
    if request.dynasty and request.dynasty in _DYNASTY_YEARS:
        dyn_beg, dyn_end = _DYNASTY_YEARS[request.dynasty]

    features = geocode(
        campaign.places,
        context_text=request.text,
        dynasty_beg_yr=dyn_beg,
        dynasty_end_yr=dyn_end,
    )

    # 3. 构建行军路线坐标
    route_lines = _build_routes(campaign, features)

    # 4. 构建 GeoJSON
    geojson = _make_geojson(features, route_lines)

    return ExtractResponse(
        extract_id=uuid.uuid4().hex[:12],
        campaign_name=campaign.campaign_name,
        factions=[f.model_dump(by_alias=True) for f in campaign.factions],
        features=[f.model_dump() for f in features],
        routes=[r.model_dump() for r in route_lines],
        geojson=geojson,
    )


# 挂载静态文件（必须在所有路由之后）
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")