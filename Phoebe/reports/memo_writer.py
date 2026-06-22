from __future__ import annotations

from typing import Dict, Optional, Tuple

from sportmira.odds.odds_math import expected_value
from sportmira.schemas import OddsSelection, ProbabilityEstimate, ResearchPackage


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def _edge(model_prob: float, odds: Optional[float]) -> str:
    if odds is None:
        return "-"
    try:
        return f"{expected_value(model_prob, odds) * 100:.1f}% EV"
    except Exception:
        return "-"


def _odds_lookup(package: ResearchPackage) -> Dict[Tuple[str, str, Optional[float]], OddsSelection]:
    lookup: Dict[Tuple[str, str, Optional[float]], OddsSelection] = {}
    if not package.odds_snapshot:
        return lookup
    for selection in package.odds_snapshot.selections:
        lookup[(selection.market, selection.selection, selection.line)] = selection
    return lookup


def _source_id(package: ResearchPackage, source_name: str) -> str:
    for item in package.evidence:
        if item.source_name == source_name:
            return item.id
    return "inference"


def write_memo(package: ResearchPackage) -> str:
    match = package.match
    model = package.model_output
    card = package.betting_card
    odds_lookup = _odds_lookup(package)
    top_score = model.likely_scorelines[0]["score"] if model and model.likely_scorelines else "未定"
    if card and card.recommendations:
        best_market = card.recommendations[0].bet
        stake_line = ", ".join(f"{r.bet}: {r.stake:g}{r.unit}" for r in card.recommendations)
        main_judgment = "小注研究型介入，严格刷新阵容/赔率。"
    else:
        best_market = "No bet / 等待更清晰赔率"
        stake_line = "0u"
        main_judgment = "当前数据或价格不足，不建议为了下单而下单。"
    lines = [
        f"# SportMira Match Betting Memo: {match.raw_match}",
        "",
        "## 1. 直接结论",
        "",
        f"* 主判断：{main_judgment}（judgment，不是 guaranteed betting advice）",
        f"* 最佳盘口：{best_market}",
        "* 不建议买的盘口：没有模型覆盖、没有赔率、或 EV 不足的盘口。",
        f"* 建议仓位：{stake_line}",
        f"* 预测比分：{top_score}（inference: Poisson baseline）",
        f"* stale_after：{package.stale_after}",
        "",
        "## 2. 当前盘口快照",
        "",
        "| Market | Selection | Odds | Implied Prob | No-vig Prob | Notes |",
        "|---|---:|---:|---:|---:|---|",
    ]
    if package.odds_snapshot and package.odds_snapshot.selections:
        for selection in package.odds_snapshot.selections:
            lines.append(
                f"| {selection.market} | {selection.selection}{' ' + str(selection.line) if selection.line is not None else ''} | "
                f"{selection.odds:.2f} | {_pct(selection.implied_probability)} | {_pct(selection.no_vig_probability)} | "
                f"{selection.notes or package.odds_snapshot.source_name} |"
            )
    else:
        lines.append("| missing | - | - | - | - | 没有可用 odds snapshot；不能推荐无赔率市场。 |")
    lines.extend(
        [
            "",
            "## 3. 球队近况与打法",
            "",
            f"* {match.home_team}：last 5 matches / goals / cards / formation 未可靠结构化解析；见 {_source_id(package, 'team_form')}。模型只使用低置信 baseline 或市场先验。",
            f"* {match.away_team}：last 5 matches / goals / cards / formation 未可靠结构化解析；见 {_source_id(package, 'team_form')}。不得把缺失数据当事实。",
            "* physicality / set-piece reliance：当前为 inference unavailable，需赛前新闻和阵容确认。",
            "",
            "## 4. 裁判报告",
            "",
            f"* referee identity：未确认；见 {_source_id(package, 'referee_profile')}。",
            "* yellow/red/penalty tendency：数据缺失时只使用 cards baseline，置信度 low。",
            "* physical contact tolerance：inference unavailable until referee announced。",
            "",
            "## 5. 战术对位",
            "",
            "* 控球权：inference，缺少可靠阵容和近期打法数据时不做强断言。",
            "* high-quality chances：以 Poisson baseline + market prior 近似，不等于真实 xG。",
            "* transition risk：若首发边后卫/中卫组合变化，必须刷新。",
            "* set-piece mismatch：当前无事实来源支持，保持 low confidence。",
            "* late-game paths：早球会推高 over/open-game path；长时间 0-0 会强化 draw/under 相关性。",
            "",
            "## 6. 模型概率",
            "",
            "| Market | Model Prob | Market Implied Prob | Edge | Confidence |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    if model and model.estimates:
        for estimate in model.estimates[:18]:
            odds = odds_lookup.get((estimate.market, estimate.selection, estimate.line))
            lines.append(
                f"| {estimate.market} {estimate.selection}{' ' + str(estimate.line) if estimate.line is not None else ''} | "
                f"{_pct(estimate.probability)} | {_pct(odds.implied_probability if odds else None)} | "
                f"{_edge(estimate.probability, odds.odds if odds else None)} | {estimate.confidence} |"
            )
    else:
        lines.append("| missing | - | - | - | low |")
    lines.extend(
        [
            "",
            "## 7. 投注建议",
            "",
            "| Bet | Odds | Stake | Reason | Main Risk |",
            "|---|---:|---:|---|---|",
        ]
    )
    if card and card.recommendations:
        for rec in card.recommendations:
            lines.append(
                f"| {rec.bet} | {rec.odds:.2f} | {rec.stake:g}{rec.unit} | {rec.reason} | {rec.main_risk} |"
            )
    else:
        lines.append("| No bet | - | 0u | 没有满足赔率、EV、置信度和相关性约束的投注。 | 强行下单会把 research 变成猜测。 |")
    lines.extend(
        [
            "",
            "## 8. 相关性和风险",
            "",
        ]
    )
    if card and card.warnings:
        lines.extend(f"* {warning}" for warning in card.warnings)
    else:
        lines.append("* 当前投注卡无集中敞口；若增加 draw/under/correct score，需重新检查相关性。")
    lines.extend(
        [
            "* what scoreline kills the card：与推荐方向相反的早球、红牌或战术退守会破坏模型假设。",
            "* early event invalidates thesis：首发重大变化、盘口大幅移动、早红牌、早 penalty。",
            "",
            "## 9. must_refresh_if",
            "",
        ]
    )
    lines.extend(f"* {item}" for item in package.must_refresh_if)
    lines.extend(
        [
            "",
            "## 10. Evidence Log",
            "",
            "| id | claim | source_name | source_url | accessed_at | confidence | used_in |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in package.evidence:
        claim = item.claim.replace("|", "/")
        lines.append(
            f"| {item.id} | {claim} | {item.source_name} | {item.source_url} | {item.accessed_at} | {item.confidence} | {item.used_in} |"
        )
    lines.append("")
    lines.append("> SportMira 只提供研究备忘录，不自动下注，不保证结果。")
    return "\n".join(lines)
