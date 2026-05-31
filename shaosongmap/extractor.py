"""战役文本提取器：通过 DeepSeek API 将战役文本转换为结构化 JSON。"""

from __future__ import annotations

import json
import logging
import re

from openai import OpenAI

from shaosongmap.models import CampaignExtract

_SYSTEM_PROMPT = """你是一位中国历史地理专家，从战役/行军文本中提取结构化JSON。

{
  "campaign_name": "战役名称或null",
  "factions": [{"name": "阵营名", "commanders": ["将领"], "troops": "兵力描述或null"}],
  "places": [{"name": "古地名", "context": "原文片段", "place_type": "city|mountain_pass|river|mountain|region|battlefield|camp|null"}],
  "routes": [{"from": "起点", "to": "终点", "via": ["途经地"]}]
}

规则：
1. 只提取明确信息，地名用原文古称，兵力保留原文描述（如「三万」），不要编造或转换
2. 仅从实际军事行动段落提取，忽略朝堂对话和议论。对话中假设性建议（如「臣以为应从X出兵」）不算实际行军
3. 军队编制名（如「秦凤路大军」「泾原路兵马」）中的行政区划名不提取为places，仅在作为独立地理位置出现时才提取
4. routes中的节点名称必须严格来自places列表中已提取的地名，不得使用places中不存在的地名
5. 无军事行动时返回空places/routes
6. 阵营标准化规则：factions的name必须使用标准历史朝代单字称谓（「宋」「金」「西夏」「辽」等），不得使用「我军」「敌军」「金军」「宋兵」等指代词或多字组合。若文本未明确提及阵营名称，必须根据历史常识推断（宋代背景下汉族将领→宋，女真/契丹将领→金）
7. 仅输出合法JSON，不要包含任何Markdown标记或解释文本"""


def _build_client() -> OpenAI:
    """构建 DeepSeek API 客户端。"""
    from shaosongmap.config import settings

    if settings is None:
        raise RuntimeError('配置未初始化，请检查应用启动流程')
    return OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)


# 军队编制后缀模式
_MILITARY_UNIT_SUFFIXES = re.compile(
    r'(大军|兵马|部队|将士|诸军|各部|行营|都统司|厢军|乡兵|蕃兵|禁军|厢兵|屯驻军|驻泊军|就粮军|系将兵|不系将兵|土兵|弓手|义勇|保甲|乡弓手|寨兵|水军|步军|马军|砦兵|戍卒|劲卒|锐卒|精卒|义军|忠义军|义士|民兵|土军|边军|戍兵|客军|正军|裨将|偏师|偏裨|游师)'
)


def _filter_military_unit_places(places: list[dict]) -> list[dict]:
    """过滤掉上下文表明属于军队编制名的地名。"""
    logger = logging.getLogger(__name__)
    filtered = []
    for place in places:
        name = place.get('name', '')
        context = place.get('context', '')
        if not name or not context:
            filtered.append(place)
            continue
        pattern = re.escape(name) + r'\s*' + _MILITARY_UNIT_SUFFIXES.pattern
        if re.search(pattern, context):
            logger.info('过滤军队编制名: %s (上下文: %s)', name, context)
            continue
        filtered.append(place)
    return filtered


def extract(text: str, model: str = 'deepseek-chat') -> CampaignExtract:
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
        raise ValueError('战役文本不能为空')

    client = _build_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': _SYSTEM_PROMPT},
            {'role': 'user', 'content': text},
        ],
        temperature=0.1,
        response_format={'type': 'json_object'},
        timeout=60.0,
    )

    raw = response.choices[0].message.content
    if not raw:
        raise ValueError('DeepSeek API 返回空响应')

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f'DeepSeek 返回非 JSON 内容: {raw[:200]}') from e

    if 'places' in data:
        data['places'] = _filter_military_unit_places(data['places'])

    return CampaignExtract.model_validate(data)
