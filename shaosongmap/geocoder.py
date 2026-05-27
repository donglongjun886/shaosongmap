"""古地名坐标匹配器：CHGIS v6 精确匹配 + LLM 上下文推断兜底。"""

from __future__ import annotations

import csv
import functools
import json
import logging
from difflib import SequenceMatcher
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger(__name__)

from shaosongmap.models import GeoFeature, Place

# CHGIS CSV 文件预期位于此路径
_CHGIS_DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'chgis_v6'
_CHGIS_V6_CSV = _CHGIS_DATA_DIR / 'chgis_v6_points.csv'

# 用于 LLM 推断坐标的提示词
_INFER_PROMPT = """你是一位中国历史地理专家，熟悉中国古代地名和山川河流的位置。

根据以下战役文段，推断列出的地名的大致经纬度坐标。

原文：
{context}

需要推断的地名：
{places}

对于每个地名：
1. 根据上下文推断它的大致位置（上下文中提到的其他地名、行军方向、山川河流关系）
2. 输出经纬度坐标（GCJ-02 坐标系）
3. 标注对推断结果的置信度：high（确定）、medium（较确定）、low（粗略估计）

以 JSON 数组输出，每个元素格式：
{{"name": "地名", "lng": 经度, "lat": 纬度, "confidence": "high|medium|low", "reasoning": "推断依据"}}

只输出 JSON 数组，不要其他内容。"""


def _fuzzy_match(text: str, candidate: str) -> float:
    """计算两个字符串的模糊匹配相似度 (0.0 ~ 1.0)。"""
    return SequenceMatcher(None, text.lower(), candidate.lower()).ratio()


