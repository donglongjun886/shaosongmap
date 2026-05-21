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

_SYSTEM_PROMPT = """你是一位中国历史地理专家，擅长从历史战争文本中提取结构化信息。

你的任务：分析用户提供的历史战役/行军文本，提取以下信息并输出 JSON：

{
  "campaign_name": "战役名称，如果文本没有明确名称则为 null",
  "factions": [
    {
      "name": "阵营名称（如宋军、金军、蒙古军）",
      "commanders": ["将领名字列表"],
      "troops": "兵力描述（如三万、十万），如果文本未提及则为 null"
    }
  ],
  "places": [
    {
      "name": "古地名（按文中出现顺序）",
      "context": "原文中出现该地名的句子片段，用于后续消歧义",
      "place_type": "地名类型，可选值：city(城池)、mountain_pass(关隘)、river(河流)、mountain(山脉)、region(行政区)、battlefield(战场)。无法确定时填 null"
    }
  ],
  "routes": [
    {
      "from": "起点地名",
      "to": "终点地名",
      "via": ["途经地点，无则为空数组"]
    }
  ]
}

规则：
1. 只提取文本中明确提及的信息，不要编造
2. 地名使用原文中的古代名称，不要转换为现代名称
3. 兵力保留原文描述（如「三万人马」「十万大军」），不要转换为数字
4. 如果同一方有多位将领，全部列出
5. 行军路线按文中描述的先后顺序排列
6. 如果文本只描述行军不涉及战斗，campaign_name 为 null
7. 文本可能混合朝堂对话、人物议论和军事行动描写。只从确认的军事行动段落中提取信息。人物在对话中假设、建议或讨论的军事行动（如「臣以为应从某地出兵」）不应被视为实际行军节点
8. 朝堂对话、场景描写等非军事内容直接忽略
9. 地名如作为军队编制名称的一部分出现——如「秦凤路大军」「泾原路兵马」「环庆路将士」「熙河路各部」等，其中的行政区划名（秦凤路、泾原路等）是军队编制修饰语，而非独立地理位置，不要将其提取为 places。仅当地名在文中作为独立地理实体出现（如「大军自秦凤路出发」「渭州城内」），才提取为 places
10. 如果文本中没有任何可确认的军事行动，返回空的 places 和 routes，factions 仅包含对话中提到的阵营（无将领和兵力）"""


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


_TIMELINE_SYSTEM_PROMPT = """你是一位中国历史地理专家，擅长从历史战争文本中提取结构化信息。

你的任务：分析用户提供的历史战役/行军文本，提取以下信息并输出 JSON：

{
  "campaign_name": "战役名称，如果文本没有明确名称则为 null",
  "factions": [
    {
      "name": "阵营名称（如宋军、金军、蒙古军）",
      "commanders": ["将领名字列表"],
      "troops": "兵力描述（如三万、十万），如果文本未提及则为 null"
    }
  ],
  "places": [
    {
      "name": "古地名（按文中出现顺序）",
      "context": "原文中出现该地名的句子片段，用于后续消歧义",
      "place_type": "地名类型，可选值：city(城池)、mountain_pass(关隘)、river(河流)、mountain(山脉)、region(行政区)、battlefield(战场)。无法确定时填 null"
    }
  ],
  "routes": [
    {
      "from": "起点地名",
      "to": "终点地名",
      "via": ["途经地点，无则为空数组"]
    }
  ],
  "events": [
    {
      "seq": 1,
      "event_type": "march",
      "description": "岳飞率军从襄阳出发，向东北方向行军",
      "actors": ["岳飞", "岳家军"],
      "places_involved": ["襄阳"]
    },
    {
      "seq": 2,
      "event_type": "battle",
      "description": "在唐州遭遇金军斥候，发生小规模冲突",
      "actors": ["岳飞", "金军斥候"],
      "places_involved": ["唐州"]
    }
  ]
}

规则：
1. 只提取文本中明确提及的信息，不要编造
2. 地名使用原文中的古代名称，不要转换为现代名称
3. 兵力保留原文描述（如「三万人马」「十万大军」），不要转换为数字
4. 如果同一方有多位将领，全部列出
5. 行军路线按文中描述的先后顺序排列
6. 如果文本只描述行军不涉及战斗，campaign_name 为 null
7. 文本可能混合朝堂对话、人物议论和军事行动描写。只从确认的军事行动段落中提取信息。人物在对话中假设、建议或讨论的军事行动（如「臣以为应从某地出兵」）不应被视为实际行军节点
8. 朝堂对话、场景描写等非军事内容直接忽略
9. 地名如作为军队编制名称的一部分出现——如「秦凤路大军」「泾原路兵马」「环庆路将士」「熙河路各部」等，其中的行政区划名（秦凤路、泾原路等）是军队编制修饰语，而非独立地理位置，不要将其提取为 places。仅当地名在文中作为独立地理实体出现（如「大军自秦凤路出发」「渭州城内」），才提取为 places
10. 将文中军事行动按时间顺序分解为事件序列，填入 events 数组。每个事件：
   - seq: 从 1 开始递增
   - event_type: "march"(行军)、"battle"(战斗)、"encamp"(扎营/驻扎)、"retreat"(撤退)
   - description: 用一句话简洁描述该事件
   - actors: 参与该事件的将领或部队
   - places_involved: 该事件涉及的地名，必须是 places 数组中已列出的地名
11. 如果文本中没有任何可确认的军事行动，返回空的 places、routes 和 events"""


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