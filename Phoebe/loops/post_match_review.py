from __future__ import annotations

from typing import List, Optional, Tuple

from sportmira.schemas import PostMatchReview
from sportmira.storage.db import latest_betting_card, save_post_match_review
from sportmira.utils.time import utc_now_iso


def _parse_score(score: Optional[str]) -> Optional[Tuple[int, int]]:
    if not score:
        return None
    parts = score.replace(":", "-").split("-")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        return None


def _result_1x2(score: Tuple[int, int]) -> str:
    if score[0] > score[1]:
        return "home"
    if score[0] < score[1]:
        return "away"
    return "draw"


def _bet_won(rec: dict, score: Tuple[int, int], cards: Optional[Tuple[int, int]], red_cards: Optional[Tuple[int, int]]) -> Optional[bool]:
    market = rec.get("market")
    selection = str(rec.get("selection", "")).lower()
    line = rec.get("line")
    if line is None:
        bet = str(rec.get("bet", ""))
        for token in bet.split():
            try:
                line = float(token)
            except ValueError:
                continue
    if market == "1x2":
        return selection == _result_1x2(score)
    if market == "total_goals" and line is not None:
        total = score[0] + score[1]
        return total > float(line) if selection == "over" else total < float(line)
    if market == "total_cards" and line is not None and cards:
        total_cards = cards[0] + cards[1]
        return total_cards > float(line) if selection == "over" else total_cards < float(line)
    if market == "red_card" and red_cards:
        any_red = red_cards[0] + red_cards[1] > 0
        return any_red if selection == "yes" else not any_red
    return None


def review_match(match: str, actual_score: str, cards: Optional[str] = None, red_cards: Optional[str] = None) -> PostMatchReview:
    score = _parse_score(actual_score)
    if score is None:
        raise ValueError("actual-score must look like 2-1")
    cards_score = _parse_score(cards)
    red_score = _parse_score(red_cards)
    card = latest_betting_card(match)
    pnl: Optional[float] = 0.0 if card else None
    error_tags: List[str] = []
    notes: List[str] = []
    if not card:
        notes.append("未找到本地 betting card，无法计算跟单 P/L。")
        error_tags.append("data error")
    else:
        for rec in card.get("recommendations", []):
            won = _bet_won(rec, score, cards_score, red_score)
            stake = float(rec.get("stake", 0.0))
            odds = float(rec.get("odds", 0.0))
            if won is None:
                notes.append(f"{rec.get('bet')} 暂不支持自动赛果判定。")
                continue
            pnl += stake * (odds - 1.0) if won else -stake
        if pnl is not None and pnl < 0:
            error_tags.append("variance")
    review = PostMatchReview(
        match=match,
        actual_score=actual_score,
        actual_cards=cards,
        actual_red_cards=red_cards,
        reviewed_at=utc_now_iso(),
        one_x_two_result=_result_1x2(score),
        total_goals=score[0] + score[1],
        pnl=round(pnl, 2) if pnl is not None else None,
        error_tags=error_tags or ["no major error classified"],
        notes=notes or ["复盘已保存；请结合比赛过程标注 tactical/referee/correlation error。"],
    )
    save_post_match_review(review)
    return review
