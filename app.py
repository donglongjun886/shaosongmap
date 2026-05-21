"""ShaosongMap FastAPI 应用入口。"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from shaosongmap.extractor import extract, extract_timeline
from shaosongmap.geocoder import geocode
from shaosongmap.models import CampaignExtract, CampaignMap, CampaignTimeline, GeoFeature, RouteLine, TimelineEvent
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
    mode: str | None = Field(
        default=None,
        description="提取模式：timeline（返回事件序列）或 static（默认，仅静态结构）",
    )


class ExtractResponse(BaseModel):
    """提取响应体（非 SSE 模式下使用）。"""

    extract_id: str = Field(description="提取唯一标识")
    campaign_name: str | None
    factions: list[dict]
    features: list[dict]
    routes: list[dict]
    geojson: dict = Field(description="GeoJSON FeatureCollection，用于前端地图渲染")


class RenderRequest(BaseModel):
    """重新渲染请求体：用户修正后的提取数据。"""

    campaign_name: str | None = Field(default=None, description="战役名称")
    factions: list[dict] = Field(default_factory=list, description="阵营列表")
    places: list[dict] = Field(default_factory=list, description="地名列表 [{name, context}]")
    routes: list[dict] = Field(default_factory=list, description="行军路线 [{from, to, via}]")
    dynasty: str | None = Field(default=None, description="朝代提示")


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


def _compute_step_map(events: list[TimelineEvent]) -> dict[str, int]:
    """从事件序列计算每个地名首次被激活的步骤编号。"""
    step_map: dict[str, int] = {}
    for event in events:
        for place_name in event.places_involved:
            if place_name not in step_map:
                step_map[place_name] = event.seq
    return step_map


def _make_geojson(
    features: list[GeoFeature],
    routes: list[RouteLine],
    events: list[TimelineEvent] | None = None,
) -> dict:
    """将 GeoFeature 和 RouteLine 列表转换为 GeoJSON FeatureCollection。

    timeline 模式下（提供 events 参数），每个 feature 的 properties
    中注入 step 属性，供前端按步骤过滤渲染。
    """
    step_map: dict[str, int] | None = None
    if events:
        step_map = _compute_step_map(events)

    geojson_features = []

    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            props: dict = {
                "name": feat.name,
                "source": feat.source,
                "modern_name": feat.modern_name,
                "confidence": feat.confidence,
            }
            if step_map is not None:
                props["step"] = step_map.get(feat.name, 0)
            geojson_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [feat.lng, feat.lat],
                },
                "properties": props,
            })

    for route in routes:
        if len(route.coordinates) >= 2:
            props: dict = {
                "type": "route",
                "from": route.from_place,
                "to": route.to_place,
            }
            if step_map is not None:
                to_step = step_map.get(route.to_place)
                from_step = step_map.get(route.from_place)
                if to_step is not None:
                    props["step"] = to_step
                elif from_step is not None:
                    props["step"] = from_step
                else:
                    props["step"] = 1
            geojson_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": route.coordinates,
                },
                "properties": props,
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


def _sse_event(event: str, data: dict) -> str:
    """构建一条 SSE 格式的事件字符串。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _run_pipeline(text: str, dynasty: str | None) -> dict:
    """执行管道并返回提取结果字典。"""
    campaign = extract(text)
    dyn_beg, dyn_end = None, None
    if dynasty and dynasty in _DYNASTY_YEARS:
        dyn_beg, dyn_end = _DYNASTY_YEARS[dynasty]

    features = geocode(
        campaign.places,
        context_text=text,
        dynasty_beg_yr=dyn_beg,
        dynasty_end_yr=dyn_end,
    )
    route_lines = _build_routes(campaign, features)
    geojson = _make_geojson(features, route_lines)

    return {
        "extract_id": uuid.uuid4().hex[:12],
        "campaign_name": campaign.campaign_name,
        "factions": [f.model_dump(by_alias=True) for f in campaign.factions],
        "features": [f.model_dump() for f in features],
        "routes": [r.model_dump() for r in route_lines],
        "geojson": geojson,
    }


