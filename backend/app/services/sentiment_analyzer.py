"""情感分析 —— 基于新闻标题的简单 NLP 打分"""

import re
from typing import Optional

from app.utils.logger import logger

# 正面词库
_POSITIVE_WORDS = {
    "大涨", "涨停", "利好", "突破", "增长", "盈利", "创新高", "放量",
    "强势", "看好", "买入", "推荐", "升级", "中标", "签约", "合作",
    "扩产", "供不应求", "扭亏", "预增", "分红",
}

# 负面词库
_NEGATIVE_WORDS = {
    "大跌", "跌停", "利空", "减持", "亏损", "下调", "预警", "风险",
    "诉讼", "处罚", "立案", "调查", "违约", "退市", "st", "*st",
    "爆雷", "资金出走", "评级下调", "债务", "冻结",
}


def _score_text(text: str) -> float:
    """对单条文本打分 -1~1"""
    text_lower = text.lower()
    pos_count = sum(1 for w in _POSITIVE_WORDS if w in text_lower)
    neg_count = sum(1 for w in _NEGATIVE_WORDS if w in text_lower)
    total = pos_count + neg_count
    if total == 0:
        return 0.0
    return (pos_count - neg_count) / total


async def analyze_sentiment(news_list: list[dict]) -> dict:
    """分析新闻情感，返回综合得分和标签"""
    try:
        if not news_list:
            return {"score": 0.0, "label": "中性", "details": []}

        scores = []
        details = []
        for item in news_list:
            title = item.get("title") or item.get("新闻标题") or item.get("content", "")
            score = _score_text(str(title))
            scores.append(score)
            details.append({"title": str(title)[:60], "score": score})

        avg_score = sum(scores) / len(scores)

        if avg_score > 0.15:
            label = "积极"
        elif avg_score < -0.15:
            label = "消极"
        else:
            label = "中性"

        return {"score": round(avg_score, 4), "label": label, "details": details}
    except Exception as e:
        logger.error(f"[sentiment] 情感分析失败: {e}")
        return {"score": 0.0, "label": "中性", "details": []}
