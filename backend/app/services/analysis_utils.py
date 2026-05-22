"""AI 分析结果解析工具函数 — 持仓建议识别 + 理由提取

优先匹配 AI 新 prompt 输出的标准值（加仓/减仓/持有观望/定投/清仓/观望），
旧记录回退到启发式规则。
"""

import json
from typing import Optional

# AI prompt 规范后的标准操作方向
STANDARD_ACTIONS = frozenset({"加仓", "减仓", "持有观望", "定投", "清仓", "观望"})


def _extract_fallback_reason(advice_text: str, position_action: str) -> str:
    """旧记录没有 position_reason 时，从 advice_text 提取首句作为理由"""
    if not advice_text:
        return position_action[:80] if position_action else ""
    text = advice_text.replace("\n", "。")
    for sep in ("。", "！", "？"):
        for part in text.split(sep):
            part = part.strip()
            if len(part) > 10:
                return part[:80] + ("…" if len(part) > 80 else "")
    return position_action[:80] if position_action else ""


def _calc_suggestion(position_action: str, shares: float, asset_type: str) -> str:
    """根据标准化的 position_action 计算具体份额建议"""
    unit = "份" if asset_type == "fund" else "股"

    if position_action == "加仓" and shares > 0:
        suggested = max(100, int(shares * 0.3 / 100) * 100) if shares >= 100 else max(1, int(shares * 0.3))
        return f"加仓 {suggested}{unit}"
    elif position_action == "减仓" and shares > 0:
        suggested = max(100, int(shares * 0.5 / 100) * 100) if shares >= 100 else max(1, int(shares * 0.5))
        return f"减仓 {suggested}{unit}"
    elif position_action == "清仓" and shares > 0:
        return "建议清仓"
    elif position_action == "定投":
        return "定投"
    else:  # 持有观望 / 观望
        return "观望"


def _heuristic_suggestion(position_action: str, advice_text: str, shares: float, asset_type: str) -> str:
    """旧格式启发式解析——为已存的历史分析记录保留兼容"""
    has_no_op = any(p in position_action for p in ("不进行", "不建议", "无需操作"))
    has_compound = "加减仓" in position_action

    conditional_markers = ("若", "如果", "一旦", "如")
    is_conditional = False
    if not has_no_op:
        for marker in conditional_markers:
            if marker in position_action and ("加仓" in position_action or "减仓" in position_action):
                is_conditional = True
                break
        if "可考虑" in position_action and ("加仓" in position_action or "减仓" in position_action):
            is_conditional = True

    has_add = not has_no_op and "加仓" in position_action and not has_compound and not is_conditional
    has_reduce = not has_no_op and "减仓" in position_action and not has_compound and not is_conditional
    has_sell = "清仓" in position_action and "不清仓" not in position_action and "不清" not in position_action
    has_dca = "定投" in position_action or ("定投" in advice_text and not has_add and not has_reduce)
    unit = "份" if asset_type == "fund" else "股"

    if is_conditional and not has_no_op:
        return "观望"
    elif has_add and shares > 0:
        suggested = max(100, int(shares * 0.3 / 100) * 100) if shares >= 100 else max(1, int(shares * 0.3))
        return f"加仓 {suggested}{unit}"
    elif (has_reduce or "止盈" in position_action) and shares > 0:
        suggested = max(100, int(shares * 0.5 / 100) * 100) if shares >= 100 else max(1, int(shares * 0.5))
        return f"减仓 {suggested}{unit}"
    elif has_sell and shares > 0:
        return "建议清仓"
    elif has_dca:
        return "定投"
    elif "持有" in position_action or "观望" in position_action or not position_action:
        return "观望"
    else:
        return position_action


def parse_suggestion(
    detail_json_str: Optional[str],
    shares: float,
    asset_type: str,
) -> tuple[str, str, str, str, str]:
    """
    从 detail_json 解析 AI 建议，返回 5 元组：
    (position_action, buy_zone, sell_zone, suggestion_label, reason)

    优先匹配 AI 新 prompt 的标准输出，旧记录回退到启发式规则。
    """
    if not detail_json_str:
        return ("", "", "", "", "")

    try:
        detail = json.loads(detail_json_str)
        ai_report = detail.get("ai_report") or {}
        position_action = (ai_report.get("position_action") or "").strip()
        buy_zone = (ai_report.get("buy_zone") or "").strip()
        sell_zone = (ai_report.get("sell_zone") or "").strip()
        advice_text = (ai_report.get("advice") or "").strip()
        position_reason = (ai_report.get("position_reason") or "").strip()
    except (json.JSONDecodeError, TypeError, AttributeError):
        return ("", "", "", "", "")

    # ── 标准值匹配（新 prompt 输出） ──
    if position_action in STANDARD_ACTIONS:
        suggestion = _calc_suggestion(position_action, shares, asset_type)
        reason = position_reason or _extract_fallback_reason(advice_text, position_action)
        return (position_action, buy_zone, sell_zone, suggestion, reason)

    # ── 旧记录启发式回退 ──
    suggestion = _heuristic_suggestion(position_action, advice_text, shares, asset_type)
    reason = _extract_fallback_reason(advice_text, position_action)
    return (position_action, buy_zone, sell_zone, suggestion, reason)
