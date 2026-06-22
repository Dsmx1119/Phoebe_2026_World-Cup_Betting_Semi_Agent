from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from sportmira.odds.market_normalizer import normalize_snapshot
from sportmira.odds.market_parser import parse_odds_text
from sportmira.schemas import OddsSnapshot
from sportmira.utils.time import utc_now_iso


OCR_MISSING_MESSAGE = (
    "OCR 不可用：请安装可选依赖 `pip install -e .[ocr]`，并安装系统 Tesseract。"
)


def _missing_snapshot(path: str, match_name: Optional[str], reason: str) -> OddsSnapshot:
    return OddsSnapshot(
        match=match_name,
        captured_at=utc_now_iso(),
        source_name="screenshot_ocr",
        source_url=path,
        selections=[],
        ocr_confidence=None,
        raw_text="",
        warnings=[reason],
    )


def preprocess_image_for_ocr(path: str):
    try:
        import cv2  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"OpenCV 不可用：{exc}")
    image = cv2.imread(path)
    if image is None:
        raise RuntimeError("无法读取截图文件；请确认文件存在且是有效图片。")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.fastNlMeansDenoising(resized, h=10)
    thresholded = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    return thresholded


def ocr_screenshot(
    path: str,
    match_name: Optional[str] = None,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
    output_json: Optional[str] = None,
) -> OddsSnapshot:
    try:
        import pytesseract  # type: ignore
    except Exception:
        snapshot = _missing_snapshot(path, match_name, OCR_MISSING_MESSAGE)
        if output_json:
            write_snapshot_json(snapshot, output_json)
        return snapshot
    if not Path(path).exists():
        snapshot = _missing_snapshot(path, match_name, "截图文件不存在。")
        if output_json:
            write_snapshot_json(snapshot, output_json)
        return snapshot
    try:
        processed = preprocess_image_for_ocr(path)
        data = pytesseract.image_to_data(
            processed,
            lang="chi_sim+eng",
            output_type=pytesseract.Output.DICT,
            config="--psm 6",
        )
        words = []
        confidences = []
        for text, confidence in zip(data.get("text", []), data.get("conf", [])):
            if text and str(text).strip():
                words.append(str(text).strip())
                try:
                    conf = float(confidence)
                    if conf >= 0:
                        confidences.append(conf)
                except Exception:
                    pass
        raw_text = "\n".join(words)
        avg_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    except Exception as exc:
        snapshot = _missing_snapshot(path, match_name, f"OCR 处理失败：{exc}")
        if output_json:
            write_snapshot_json(snapshot, output_json)
        return snapshot
    snapshot = parse_odds_text(
        raw_text,
        match_name=match_name,
        home_team=home_team,
        away_team=away_team,
        source_name="screenshot_ocr",
        source_url=path,
        ocr_confidence=avg_confidence,
    )
    if avg_confidence < 0.60:
        snapshot.warnings.append("OCR 置信度偏低；请人工确认盘口、选项和赔率。")
    normalize_snapshot(snapshot)
    if output_json:
        write_snapshot_json(snapshot, output_json)
    return snapshot


def write_snapshot_json(snapshot: OddsSnapshot, output_path: str = "odds_snapshot.json") -> None:
    Path(output_path).write_text(json.dumps(snapshot.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
