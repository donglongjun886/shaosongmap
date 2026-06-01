"""地理实体提取器：通过 DeepSeek API 将历史文本转换为地理实体结构化 JSON。"""

from __future__ import annotations

import json
import re

from openai import OpenAI

from shaosongmap.models import GeoEntityExtract

_SYSTEM_PROMPT = """你是一位中国历史地理专家，从历史文本中提取纯地理实体信息。

{
  "event_name": "事件/战役名称或null",
  "dynasty": "朝代（如'南宋''北宋''唐'）或null",
  "boundaries": [{"name": "边界名称", "description": "边界描述文本"}],
  "person_places": [{"person": "人物名", "place": "地名", "relation": "关系（如'驻扎''出生''战死''行军经过'）"}],
  "places": [{"name": "古地名", "context": "原文片段"}],
  "scale": "tactical|battle|strategic或null"
}

规则：
1. 只提取地理相关信息：边界/疆域、人物与地点关联、地名列表。不提取部队编制、兵力数量、行军路线、进攻方向
2. 地名用原文古称，不要编造或转换
3. 仅从实际发生的事件段落提取，忽略朝堂议论和假设性建议（如「臣以为应从X出兵」不算实际发生）
4. boundaries 提取文中明确描述的疆域边界（如「宋金以淮河为界」），仅在原文有明确边界描述时填入
5. person_places 提取人物直接关联的地点（如「岳飞驻襄阳」「完颜宗弼镇守汴京」「李纲生于华亭」），relation 字段简洁概括关系
6. scale 判定标准：
   - tactical：仅涉及1个具体城池/地点
   - battle：涉及2个及以上具体地点，或在一个州/府范围内移动
   - strategic：跨州/路/省的宏观描述，或涉及"江淮""关中""河北"等区域概念
   无法判断时填 null
7. places 与 person_places 关系：places 是文本中出现的所有独立地理位置的全集（包含已在 person_places 中出现的地名），person_places 是带人物关联的子集，两者可以有重复。places 仅提取作为独立地理位置出现的地名，军队编制名中的地名不提取。
8. 列表字段（boundaries/person_places/places）无数据时必须返回空数组 []，不可返回 null
9. 仅输出合法JSON，不要包含任何Markdown标记或解释文本

反例（Negative Examples）：以下情况不提取为places——
- 「建康府大军」中的「建康府」是军队编制名，不提取为place
- 「秦凤路兵马」中的「秦凤路」是军队编制名，不提取为place
- 「泾原路大军」中的「泾原路」是军队编制名，不提取为place
只有当这些地名作为独立地理位置出现时才提取（如「岳飞进入秦凤路」中的「秦凤路」应提取）"""

# 军队编制后缀模式，用于兜底过滤
_MILITARY_SUFFIX_PATTERN = re.compile(
    r'(大军|兵马|行营|都统司|厢军|乡兵|禁军|厢|砦兵|戍卒|义军|民兵|土军|边军|屯驻军|驻泊军)$'
)


def _filter_military_names(places: list[dict]) -> list[dict]:
    """过滤掉名称后缀表明属于军队编制的'地名'。

    作为 LLM prompt 约束的兜底保障，在结果返回后对每个地名做正则校验。
    如果地名以军队编制后缀结尾，则从列表中移除。

    Args:
        places: LLM 返回的原始 places 列表，每项含 name 和 context 字段

    Returns:
        过滤后的 places 列表
    """
    return [p for p in places if not _MILITARY_SUFFIX_PATTERN.search(p.get('name', ''))]


def _build_client() -> OpenAI:
    """构建 DeepSeek API 客户端。"""
    from shaosongmap.config import settings

    if settings is None:
        raise RuntimeError('配置未初始化，请检查应用启动流程')
    return OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)


def extract(text: str, model: str = 'deepseek-chat') -> GeoEntityExtract:
    """从一段历史文本中提取地理实体数据。

    提取内容：事件名称、朝代、边界/疆域、人物→地点关联、地名列表、地图尺度。
    不提取部队编制、兵力数量、行军路线、进攻方向。

    Args:
        text: 历史文本
        model: DeepSeek 模型名称，默认 deepseek-chat

    Returns:
        GeoEntityExtract: 提取的地理实体数据（边界、人物地点关联、地名列表）

    Raises:
        ValueError: 文本为空或模型返回格式不合法
    """
    text = text.strip()
    if not text:
        raise ValueError('历史文本不能为空')

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

    # 清洗 Markdown 代码块包裹（如 ```json ... ```）
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.MULTILINE)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f'DeepSeek 返回非 JSON 内容: {raw[:200]}') from e

    # 兜底过滤：LLM 偶尔仍会将军队编制名误提取为地名
    if 'places' in data and isinstance(data['places'], list):
        data['places'] = _filter_military_names(data['places'])

    return GeoEntityExtract.model_validate(data)
