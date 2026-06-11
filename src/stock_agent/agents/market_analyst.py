"""Agent 2 — 시황 분석 (단기/중기)."""

from __future__ import annotations

import json

from ..config import Config
from ..llm import complete
from ..state import MarketView, PipelineState

SYSTEM = (
    "너는 한국 주식시장 시황 분석가다. 주어진 지수 지표를 바탕으로 "
    "단기(1~5일)와 중기(1~3개월) 관점의 시황을 간결하고 전문적으로 한국어로 요약한다. "
    "과장 없이 데이터 근거 중심으로 서술한다."
)


def _rule_stance(kospi_20d: float, breadth: float) -> str:
    if kospi_20d > 3 and breadth > 0.55:
        return "bullish"
    if kospi_20d < -3 and breadth < 0.45:
        return "bearish"
    return "neutral"


def run(state: PipelineState, cfg: Config) -> PipelineState:
    md = state.get("market_data", {})
    indices = md.get("indices", {})
    stocks = md.get("stocks")

    kospi = indices.get("KOSPI", {})
    kosdaq = indices.get("KOSDAQ", {})
    breadth = float(stocks["above_ma20"].mean()) if stocks is not None and not stocks.empty else 0.5

    stance = _rule_stance(kospi.get("pct_20d", 0.0), breadth)

    metrics = {
        "KOSPI": {k: round(kospi.get(k, 0.0), 2) for k in ("pct_1d", "pct_5d", "pct_20d", "pct_60d")},
        "KOSDAQ": {k: round(kosdaq.get(k, 0.0), 2) for k in ("pct_1d", "pct_5d", "pct_20d", "pct_60d")},
        "breadth_above_ma20": round(breadth, 3),
        "rule_stance": stance,
    }

    short_term = (
        f"KOSPI 1일 {metrics['KOSPI']['pct_1d']}%, 5일 {metrics['KOSPI']['pct_5d']}%. "
        f"KOSDAQ 1일 {metrics['KOSDAQ']['pct_1d']}%. "
        f"시장 폭(20일선 상회 비중) {round(breadth * 100, 1)}%."
    )
    mid_term = (
        f"KOSPI 20일 {metrics['KOSPI']['pct_20d']}%, 60일 {metrics['KOSPI']['pct_60d']}%. "
        f"중기 추세 스탠스: {stance}."
    )
    commentary = ""

    llm_out = complete(
        cfg.llm,
        SYSTEM,
        "다음 지표를 바탕으로 단기/중기 시황과 한줄 코멘트를 JSON으로 작성하라. "
        'JSON 형식: {"short_term": "...", "mid_term": "...", "commentary": "..."}\n\n'
        f"지표: {json.dumps(metrics, ensure_ascii=False)}",
    )
    if llm_out:
        try:
            cleaned = llm_out.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            parsed = json.loads(cleaned)
            short_term = parsed.get("short_term", short_term)
            mid_term = parsed.get("mid_term", mid_term)
            commentary = parsed.get("commentary", "")
        except Exception:
            commentary = llm_out[:500]

    view = MarketView(
        as_of=state.get("as_of", ""),
        short_term=short_term,
        mid_term=mid_term,
        stance=stance,
        kospi_pct_1d=kospi.get("pct_1d", 0.0),
        kospi_pct_20d=kospi.get("pct_20d", 0.0),
        kosdaq_pct_1d=kosdaq.get("pct_1d", 0.0),
        kosdaq_pct_20d=kosdaq.get("pct_20d", 0.0),
        commentary=commentary,
    )
    state["market_view"] = view
    return state