@app.post("/api/extract")
async def extract_campaign(request: ExtractRequest):
    """从战役文本中提取结构化数据并返回地图要素（SSE 流式）。

    通过 Server-Sent Events 推送管道各阶段进度，
    最终以 result 事件返回完整数据。
    """
    # 前置校验：空文本直接返回 422，不启动 SSE 流
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="战役文本不能为空")

    async def event_stream():
        # Stage 1: Extract
        use_timeline = request.mode == "timeline"
        try:
            if use_timeline:
                campaign = extract_timeline(request.text)
            else:
                campaign = extract(request.text)
        except ValueError as e:
            yield _sse_event("error", {"stage": "extract", "message": str(e)})
            return

        places_count = len(campaign.places)
        routes_count = len(campaign.routes)
        events_count = len(getattr(campaign, "events", []))
        extract_detail = f"提取结构数据 ({places_count}地名, {routes_count}路线"
        if use_timeline:
            extract_detail += f", {events_count}事件"
        extract_detail += ")"
        yield _sse_event("progress", {
            "stage": "extract_done",
            "detail": extract_detail,
            "ok": True,
        })

        # Stage 2: Geocode
        dyn_beg, dyn_end = None, None
        if request.dynasty and request.dynasty in _DYNASTY_YEARS:
            dyn_beg, dyn_end = _DYNASTY_YEARS[request.dynasty]

        try:
            features = geocode(
                campaign.places,
                context_text=request.text,
                dynasty_beg_yr=dyn_beg,
                dynasty_end_yr=dyn_end,
            )
        except Exception as e:
            yield _sse_event("error", {"stage": "geocode", "message": str(e)})
            return

        chgis_count = sum(1 for f in features if f.source == "chgis")
        llm_count = sum(1 for f in features if f.source == "llm_infer")
        yield _sse_event("progress", {
            "stage": "geocode_done",
            "detail": f"匹配古地名 ({chgis_count} CHGIS + {llm_count} LLM推断)",
            "ok": True,
        })

        # Stage 3: Build routes & GeoJSON
        route_lines = _build_routes(campaign, features)
        timeline_events = getattr(campaign, "events", []) if use_timeline else None
        geojson = _make_geojson(features, route_lines, events=timeline_events)

        render_detail = f"渲染地图 ({len(features)}标记, {len(route_lines)}路线)"
        if use_timeline and timeline_events:
            render_detail += f", {len(timeline_events)}步骤"
        yield _sse_event("progress", {
            "stage": "render_done",
            "detail": render_detail,
            "ok": True,
        })

        # Final result
        result: dict = {
            "extract_id": uuid.uuid4().hex[:12],
            "campaign_name": campaign.campaign_name,
            "factions": [f.model_dump(by_alias=True) for f in campaign.factions],
            "features": [f.model_dump() for f in features],
            "routes": [r.model_dump() for r in route_lines],
            "geojson": geojson,
        }
        if use_timeline and timeline_events:
            result["events"] = [e.model_dump() for e in timeline_events]
            result["total_steps"] = len(timeline_events)
        yield _sse_event("result", result)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/render", response_model=ExtractResponse)
async def render_modified(request: RenderRequest):
    """接收用户修正后的提取数据，跳过 LLM 提取，直接 geocode + GeoJSON。

    用于前端可编辑面板的「重新渲染」功能。
    """
    from shaosongmap.models import Faction, Place, Route

    # 重建 Pydantic 模型
    try:
        factions = [Faction(**f) for f in request.factions]
        places = [Place(**p) for p in request.places]
        routes = [Route(**r) for r in request.routes]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"数据格式错误: {e}") from e

    campaign = CampaignExtract(
        campaign_name=request.campaign_name,
        factions=factions,
        places=places,
        routes=routes,
    )

    # Geocode
    dyn_beg, dyn_end = None, None
    if request.dynasty and request.dynasty in _DYNASTY_YEARS:
        dyn_beg, dyn_end = _DYNASTY_YEARS[request.dynasty]

    try:
        features = geocode(
            campaign.places,
            context_text="",
            dynasty_beg_yr=dyn_beg,
            dynasty_end_yr=dyn_end,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"地名匹配失败: {e}") from e

    route_lines = _build_routes(campaign, features)
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