@functools.lru_cache(maxsize=1)
def _load_chgis_data() -> list[dict]:
    """加载 CHGIS v6 数据集。

    预期 CSV 列：
        name_ch: 中文地名
        x_coord: 经度
        y_coord: 纬度
        beg_yr: 该地名存在的起始年份（公元纪年）
        end_yr: 该地名存在的结束年份（公元纪年）
        lev: 行政层级（府/州/县）
        modern_name: 现代地名（可选）

    Returns:
        地名记录列表，每条为 dict

    Raises:
        FileNotFoundError: CHGIS 数据文件不存在
    """
    if not _CHGIS_V6_CSV.exists():
        logger.warning('CHGIS 数据文件缺失: %s，全部地名为 LLM 推断', _CHGIS_V6_CSV)
        raise FileNotFoundError(
            f'CHGIS v6 数据文件不存在: {_CHGIS_V6_CSV}\n请将 CHGIS v6 点数据放置于此路径'
        )
    records = []
    with open(_CHGIS_V6_CSV, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(
                {
                    'name_ch': row.get('name_ch', ''),
                    'lng': float(row.get('x_coord', 0)),
                    'lat': float(row.get('y_coord', 0)),
                    'beg_yr': int(row.get('beg_yr', 0)),
                    'end_yr': int(row.get('end_yr', 9999)),
                    'lev': row.get('lev', ''),
                    'modern_name': row.get('modern_name', ''),
                }
            )
    return records


def match_chgis(
    place_name: str,
    dynasty_beg_yr: int | None = None,
    dynasty_end_yr: int | None = None,
    threshold: float = 0.8,
) -> GeoFeature | None:
    """在 CHGIS v6 数据集中匹配古地名的经纬度坐标。

    匹配策略：
    1. 模糊字符串匹配（相似度 >= threshold）
    2. 如有朝代时间范围，优先返回时间重叠的候选
    3. 如无朝代信息，返回相似度最高的候选

    Args:
        place_name: 古地名字符串
        dynasty_beg_yr: 朝代起始年份（公元纪年，可为 None）
        dynasty_end_yr: 朝代结束年份（公元纪年，可为 None）
        threshold: 模糊匹配最低相似度阈值

    Returns:
        GeoFeature（source="chgis"），匹配失败返回 None
    """
    records = _load_chgis_data()
    candidates: list[tuple[float, dict]] = []

    for rec in records:
        score = _fuzzy_match(place_name, rec['name_ch'])
        if score >= threshold:
            candidates.append((score, rec))

    if not candidates:
        return None

    # 按相似度降序排列
    candidates.sort(key=lambda x: x[0], reverse=True)

    # 如果有朝代限制，按时间重叠过滤
    if dynasty_beg_yr and dynasty_end_yr:
        for _score, rec in candidates:
            # 地名存在时间与目标朝代有交集
            if rec['beg_yr'] <= dynasty_end_yr and rec['end_yr'] >= dynasty_beg_yr:
                return GeoFeature(
                    name=place_name,
                    lng=rec['lng'],
                    lat=rec['lat'],
                    source='chgis',
                    modern_name=rec.get('modern_name'),
                )

    # 无朝代限制或没有时间匹配的，返回得分最高的
    best_score, best_rec = candidates[0]
    return GeoFeature(
        name=place_name,
        lng=best_rec['lng'],
        lat=best_rec['lat'],
        source='chgis',
        modern_name=best_rec.get('modern_name'),
    )


def infer_with_llm(
    place_names: list[str],
    context_text: str,
    model: str = 'deepseek-chat',
) -> list[GeoFeature]:
    """调用 LLM 根据上下文推断地名近似坐标。

    Args:
        place_names: 无法在 CHGIS 中匹配的地名列表
        context_text: 完整的原始战役文本（提供上下文）
        model: DeepSeek 模型名称

    Returns:
        GeoFeature 列表，source 为 "llm_infer" 或 "unknown"
    """
    if not place_names:
        return []

    from shaosongmap.config import settings

    if settings is None:
        raise RuntimeError('配置未初始化，请检查应用启动流程')

    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    prompt = _INFER_PROMPT.format(
        context=context_text,
        places='\n'.join(f'- {p}' for p in place_names),
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.3,
        response_format={'type': 'json_object'},
        timeout=60.0,
    )

    raw = response.choices[0].message.content
    if not raw:
        # LLM 无响应时，全部标记为 unknown
        return [GeoFeature(name=name, source='unknown') for name in place_names]

    try:
        data = json.loads(raw)
        # LLM 可能返回 {"result": [...]} 或直接返回数组
        items = data if isinstance(data, list) else data.get('result', [])
    except json.JSONDecodeError:
        logger.warning('LLM 返回非 JSON 格式，标记为 unknown')
        return [GeoFeature(name=name, source='unknown') for name in place_names]

    results: list[GeoFeature] = []
    for item in items:
        name = item.get('name', '')
        try:
            results.append(
                GeoFeature(
                    name=name,
                    lng=item.get('lng'),
                    lat=item.get('lat'),
                    source='llm_infer',
                    confidence=item.get('confidence', 'low'),
                )
            )
        except Exception:
            results.append(GeoFeature(name=name, source='unknown'))

    # 确保不遗漏输入中但 LLM 未返回的地名
    returned_names = {r.name for r in results}
    for name in place_names:
        if name not in returned_names:
            results.append(GeoFeature(name=name, source='unknown'))

    return results


def geocode(
    places: list[Place],
    context_text: str = '',
    dynasty_beg_yr: int | None = None,
    dynasty_end_yr: int | None = None,
) -> list[GeoFeature]:
    """遍历地名列表，优先 CHGIS 匹配，失败则 LLM 推断。

    这是 Geocoder 的主入口函数。

    Args:
        places: Extractor 提取的地名列表
        context_text: 原始战役文本（LLM 推断时用作上下文）
        dynasty_beg_yr: 朝代起始年份（可选，用于 CHGIS 时间过滤）
        dynasty_end_yr: 朝代结束年份（可选）

    Returns:
        GeoFeature 列表，每个地名一条，含坐标和来源标记
    """
    unmatched: list[str] = []
    results: list[GeoFeature] = []

    logger.info('地理编码开始: %d 地名', len(places))  # 第一遍：CHGIS 匹配
    for place in places:
        chgis = None
        try:
            chgis = match_chgis(place.name, dynasty_beg_yr, dynasty_end_yr)
        except FileNotFoundError:
            # CHGIS 数据缺失，全部走 LLM 兜底
            unmatched.append(place.name)
            continue

        if chgis:
            chgis.place_type = place.place_type
            results.append(chgis)
        else:
            unmatched.append(place.name)

    # 建立地名→Place映射，用于补充place_type
    place_map = {p.name: p for p in places}

    # 第二遍：LLM 推断兜底
    if unmatched:
        logger.info('LLM 推断兜底: %d 个地名', len(unmatched))
        llm_results = infer_with_llm(unmatched, context_text)
        for feat in llm_results:
            if feat.name in place_map:
                feat.place_type = place_map[feat.name].place_type
        results.extend(llm_results)

    logger.info(
        '地理编码完成: %d CHGIS + %d LLM + %d unknown',
        sum(1 for r in results if r.source == 'chgis'),
        sum(1 for r in results if r.source == 'llm_infer'),
        sum(1 for r in results if r.source == 'unknown'),
    )
    return results
