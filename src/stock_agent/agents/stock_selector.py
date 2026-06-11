"""Agent 4 — 종목 추천 (섹터별 N개)."""

from __future__ import annotations

import pandas as pd

from ..config import Config
from ..state import PipelineState, StockPick


def _stock_score(r: pd.Series) -> float:
    score = r["mom_score"]
    if r["above_ma20"]:
        score += 5
    if r["above_ma60"]:
        score += 5
    # 과열(RSI>75) 감점, 과매도 반등 여지(35~55) 소폭 가점
    rsi = r["rsi14"]
    if rsi > 75:
        score -= 10
    elif 35 <= rsi <= 55:
        score += 3
    return float(score)


def _horizon(r: pd.Series) -> str:
    if r["pct_5d"] >= r["pct_60d"] / 12 and r["pct_5d"] > 0:
        return "short"
    if r["above_ma60"] and r["pct_60d"] > 0:
        return "mid"
    return "short"


def run(state: PipelineState, cfg: Config) -> PipelineState:
    md = state.get("market_data", {})
    stocks = md.get("stocks")
    sector_picks = state.get("sectors", [])
    errors = list(state.get("errors", []))

    if stocks is None or stocks.empty or not sector_picks:
        errors.append("종목 데이터/섹터 추천이 없어 종목 추천 불가")
        state["picks"] = []
        state["errors"] = errors
        return state

    df = stocks.copy()
    df["sscore"] = df.apply(_stock_score, axis=1)

    picks: list[StockPick] = []
    for sp in sector_picks:
        sub = df[df["Sector"] == sp.name].sort_values("sscore", ascending=False)
        sub = sub.head(cfg.recommend.stocks_per_sector)
        for _, r in sub.iterrows():
            picks.append(
                StockPick(
                    ticker=str(r["Code"]),
                    name=str(r["Name"]),
                    sector=sp.name,
                    score=round(float(r["sscore"]), 2),
                    last_close=float(r["last_close"]),
                    pct_1d=round(float(r["pct_1d"]), 2),
                    pct_5d=round(float(r["pct_5d"]), 2),
                    pct_20d=round(float(r["pct_20d"]), 2),
                    rsi14=round(float(r["rsi14"]), 1),
                    above_ma20=bool(r["above_ma20"]),
                    above_ma60=bool(r["above_ma60"]),
                    horizon=_horizon(r),
                    rationale=(
                        f"5일 {round(float(r['pct_5d']), 1)}% / 20일 {round(float(r['pct_20d']), 1)}% 모멘텀, "
                        f"RSI {round(float(r['rsi14']), 0):.0f}, "
                        f"{'20·60일선 상회' if r['above_ma20'] and r['above_ma60'] else '추세 회복 구간'}."
                    ),
                    risk=(
                        "단기 과열 가능(RSI 높음)" if r["rsi14"] > 70 else "추세 이탈 시 손절 기준 관리 필요"
                    ),
                )
            )

    state["picks"] = picks
    state["errors"] = errors
    return state
