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
  "places": [{"name": "古地名", "context": "原文片段", "place_type": "city|mountain_pass|river|mountain|region|battlefield|camp|null"}],
  "routes": [{"from": "起点", "to": "终点", "via": ["途经地"]}],
  "scale": "tactical|battle|strategic|null"
}

规则：
1. 只提取明确信息，地名用原文古称，兵力保留原文描述（如「三万」），不要编造或转换
2. 仅从实际军事行动段落提取，忽略朝堂对话和议论。对话中假设性建议（如「臣以为应从X出兵」）不算实际行军
3. 军队编制名（如「秦凤路大军」「泾原路兵马」）中的行政区划名不提取为places，仅在作为独立地理位置出现时才提取
4. 无军事行动时返回空places/routes
5. scale分类规则：tactical(战术级,1-10km,单地点局部冲突/单次遭遇) / battle(战役级,20-200km,多地行军数日) / strategic(战略级,200-1000km,跨州府多路并进数月)；仅一处地点且方向单一用tactical，多地点有完整行军路线用battle，涉及多路大军跨多个州府的用strategic；无军事行动时用null
6. 阵营标准化规则：factions的name必须使用标准历史朝代单字称谓（「宋」「金」「西夏」「辽」等），不得使用「我军」「敌军」「金军」「宋兵」等指代词或多字组合。若文本未明确提及阵营名称，必须根据历史常识推断（宋代背景下汉族将领→宋，女真/契丹将领→金）"""


def _build_client() -> OpenAI:
    """构建 DeepSeek API 客户端。

    DeepSeek API 兼容 OpenAI SDK，通过 base_url 和 api_key 切换。
    """
    api_key = os.getenv('DEEPSEEK_API_KEY', '')
    base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    if not api_key:
        raise ValueError('请设置环境变量 DEEPSEEK_API_KEY')
    return OpenAI(api_key=api_key, base_url=base_url)


# 军队编制后缀模式：地名后紧跟这些词时，该地名可能是军队编制的修饰语而非独立地理位置
_MILITARY_UNIT_SUFFIXES = re.compile(
    r'(大军|兵马|部队|将士|诸军|各部|行营|都统司|厢军|乡兵|蕃兵|禁军|厢兵|屯驻军|驻泊军|就粮军|系将兵|不系将兵|土兵|弓手|义勇|保甲|乡弓手|寨兵|水军|步军|马军|砦兵|戍卒|劲卒|锐卒|精卒|义军|忠义军|义士|民兵|土军|边军|戍兵|客军|正军|裨将|偏师|偏裨|游师)'
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
        name = place.get('name', '')
        context = place.get('context', '')
        if not name or not context:
            filtered.append(place)
            continue

        # 在 context 中查找地名后紧跟军队编制后缀的模式
        # 使用非贪婪匹配：地名 + 可选空白/标点 + 军队后缀
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


_TIMELINE_SYSTEM_PROMPT = """你是一位中国历史地理专家，从战役/行军文本中提取结构化JSON。

{
  "campaign_name": "战役名称或null",
  "factions": [{"name": "阵营名", "commanders": ["将领"], "troops": "兵力描述或null"}],
  "places": [{"name": "古地名", "context": "原文片段", "place_type": "city|mountain_pass|river|mountain|region|battlefield|camp|null"}],
  "routes": [{"from": "起点", "to": "终点", "via": ["途经地"]}],
  "events": [{"seq": 1, "event_type": "march|battle|encamp|retreat", "description": "一句话描述", "actors": ["将领/部队"], "places_involved": ["地名"]}],
  "units": [{"name": "部队名", "faction": "所属阵营", "commander": "指挥官", "troop_type": "infantry|cavalry|mixed", "troop_count": "兵力描述", "direction": "进攻方位或null"}],
  "unit_states": [{"seq": 1, "unit_name": "部队名", "status": "deploying|marching|engaging|retreating|routing", "location": "所在地名或null", "direction": "进攻方位或null", "description": "一句话战术动作描述"}],
  "scale": "tactical|battle|strategic|null"
}

