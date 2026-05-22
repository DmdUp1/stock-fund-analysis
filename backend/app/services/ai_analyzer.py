"""AI 分析器 —— 调用 DeepSeek，按资产类型和投资风格生成报告"""

import json
from typing import Optional

from openai import AsyncOpenAI

from app.utils.config import settings
from app.utils.logger import logger
from app.models.schemas import MultiDimAnalysis, AIReport


async def generate_report(analysis: MultiDimAnalysis) -> AIReport:
    """根据多维分析结果和资产类型，生成个性化 AI 报告"""
    client = AsyncOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )

    asset_label = "股票" if analysis.asset_type == "stock" else "基金"
    tech = analysis.technical_indicators
    percentile_252 = analysis.price_percentile or tech.get("price_percentile_252d", 0.5)

    # ── 根据不同资产类型构造不同 prompt ──
    if analysis.asset_type == "fund":
        prompt = _build_fund_prompt(analysis, tech, percentile_252, asset_label)
    else:
        prompt = _build_stock_prompt(analysis, tech, percentile_252, asset_label)

    try:
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("AI 返回空内容")
        data = json.loads(content)
        return AIReport(
            code=analysis.code,
            name=analysis.name,
            asset_type=analysis.asset_type,
            style=analysis.style or settings.INVESTMENT_STYLE,
            summary=data.get("summary", ""),
            technical_view=data.get("technical_view", ""),
            fundamental_view=data.get("fundamental_view", ""),
            sentiment_view=data.get("sentiment_view", ""),
            risk_warning=data.get("risk_warning", ""),
            opportunity=data.get("opportunity", ""),
            advice=data.get("advice", ""),
            buy_zone=data.get("buy_zone", ""),
            sell_zone=data.get("sell_zone", ""),
            position_action=data.get("position_action", ""),
            position_reason=data.get("position_reason", ""),
            strategy=data.get("strategy", ""),
            personal_advice=data.get("personal_advice", ""),
            market_advice=data.get("market_advice", ""),
        )
    except Exception as e:
        logger.error(f"[ai_analyzer] DeepSeek 调用失败: {e}")
        return _fallback_report(analysis, asset_label)


def _build_stock_prompt(analysis: MultiDimAnalysis, tech: dict, pct: float, label: str) -> str:
    percentile_str = f"近252日价格分位: {pct:.1%}"
    macd = tech.get("macd", {})
    boll = tech.get("bollinger", {})

    # 持仓上下文
    position_block = ""
    if analysis.shares > 0 and analysis.cost_price > 0:
        current_price = tech.get("close", 0)
        cost_total = analysis.cost_price * analysis.shares
        current_total = current_price * analysis.shares if current_price else 0
        pl_pct = ((current_price - analysis.cost_price) / analysis.cost_price * 100) if analysis.cost_price > 0 else 0
        holding_days = analysis.technical_indicators.get("holding_days", 0)
        position_block = f"""
【您的实际持仓】（请重点结合以下持仓数据给出操作建议）
- 持仓数量: {analysis.shares:.0f}股
- 持仓成本价: ¥{analysis.cost_price:.4f}
- 持仓总成本: ¥{cost_total:.2f}
- 当前市值: ¥{current_total:.2f}
- 持仓盈亏: {pl_pct:+.2f}%
- 持有时长: {holding_days}天
"""

    return f"""你是一位专注于{analysis.style or settings.INVESTMENT_STYLE}的资深投资分析师，拥有15年证券市场实战经验。
请基于以下数据，对{label} {analysis.code} ({analysis.name}) 进行全方位分析，以JSON格式输出。

【技术面】
- 最新收盘价: {tech.get("close", "N/A")}
- 涨跌幅: {tech.get("change_pct", "N/A")}%
- MA5: {tech.get("ma5", "N/A")} | MA10: {tech.get("ma10", "N/A")} | MA20: {tech.get("ma20", "N/A")} | MA60: {tech.get("ma60", "N/A")}
- RSI(14): {tech.get("rsi", "N/A")}
- MACD: DIF={macd.get("dif", "N/A")} DEA={macd.get("dea", "N/A")} HIST={macd.get("hist", "N/A")}
- 布林带: 上轨={boll.get("upper", "N/A")} 中轨={boll.get("mid", "N/A")} 下轨={boll.get("lower", "N/A")}
- 年化波动率: {tech.get("volatility", "N/A")}
{percentile_str}

【基本面】
{json.dumps(analysis.fundamental, ensure_ascii=False, indent=2) if analysis.fundamental else "暂无数据"}

【市场情绪】
{analysis.sentiment_label} (得分: {analysis.sentiment_score})
{position_block}
请严格按照以下JSON格式输出，每项内容需专业、具体、可操作：
{{
  "summary": "一句话整体判断，含当前价格水平定位",
  "technical_view": "详细技术面分析：均线排列、MACD形态、RSI超买超卖、布林带位置、支撑位/压力位具体价格",
  "fundamental_view": "基本面分析：PE/PB估值水平、行业对比、业绩看点",
  "sentiment_view": "市场情绪与资金面解读",
  "risk_warning": "具体风险提示：下行关键支撑位、可能的风险事件",
  "opportunity": "潜在机会：上行目标位、催化剂因素",
  "advice": "综合投资建议",
  "buy_zone": "适宜买入价格区间（明确价格范围，如'XX元-XX元'），若当前不在买入区间则说明原因",
  "sell_zone": "止盈卖出价格区间（明确价格范围，如'XX元-XX元'），以及止损价位",
  "position_action": "【关键】必须严格从以下选项中选择一项：'加仓'/'减仓'/'持有观望'/'定投'/'清仓'/'观望'，不要输出其他值",
  "position_reason": "简述给出此操作建议的核心原因，一句话（如'估值处于低位'/'技术面超买'）",
  "strategy": "【必须结合您持仓】具体策略：单笔买入、分批建仓或定投的适用性分析，给出具体执行方案和数量安排",
  "personal_advice": "【个人持仓专属建议】基于您的持仓成本、仓位占比、持有时长、盈亏状态，给出具体操作方向、数量和建议操作时机。例如：鉴于您的持仓成本为XX元，当前价格YY元，盈亏+Z.ZZ%，建议加仓XXXX股",
  "market_advice": "【通用市场参考建议】分析所属行业/品类的整体行情趋势、估值水平、市场情绪、资金流向等，给出不依赖持仓的独立市场研判"
}}"""


