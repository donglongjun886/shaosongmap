"""战役文本提取器：通过 DeepSeek API 将战役文本转换为结构化 JSON。"""

from __future__ import annotations

import json
import os

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
      "context": "原文中出现该地名的句子片段，用于后续消歧义"
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
9. 如果文本中没有任何可确认的军事行动，返回空的 places 和 routes，factions 仅包含对话中提到的阵营（无将领和兵力）"""


def _build_client() -> OpenAI:
    """构建 DeepSeek API 客户端。

    DeepSeek API 兼容 OpenAI SDK，通过 base_url 和 api_key 切换。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    if not api_key:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")
    return OpenAI(api_key=api_key, base_url=base_url)


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
      "context": "原文中出现该地名的句子片段，用于后续消歧义"
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
9. 将文中军事行动按时间顺序分解为事件序列，填入 events 数组。每个事件：
   - seq: 从 1 开始递增
   - event_type: "march"(行军)、"battle"(战斗)、"encamp"(扎营/驻扎)、"retreat"(撤退)
   - description: 用一句话简洁描述该事件
   - actors: 参与该事件的将领或部队
   - places_involved: 该事件涉及的地名，必须是 places 数组中已列出的地名
10. 如果文本中没有任何可确认的军事行动，返回空的 places、routes 和 events"""


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

    return CampaignTimeline.model_validate(data)