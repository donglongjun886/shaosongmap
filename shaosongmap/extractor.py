"""战役文本提取器：通过 DeepSeek API 将战役文本转换为结构化 JSON。"""

from __future__ import annotations

import json
import logging
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from shaosongmap.models import CampaignExtract, CampaignTimeline

_SYSTEM_PROMPT = """你是一位中国历史地理专家，从战役/行军文本中提取结构化JSON。

{
  "campaign_name": "战役名称或null",
  "factions": [{"name": "阵营名", "commanders": ["将领"], "troops": "兵力描述或null"}],
  "places": [{"name": "古地名", "context": "原文片段", "place_type": "city|mountain_pass|river|mountain|region|battlefield|null"}],
  "routes": [{"from": "起点", "to": "终点", "via": ["途经地"]}]
}

规则：
1. 只提取明确信息，地名用原文古称，兵力保留原文描述（如「三万」），不要编造或转换
2. 仅从实际军事行动段落提取，忽略朝堂对话和议论。对话中假设性建议（如「臣以为应从X出兵」）不算实际行军
3. 军队编制名（如「秦凤路大军」「泾原路兵马」）中的行政区划名不提取为places，仅在作为独立地理位置出现时才提取
4. 无军事行动时返回空places/routes"""


def _build_client() -> OpenAI:
    """构建 DeepSeek API 客户端。

    DeepSeek API 兼容 OpenAI SDK，通过 base_url 和 api_key 切换。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    if not api_key:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")
    return OpenAI(api_key=api_key, base_url=base_url)


# 军队编制后缀模式：地名后紧跟这些词时，该地名可能是军队编制的修饰语而非独立地理位置
_MILITARY_UNIT_SUFFIXES = re.compile(
    r"(大军|兵马|部队|将士|诸军|各部|行营|都统司|厢军|乡兵|蕃兵|禁军|厢兵|屯驻军|驻泊军|就粮军|系将兵|不系将兵|土兵|弓手|义勇|保甲|乡弓手|寨兵|水军|步军|马军|砦兵|戍卒|劲卒|锐卒|精卒|义军|忠义军|义士|民兵|土军|边军|戍兵|客军|正军|裨将|偏师|偏裨|游师)"
)


def _filter_military_unit_places(places: list[dict]) -> list[dict]:
    """过滤掉上下文表明属于军队编制名的地名。

    当地名在上下文文本中后紧跟军事编制后缀（如「大军」「兵马」等），
    说明该地名是军队编制名的一部分（如「秦凤路大军」中的「秦凤路」），
    而非独立地理位置，应从 places 列表中移除。

    Args:
        places: LLM 返回的地名列表，每项含 name 和 context 字段

    Returns:
        过滤后的地名列表
    """
    logger = logging.getLogger(__name__)
    filtered = []
    for place in places:
        name = place.get("name", "")
        context = place.get("context", "")
        if not name or not context:
            filtered.append(place)
            continue

        # 在 context 中查找地名后紧跟军队编制后缀的模式
        # 使用非贪婪匹配：地名 + 可选空白/标点 + 军队后缀
        pattern = re.escape(name) + r"\s*" + _MILITARY_UNIT_SUFFIXES.pattern
        if re.search(pattern, context):
            logger.info("过滤军队编制名: %s (上下文: %s)", name, context)
            continue

        filtered.append(place)

    return filtered


def extract(text: str, model: str = "deepseek-chat") -> CampaignExtract:
    """从一段战役文本中提取结构化数据。

    Args:
        text: 战役/行军文本
        model: DeepSeek 模型名称，默认 deepseek-chat

    Returns:
        CampaignExtract: 提取的结构化战役数据

    Raises:
        ValueError: 文本为空或模型返回格式不合法
    """
    text = text.strip()
    if not text:
        raise ValueError("战役文本不能为空")

    client = _build_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    if not raw:
        raise ValueError("DeepSeek API 返回空响应")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"DeepSeek 返回非 JSON 内容: {raw[:200]}") from e

    if "places" in data:
        data["places"] = _filter_military_unit_places(data["places"])

    return CampaignExtract.model_validate(data)


_TIMELINE_SYSTEM_PROMPT = """你是一位中国历史地理专家，从战役/行军文本中提取结构化JSON。

{
  "campaign_name": "战役名称或null",
  "factions": [{"name": "阵营名", "commanders": ["将领"], "troops": "兵力描述或null"}],
  "places": [{"name": "古地名", "context": "原文片段", "place_type": "city|mountain_pass|river|mountain|region|battlefield|null"}],
  "routes": [{"from": "起点", "to": "终点", "via": ["途经地"]}],
  "events": [{"seq": 1, "event_type": "march|battle|encamp|retreat", "description": "一句话描述", "actors": ["将领/部队"], "places_involved": ["地名"]}]
}

规则：
1. 只提取明确信息，地名用原文古称，兵力保留原文描述，不要编造或转换
2. 仅从实际军事行动段落提取，忽略朝堂对话和议论。对话中假设性建议不算实际行军
3. 军队编制名（如「秦凤路大军」「泾原路兵马」）中的行政区划名不提取为places
4. events按时间顺序排列，seq从1递增，event_type为march/battle/encamp/retreat，places_involved必须是places中已有地名
5. 无军事行动时返回空places/routes/events"""


def extract_timeline(text: str, model: str = "deepseek-chat") -> CampaignTimeline:
    """从战役文本中提取时间线结构化数据。

    与 extract() 的区别：额外返回按时间顺序排列的 events 数组，
    供前端时间轴逐步渲染使用。

    Args:
        text: 战役/行军文本
        model: DeepSeek 模型名称，默认 deepseek-chat

    Returns:
        CampaignTimeline: 包含事件序列的战役数据

    Raises:
        ValueError: 文本为空或模型返回格式不合法
    """
    text = text.strip()
    if not text:
        raise ValueError("战役文本不能为空")

    client = _build_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _TIMELINE_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    if not raw:
        raise ValueError("DeepSeek API 返回空响应")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"DeepSeek 返回非 JSON 内容: {raw[:200]}") from e

    if "places" in data:
        data["places"] = _filter_military_unit_places(data["places"])

    return CampaignTimeline.model_validate(data)