def _build_fund_prompt(analysis: MultiDimAnalysis, tech: dict, pct: float, label: str) -> str:
    # 持仓上下文
    position_block = ""
    if analysis.shares > 0 and analysis.cost_price > 0:
        current_nav = tech.get("nav", 0)
        cost_total = analysis.cost_price * analysis.shares
        current_total = current_nav * analysis.shares if current_nav else 0
        pl_pct = ((current_nav - analysis.cost_price) / analysis.cost_price * 100) if analysis.cost_price > 0 else 0
        holding_days = analysis.technical_indicators.get("holding_days", 0)
        position_block = f"""
【您的实际持仓】（请重点结合以下持仓数据给出操作建议）
- 持仓份额: {analysis.shares:.0f}份
- 持仓成本净值: ¥{analysis.cost_price:.4f}
- 持仓总成本: ¥{cost_total:.2f}
- 当前市值: ¥{current_total:.2f}
- 持仓盈亏: {pl_pct:+.2f}%
- 持有时长: {holding_days}天
"""

    return f"""你是一位专注于{analysis.style or settings.INVESTMENT_STYLE}的资深基金分析师，拥有10年以上基金研究经验。
请基于以下数据，对{label} {analysis.code} ({analysis.name}) 进行全方位分析，以JSON格式输出。

【净值表现】
- 最新净值: {tech.get("nav", "N/A")}
- 累计净值: {tech.get("acc_nav", "N/A")}
- 日涨幅: {tech.get("change_pct", "N/A")}%
- 累计收益率: {tech.get("total_return", "N/A")}%
- 年化波动率: {tech.get("volatility", "N/A")}
- 最大回撤: {tech.get("max_drawdown", "N/A")}%
- 近一年净值分位: {pct:.1%}
- 近一年最高净值: {tech.get("max_nav_1y", "N/A")}
- 近一年最低净值: {tech.get("min_nav_1y", "N/A")}

【基金档案】
{json.dumps(analysis.fundamental, ensure_ascii=False, indent=2) if analysis.fundamental else "暂无数据"}

【市场情绪】
{analysis.sentiment_label} (得分: {analysis.sentiment_score})
{position_block}
请严格按照以下JSON格式输出，每项内容需专业、具体、可操作：
{{
  "summary": "一句话整体判断，含当前净值水平定位",
  "technical_view": "净值走势与回撤分析：当前处于什么位置、趋势方向、支撑位/压力位",
  "fundamental_view": "基金档案分析：基金经理、持仓结构、风格特点",
  "sentiment_view": "市场情绪与行业轮动解读",
  "risk_warning": "具体风险提示：最大回撤风险、行业集中度风险、流动性风险",
  "opportunity": "投资机会：净值回归预期、行业催化剂",
  "advice": "综合投资建议",
  "buy_zone": "适宜买入净值区间（明确净值范围），若当前不在买入区间则说明原因",
  "sell_zone": "止盈卖出净值区间（明确净值范围），以及止损策略",
  "position_action": "【关键】必须严格从以下选项中选择一项：'加仓'/'减仓'/'持有观望'/'定投'/'清仓'/'观望'，不要输出其他值",
  "position_reason": "简述给出此操作建议的核心原因，一句话（如'净值处于低位'/'回撤风险较大'）",
  "strategy": "【必须结合您持仓】具体策略：单笔买入、分批建仓或定投的适用性分析，给出具体执行方案和数量安排",
  "personal_advice": "【个人持仓专属建议】基于您的持仓成本、仓位占比、持有时长、盈亏状态，给出具体操作方向、数量和建议操作时机",
  "market_advice": "【通用市场参考建议】分析所属行业/品类的整体行情趋势、估值水平、市场情绪、资金流向等，给出不依赖持仓的独立市场研判"
}}"""


