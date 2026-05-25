"""ShaosongMap FastAPI 应用入口。"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from shaosongmap.extractor import extract, extract_timeline
from shaosongmap.geocoder import geocode
from shaosongmap.models import CampaignExtract, CampaignMap, CampaignTimeline, ForceUnit, GeoFeature, RouteLine, TimelineEvent, UnitState
from shaosongmap.ocr import _get_ocr, merge_texts, ocr_main

logger = logging.getLogger("shaosongmap")


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """应用生命周期：启动时预加载 PaddleOCR 模型。"""
    logger.info("正在预加载 PaddleOCR 模型...")
    _get_ocr()
    logger.info("PaddleOCR 模型预热完成")
    yield


app = FastAPI(
    title="ShaosongMap",
    description="让历史小说读者「边读边看地图」——输入战役段落，生成古代地图",
    version="0.1.0",
    lifespan=_lifespan,
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
    scale: str | None = Field(default=None, description="军事行动规模：tactical / battle / strategic")


class RenderRequest(BaseModel):
    """重新渲染请求体：用户修正后的提取数据。"""

    campaign_name: str | None = Field(default=None, description="战役名称")
    factions: list[dict] = Field(default_factory=list, description="阵营列表")
    places: list[dict] = Field(default_factory=list, description="地名列表 [{name, context}]")
    routes: list[dict] = Field(default_factory=list, description="行军路线 [{from, to, via}]")
    dynasty: str | None = Field(default=None, description="朝代提示")
    scale: str | None = Field(default=None, description="军事行动规模")


class OcrResponse(BaseModel):
    """OCR 响应体。"""

    text: str = Field(description="清洗后的连续文本段落")
    raw_lines: int = Field(description="OCR 原始识别行数")
    elapsed_ms: float = Field(description="OCR 耗时（毫秒）")


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
        t0 = time.perf_counter()
        text, raw_lines = ocr_main(image_bytes)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info("OCR完成: %d行 → %d字符, 耗时 %.0fms", raw_lines, len(text), elapsed)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return OcrResponse(text=text, raw_lines=raw_lines, elapsed_ms=round(elapsed))


_MAX_BATCH_SIZE = 10


@app.post("/api/ocr/batch")
async def ocr_batch(files: list[UploadFile] = File(...)):
    """批量截图 OCR：接收多张截图，依次识别后去重拼接。

    通过 SSE 流式返回每张图的处理进度，最终返回拼接后的完整文本。
    最多支持 10 张截图，单张失败则整体中止并指明失败序号。
    """
    if len(files) > _MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"每次最多上传 {_MAX_BATCH_SIZE} 张截图",
        )
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="请至少上传一张截图")

    # 先读取所有文件内容，避免 StreamingResponse 中文件被提前关闭
    file_data: list[tuple[str, bytes]] = []
    for i, file in enumerate(files):
        label = f"第 {i + 1} 张"
        if file.content_type not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"{label}截图格式不支持，仅支持 PNG 和 JPEG 格式",
            )
        image_bytes = await file.read()
        if len(image_bytes) > _MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"{label}截图大小超过 {_MAX_IMAGE_SIZE // 1024 // 1024}MB 限制",
            )
        if len(image_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"{label}截图不能为空",
            )
        file_data.append((label, image_bytes))

    async def event_stream():
        texts: list[str] = []
        total = len(file_data)
        t_pipeline_start = time.perf_counter()

        for label, img_bytes in file_data:
            t0 = time.perf_counter()
            try:
                text, _raw_lines = ocr_main(img_bytes)
            except ValueError as e:
                yield _sse_event("error", {
                    "message": f"{label}截图识别失败: {e}",
                })
                return

            elapsed = (time.perf_counter() - t0) * 1000
            logger.info("批量OCR %s: %d字符, 耗时 %.0fms", label, len(text), elapsed)
            texts.append(text)
            yield _sse_event("progress", {
                "current": len(texts),
                "total": total,
                "char_count": len(text),
                "elapsed_ms": round(elapsed),
            })

        # 去重拼接
        original_chars = sum(len(t) for t in texts)
        t_merge_start = time.perf_counter()
        merged_text, removed_dup = merge_texts(texts)
        merge_elapsed = (time.perf_counter() - t_merge_start) * 1000
        logger.info("批量OCR 去重拼接: %d字符 → %d字符 (去重%d), 耗时 %.0fms",
                     original_chars, len(merged_text), removed_dup, merge_elapsed)
        yield _sse_event("merge", {
            "original_chars": original_chars,
            "merged_chars": len(merged_text),
            "removed_dup": removed_dup,
            "elapsed_ms": round(merge_elapsed),
        })

        total_elapsed = (time.perf_counter() - t_pipeline_start) * 1000
        logger.info("批量OCR 全部完成: %d张截图 → %d字符, 总耗时 %.0fms",
                     total, len(merged_text), total_elapsed)
        yield _sse_event("complete", {"text": merged_text, "total_elapsed_ms": round(total_elapsed)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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


# 进攻方位 → 角度（正东=0°，逆时针）
_DIRECTION_ANGLE: dict[str, float] = {
    "东": 0, "南": 270, "西": 180, "北": 90,
    "东南": 315, "西南": 225, "东北": 45, "西北": 135,
}


def _angle_for_direction(direction: str | None) -> float:
    """将方位词转换为角度，默认 0°（正东）。"""
    if direction and direction in _DIRECTION_ANGLE:
        return _DIRECTION_ANGLE[direction]
    return 0.0


def _compute_data_diagonal(place_coords: list[tuple[float, float]]) -> float:
    """计算数据包围盒对角线长度（米），用于自适应箭头尺寸。"""
    import math
    if not place_coords or len(place_coords) < 2:
        return 100.0  # 单点默认100m
    lngs = [c[0] for c in place_coords]
    lats = [c[1] for c in place_coords]
    min_lng, max_lng = min(lngs), max(lngs)
    min_lat, max_lat = min(lats), max(lats)
    mid_lat = math.radians((min_lat + max_lat) / 2)
    dx = (max_lng - min_lng) * 111320.0 * math.cos(mid_lat)
    dy = (max_lat - min_lat) * 111320.0
    return math.sqrt(dx * dx + dy * dy)


def _offset_point(
    lng: float, lat: float, angle_deg: float, distance_m: float,
) -> list[float]:
    """从给定点沿给定角度偏移指定距离（米），返回 [lng, lat]."""
    import math
    lat_rad = math.radians(lat)
    angle_rad = math.radians(angle_deg)
    d_lng = distance_m * math.cos(angle_rad) / (111320.0 * math.cos(lat_rad))
    d_lat = distance_m * math.sin(angle_rad) / 111320.0
    return [lng + d_lng, lat + d_lat]


def _make_unit_banner_features(
    lng: float,
    lat: float,
    angle_deg: float | None,
    direction_name: str | None,
    direction_len_m: float,
    unit_name: str,
    faction: str,
    status: str,
    seq: int,
    description: str,
    scale: str | None,
) -> list[dict]:
    """为部队生成汉代《驻军图》风格旗帜标记 GeoJSON 特征。

    返回 list，包含：
    - Point 特征：旗帜位置（渲染为双线矩形框图标）
    - LineString 特征（如有方向）：方向指示线
    """

    banner_props = {
        "_feature_type": "unit_banner",
        "unit_name": unit_name,
        "faction": faction,
        "status": status,
        "step": seq,
        "description": description,
        "direction": direction_name,
        "scale": scale,
    }

    features: list[dict] = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": banner_props,
    }]

    if angle_deg is not None:
        end = _offset_point(lng, lat, angle_deg, direction_len_m)
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[lng, lat], end]},
            "properties": {
                "_feature_type": "unit_direction",
                "unit_name": unit_name,
                "faction": faction,
                "status": status,
                "step": seq,
            },
        })

    return features


def _compute_unit_offsets(
    unit_states: list[UnitState],
    units: list[ForceUnit],
    features: list[GeoFeature],
    scale: str | None,
) -> dict[str, list[float]]:
    """计算同名地多部队的平行错位偏移。

    同一地点有多个部队时，统一沿南北方向做平行错位展开，
    避免各部队方向角不同导致偏移方向不一致而重叠。

    Returns:
        映射: unit_name → [offset_lng, offset_lat]
    """
    import math

    # 建立地名→坐标映射
    coord_map: dict[str, list[float]] = {}
    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            coord_map[feat.name] = [feat.lng, feat.lat]

    # 统计每个坐标点有多少部队（按实际坐标分组，而非地名）
    coord_units: dict[tuple[float, float], list[str]] = {}
    for us in unit_states:
        if us.location and us.location in coord_map:
            coord = tuple(coord_map[us.location])
            if coord not in coord_units:
                coord_units[coord] = []
            if us.unit_name not in coord_units[coord]:
                coord_units[coord].append(us.unit_name)

    # 旗帜间距估算
    scale_ratio_w = {"tactical": 0.10, "battle": 0.08, "strategic": 0.03}
    ratio_w = scale_ratio_w.get(scale, 0.08)
    lngs = [c[0] for c in coord_map.values() if c[0] is not None]
    lats = [c[1] for c in coord_map.values() if c[1] is not None]
    if len(lngs) >= 2:
        import math as _m
        mid_lat = _m.radians((min(lats) + max(lats)) / 2)
        dx = (max(lngs) - min(lngs)) * 111320.0 * _m.cos(mid_lat)
        dy = (max(lats) - min(lats)) * 111320.0
        diag = _m.sqrt(dx*dx + dy*dy)
    else:
        diag = 100.0
    body_width_est = max(diag * ratio_w / 3.5, 22.0)
    arrow_spacing_m = body_width_est * 1.2

    offsets: dict[str, list[float]] = {}
    for coord, unit_names in coord_units.items():
        if len(unit_names) <= 1:
            continue
        base = list(coord)
        deg_per_m_lat = 1.0 / 111320.0

        for i, uname in enumerate(unit_names):
            # 统一沿南北方向错位展开，以中心为基准向两侧分布
            offset_idx = (i - (len(unit_names) - 1) / 2) * 1.2
            offset_m = offset_idx * arrow_spacing_m
            offsets[uname] = [0.0, offset_m * deg_per_m_lat]

    return offsets


def _make_unit_geojson(
    units: list[ForceUnit],
    unit_states: list[UnitState],
    features: list[GeoFeature],
    scale: str | None,
) -> list[dict]:
    """为部队生成汉代《驻军图》风格旗帜标记 GeoJSON 特征列表。

    每个步骤只渲染每个部队的「最新状态」（seq <= 当前步骤的最新 unit_state），
    避免同一部队在多个历史位置同时显示。
    """
    from collections import defaultdict

    # 建立地名→坐标映射
    coord_map: dict[str, list[float]] = {}
    for feat in features:
        if feat.lng is not None and feat.lat is not None:
            coord_map[feat.name] = [feat.lng, feat.lat]

    # 计算同地多部队偏移（基于所有状态一次算出，偏移量不随步骤变化）
    offsets = _compute_unit_offsets(unit_states, units, features, scale)

    # 计算数据范围对角线，用于自适应方向线长度
    place_coords = [
        (feat.lng, feat.lat)
        for feat in features if feat.lng is not None and feat.lat is not None
    ]
    diagonal_m = _compute_data_diagonal(place_coords)
    scale_ratio = {"tactical": 0.10, "battle": 0.08, "strategic": 0.03}
    ratio = scale_ratio.get(scale, 0.08)
    direction_len_m = diagonal_m * ratio
    direction_len_m = max(direction_len_m, 500.0)   # 最小500m
    direction_len_m = min(direction_len_m, 20000.0)  # 最大20km

    # 建立部队名→部队对象映射
    unit_map: dict[str, ForceUnit] = {u.name: u for u in units}

    # 按 seq 分组 unit_states，同时记录所有步骤号
    seq_states: dict[int, list[UnitState]] = defaultdict(list)
    all_seqs: set[int] = set()
    for us in unit_states:
        seq_states[us.seq].append(us)
        all_seqs.add(us.seq)

    if not all_seqs:
        return []

    max_seq = max(all_seqs)
    geojson_features: list[dict] = []

    # 对每个步骤，计算每个部队的「有效状态」（最新且 ≤ 当前步骤）
    for current_seq in sorted(all_seqs):
        # 为每个部队找到最新的 unit_state (seq <= current_seq)
        effective: dict[str, UnitState] = {}
        for us in unit_states:
            if us.seq > current_seq:
                continue
            if us.unit_name not in effective or us.seq > effective[us.unit_name].seq:
                effective[us.unit_name] = us

        for unit_name, us in effective.items():
            unit = unit_map.get(unit_name)
            location = us.location
            if not location or location not in coord_map:
                continue

            base = coord_map[location]
            offset = offsets.get(unit_name, [0, 0])
            anchor_lng = base[0] + offset[0]
            anchor_lat = base[1] + offset[1]

            # 方向：优先 unit_state，回退到 unit 级别默认方向
            direction = us.direction or (unit.direction if unit else None)
            angle = _angle_for_direction(direction) if direction else None

            feat_list = _make_unit_banner_features(
                anchor_lng, anchor_lat, angle, direction,
                direction_len_m, unit_name,
                unit.faction if unit else "",
                us.status, current_seq, us.description, scale,
            )
            geojson_features.extend(feat_list)

    return geojson_features


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
        "scale": campaign.scale,
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
        t_pipeline_start = time.perf_counter()

        # Stage 1: Extract
        use_timeline = request.mode == "timeline"
        t0 = time.perf_counter()
        try:
            if use_timeline:
                campaign = extract_timeline(request.text)
            else:
                campaign = extract(request.text)
        except ValueError as e:
            yield _sse_event("error", {"stage": "extract", "message": str(e)})
            return

        extract_elapsed = (time.perf_counter() - t0) * 1000
        places_count = len(campaign.places)
        routes_count = len(campaign.routes)
        events_count = len(getattr(campaign, "events", []))
        extract_detail = f"提取结构数据 ({places_count}地名, {routes_count}路线"
        if use_timeline:
            extract_detail += f", {events_count}事件"
        extract_detail += ")"
        logger.info("Stage 1 提取: %s, 耗时 %.0fms", extract_detail, extract_elapsed)
        yield _sse_event("progress", {
            "stage": "extract_done",
            "detail": extract_detail,
            "ok": True,
            "elapsed_ms": round(extract_elapsed),
        })

        # Stage 2: Geocode
        dyn_beg, dyn_end = None, None
        if request.dynasty and request.dynasty in _DYNASTY_YEARS:
            dyn_beg, dyn_end = _DYNASTY_YEARS[request.dynasty]

        t0 = time.perf_counter()
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

        geocode_elapsed = (time.perf_counter() - t0) * 1000
        chgis_count = sum(1 for f in features if f.source == "chgis")
        llm_count = sum(1 for f in features if f.source == "llm_infer")
        logger.info("Stage 2 地理编码: %d CHGIS + %d LLM, 耗时 %.0fms",
                     chgis_count, llm_count, geocode_elapsed)
        yield _sse_event("progress", {
            "stage": "geocode_done",
            "detail": f"匹配古地名 ({chgis_count} CHGIS + {llm_count} LLM推断)",
            "ok": True,
            "elapsed_ms": round(geocode_elapsed),
        })

        # Stage 3: Build routes & GeoJSON
        t0 = time.perf_counter()
        route_lines = _build_routes(campaign, features)
        timeline_events = getattr(campaign, "events", []) if use_timeline else None
        geojson = _make_geojson(features, route_lines, events=timeline_events)

        render_elapsed = (time.perf_counter() - t0) * 1000
        render_detail = f"渲染地图 ({len(features)}标记, {len(route_lines)}路线)"
        if use_timeline and timeline_events:
            render_detail += f", {len(timeline_events)}步骤"
        logger.info("Stage 3 渲染: %s, 耗时 %.0fms", render_detail, render_elapsed)
        yield _sse_event("progress", {
            "stage": "render_done",
            "detail": render_detail,
            "ok": True,
            "elapsed_ms": round(render_elapsed),
        })

        # Stage 3.5: Build unit GeoJSON (timeline mode only)
        unit_geojson_features: list[dict] = []
        if use_timeline:
            timeline_units = getattr(campaign, "units", [])
            timeline_unit_states = getattr(campaign, "unit_states", [])
            if timeline_units and timeline_unit_states:
                unit_geojson_features = _make_unit_geojson(
                    timeline_units, timeline_unit_states, features, campaign.scale,
                )
                # 将部队 feature 合并到 GeoJSON FeatureCollection
                geojson["features"].extend(unit_geojson_features)

        # Final result
        total_elapsed = (time.perf_counter() - t_pipeline_start) * 1000
        logger.info("管道全部完成: 总耗时 %.0fms (提取 %.0f + 编码 %.0f + 渲染 %.0f)",
                     total_elapsed, extract_elapsed, geocode_elapsed, render_elapsed)
        result: dict = {
            "extract_id": uuid.uuid4().hex[:12],
            "campaign_name": campaign.campaign_name,
            "factions": [f.model_dump(by_alias=True) for f in campaign.factions],
            "features": [f.model_dump() for f in features],
            "routes": [r.model_dump() for r in route_lines],
            "geojson": geojson,
            "scale": campaign.scale,
            "elapsed": {
                "extract_ms": round(extract_elapsed),
                "geocode_ms": round(geocode_elapsed),
                "render_ms": round(render_elapsed),
                "total_ms": round(total_elapsed),
            },
        }
        if use_timeline and timeline_events:
            result["events"] = [e.model_dump() for e in timeline_events]
            result["total_steps"] = len(timeline_events)
            if timeline_units:
                result["units"] = [u.model_dump() for u in timeline_units]
            if timeline_unit_states:
                result["unit_states"] = [us.model_dump() for us in timeline_unit_states]
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
        scale=request.scale,
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
        scale=campaign.scale,
    )


# 挂载静态文件（必须在所有路由之后）
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")