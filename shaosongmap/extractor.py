"""战役文本提取器：通过 DeepSeek API 将战役文本转换为结构化 JSON。"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from shaosongmap.models import CampaignExtract

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
6. 如果文本只描述行军不涉及战斗，campaign_name 为 null"""


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