def _fallback_report(analysis: MultiDimAnalysis, asset_label: str) -> AIReport:
    """DeepSeek 不可用时的降级规则报告"""
    tech = analysis.technical_indicators

    if analysis.asset_type == "fund":
        nav = tech.get("nav", "N/A")
        dd = tech.get("max_drawdown", 0)
        ret = tech.get("total_return", 0)

        if dd < -20:
            risk = f"最大回撤已达 {dd}%，回撤幅度较大"
        else:
            risk = f"最大回撤 {dd}%，处于可控范围"

        return AIReport(
            code=analysis.code,
            name=analysis.name,
            asset_type="fund",
            style=analysis.style or settings.INVESTMENT_STYLE,
            summary=f"{analysis.code} 净值分析完毕，最新净值: {nav}",
            technical_view=f"累计收益率: {ret}%，最大回撤: {dd}%。{risk}。",
            fundamental_view="基金详细数据暂不可用（AI降级模式）",
            sentiment_view="市场情绪数据暂不可用",
            risk_warning=risk + "。AI分析服务暂不可用，本报告基于规则生成，仅供参考。",
            opportunity="请稍后重试以获取完整的AI驱动分析",
            advice="建议结合个人投资风格和仓位情况谨慎决策。",
            buy_zone="",
            sell_zone="",
            position_action="观望",
            strategy="AI分析服务暂不可用，建议后续重新获取完整分析报告后再决策。",
            personal_advice="AI分析服务暂不可用，无法生成个人持仓建议",
            market_advice="AI分析服务暂不可用，无法生成市场参考建议",
        )

    # 股票降级
    pct = analysis.price_percentile or tech.get("price_percentile_252d", 0.5)
    rsi = tech.get("rsi", 50)

    if rsi > 70:
        view = "RSI > 70，处于超买区间，短期回调风险较大"
    elif rsi < 30:
        view = "RSI < 30，处于超卖区间，可能存在反弹机会"
    else:
        view = f"RSI = {rsi}，处于中性区间，趋势不明显"

    if pct > 0.8:
        percentile_view = f"股价处于近一年 {pct:.0%} 分位，处于相对高位"
    elif pct < 0.2:
        percentile_view = f"股价处于近一年 {pct:.0%} 分位，处于相对低位"
    else:
        percentile_view = f"股价处于近一年 {pct:.0%} 分位，估值相对合理"

    return AIReport(
        code=analysis.code,
        name=analysis.name,
        asset_type="stock",
        style=analysis.style or settings.INVESTMENT_STYLE,
        summary=f"{analysis.code} 技术面分析完毕",
        technical_view=f"{view}。{percentile_view}。",
        fundamental_view="基本面数据暂不可用（AI降级模式）",
        sentiment_view=f"市场情绪: {analysis.sentiment_label}",
        risk_warning="AI分析服务暂不可用，本报告基于规则生成，仅供参考",
        opportunity="请稍后重试以获取完整的AI驱动分析",
        advice="建议结合个人投资风格和仓位情况谨慎决策。",
        buy_zone="",
        sell_zone="",
        position_action="观望",
        strategy="AI分析服务暂不可用，建议后续重新获取完整分析报告后再决策。",
        personal_advice="AI分析服务暂不可用，无法生成个人持仓建议",
        market_advice="AI分析服务暂不可用，无法生成市场参考建议",
    )
