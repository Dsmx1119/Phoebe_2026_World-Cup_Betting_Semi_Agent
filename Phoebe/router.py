from __future__ import annotations

from typing import Optional

from sportmira.schemas import RouteDecision


def route_task(
    text: str = "",
    match: Optional[str] = None,
    screenshot: Optional[str] = None,
    bankroll: Optional[float] = None,
    max_bets: Optional[int] = None,
    review: bool = False,
) -> RouteDecision:
    lowered = (text or "").lower()
    reasons = []
    if review or "复盘" in lowered or "review" in lowered:
        return RouteDecision("post_match_review", "high", ["用户提供赛后结果或要求复盘"], needs_review=True, needs_research=False)
    if screenshot and not match and not bankroll:
        return RouteDecision("odds_only", "high", ["用户提供盘口截图但未指定完整赛前研究输入"], needs_odds=True, needs_research=False)
    if bankroll and max_bets:
        reasons.append("用户提供 bankroll/max-bets，需要输出投注卡")
        return RouteDecision("betting_card", "high", reasons, needs_odds=True, needs_research=True)
    if screenshot:
        reasons.append("用户提供盘口截图，需要解析 odds snapshot")
    if any(word in lowered for word in ["深度", "deep", "详细", "全市场"]):
        reasons.append("用户请求深度研究")
        return RouteDecision("deep_dive", "medium", reasons, needs_odds=True, needs_research=True)
    if any(word in lowered for word in ["盘口", "odds", "parse", "截图"]):
        reasons.append("用户关注盘口")
        return RouteDecision("odds_only" if not match else "standard", "medium", reasons, needs_odds=True, needs_research=bool(match))
    if any(word in lowered for word in ["看一下", "quick", "快速"]):
        reasons.append("用户请求快速概览")
        return RouteDecision("quick_map", "medium", reasons, needs_odds=False, needs_research=True)
    return RouteDecision("standard", "medium", reasons or ["默认赛前研究 memo"], needs_odds=True, needs_research=True)