规则：
1. 只提取明确信息，地名用原文古称，兵力保留原文描述，不要编造或转换
2. 仅从实际军事行动段落提取，忽略朝堂对话和议论。对话中假设性建议不算实际行军
3. 军队编制名（如「秦凤路大军」「泾原路兵马」）中的行政区划名不提取为places
4. events按时间顺序排列，seq从1递增，event_type为march/battle/encamp/retreat，places_involved必须是places中已有地名
5. 无军事行动时返回空places/routes/events/units/unit_states
6. scale分类规则：tactical(战术级,1-10km,单地点局部冲突/单次遭遇) / battle(战役级,20-200km,多地行军数日) / strategic(战略级,200-1000km,跨州府多路并进数月)；仅一处地点且方向单一用tactical，多地点有完整行军路线用battle，涉及多路大军跨多个州府的用strategic；无军事行动时用null
7. units提取规则：从文本中识别独立军事部队实体，同一阵营下可能有多个独立行动的部队（如宋军的「焦文通部」「郦琼部」「秦凤路兵马」是三个不同部队）。部队名在全文JSON中保持统一，不要用别名。troop_type根据文本判断：提及骑/铁浮屠/合扎猛安/拐子马→cavalry，提及步/弩手/刀斧手→infantry，无法判断→mixed。direction必须是标准八方位词之一：东/南/西/北/东南/西南/东北/西北。推断规则和示例：据守/驻守/驻扎X地→无进攻方向，填null；从岭北仰攻→攻击方在防守方北侧向南攻，direction=南；自岭南迂回包抄→攻击方从南侧向北绕行，direction=北；向塬底冲击→塬底相对位置可推断，direction=西北；侧翼压上→侧面推进，无法确定具体方位，填null。绝不可填地名或非方位词（如「侧翼」「塬底」是错误的）。无法推断时填null
8. unit_states提取规则：关键原则——每个event的actors中涉及的部队（无论是进攻方还是被攻击方），都必须在该event的seq有对应的unit_state记录。换句话说，只要部队在某个事件中被提及或参与行动，就应当为其生成该步骤的状态快照，不可遗漏。如果部队在某个步骤确实毫无行为描述，可以跳过。status判断标准：部队列阵/驻扎/原地待命→deploying，部队向某方向移动/进军→marching，部队与敌军交战/接战→engaging，部队主动撤退/后撤→retreating，部队被击溃/全军覆没/崩溃→routing。location必须是places中已有地名。direction同rule 7的标准八方位词约束，绝不可填地名或模糊描述。description用一句话描述该部队在此步骤的战术动作
152	9. 将领姓名规则：factions的commanders和units的commander必须使用完整历史姓名（含姓氏）。例如文本仅提「娄室」应补充为「完颜娄室」，「兀术」→「完颜宗弼」，「韩常」→「韩常」（已有姓氏）；文本提「岳帅」「岳王」应规范为「岳飞」。部队名保持原文不变（如「娄室中军」中有「娄室」不强制改）。无法确定完整姓名时保留下文原文，不要编造姓名
10. 阵营标准化规则：factions的name必须使用标准历史朝代单字称谓（「宋」「金」「西夏」「辽」「蒙古」「元」「清」等），不得使用「我军」「敌军」「对方」「金军」「宋兵」等指代词或多字组合。若文本未明确提及阵营名称（如仅出现「王贵」「完颜宗弼」），必须根据历史常识推断阵营归属——宋代背景下，汉族将领（王贵、张宪、岳飞等）所属为「宋」，女真/契丹将领（完颜宗弼、合扎猛安等）所属为「金」。ForceUnit.faction字段必须与factions数组中某个faction的name值完全一致（字符串精确匹配）。整个JSON中同一阵营不得出现多种称谓变体"""


def _validate_unit_states(
    unit_states: list[dict], units: list[dict], events: list[dict]
) -> list[dict]:
    """校验 unit_states 的有效性并过滤无效记录。

    校验规则：
    1. unit_state 的 seq 必须在 events 中存在
    2. unit_state 的 unit_name 必须在 units 中存在

    Args:
        unit_states: LLM 返回的部队状态列表
        units: LLM 返回的部队实体列表
        events: LLM 返回的事件列表

    Returns:
        过滤后的有效 unit_states 列表
    """
    logger = logging.getLogger(__name__)
    valid_seqs = {e.get('seq') for e in events if isinstance(e, dict)}
    valid_unit_names = {u.get('name') for u in units if isinstance(u, dict)}

    validated = []
    for us in unit_states:
        if not isinstance(us, dict):
            continue
        seq = us.get('seq')
        unit_name = us.get('unit_name', '')
        if seq not in valid_seqs:
            logger.warning('丢弃无效 unit_state: seq=%s 不在 events 中', seq)
            continue
        if unit_name not in valid_unit_names:
            logger.warning("丢弃无效 unit_state: unit_name='%s' 不在 units 中", unit_name)
            continue
        validated.append(us)

    return validated


def _deduplicate_unit_names(units: list[dict]) -> list[dict]:
    """合并疑似同一部队的名称变体。

    使用编辑距离判断两个部队名是否指向同一实体。
    当编辑距离 ≤ 1 且名称长度 ≥ 3 时，视为同一部队并保留先出现的。

    Args:
        units: LLM 返回的部队实体列表

    Returns:
        去重后的部队列表
    """
    if len(units) <= 1:
        return units

    logger = logging.getLogger(__name__)
    kept: list[dict] = []
    for unit in units:
        name = unit.get('name', '')
        # 检查是否与已保留的部队名高度相似
        is_dup = False
        for existing in kept:
            existing_name = existing.get('name', '')
            if len(name) >= 3 and len(existing_name) >= 3:
                dist = _edit_distance(name, existing_name)
                if dist <= 1:
                    logger.info(
                        "合并部队名变体: '%s' → '%s' (编辑距离=%d)", name, existing_name, dist
                    )
                    is_dup = True
                    break
        if not is_dup:
            kept.append(unit)

    return kept


def _edit_distance(s1: str, s2: str) -> int:
    """计算两个字符串之间的编辑距离（Levenshtein 距离）。"""
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            # 插入/删除/替换的代价
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (0 if c1 == c2 else 1)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def extract_timeline(text: str, model: str = 'deepseek-chat') -> CampaignTimeline:
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
        raise ValueError('战役文本不能为空')

    client = _build_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': _TIMELINE_SYSTEM_PROMPT},
            {'role': 'user', 'content': text},
        ],
        temperature=0.1,
        response_format={'type': 'json_object'},
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

    # 后处理：清洗 units 中的 null 字段（LLM 可能返回 null 而非空字符串）
    if 'units' in data and data['units']:
        for u in data['units']:
            if isinstance(u, dict):
                if u.get('commander') is None:
                    u['commander'] = ''
                if u.get('troop_count') is None:
                    u['troop_count'] = ''
        data['units'] = _deduplicate_unit_names(data['units'])

    # 后处理：部队状态校验
    if 'unit_states' in data and data['unit_states']:
        for us in data['unit_states']:
            if isinstance(us, dict) and us.get('description') is None:
                us['description'] = ''
        data['unit_states'] = _validate_unit_states(
            data['unit_states'],
            data.get('units', []),
            data.get('events', []),
        )

    return CampaignTimeline.model_validate(data)
