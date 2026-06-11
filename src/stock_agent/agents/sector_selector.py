"""Agent 3 — 섹터 추천 (상위 N개)."""

from __future__ import annotations

from ..config import Config
from ..state import PipelineState, SectorPick


def run(state: PipelineState, cfg: Config) -> PipelineState:
    md = state.get("market_data", {})
    sectors = md.get("sectors")
    errors = list(state.get("errors", []))

    if sectors is None or sectors.empty:
        errors.append("섹터 데이터가 비어 있어 섹터 추천 불가")
        state["sectors"] = []
        state["errors"] = errors
        return state

    df = sectors.copy()
    # 종합 점수: 모멘텀(0~100) 70% + 시장폭(0~1→0~100) 30%
    df["score"] = 0.7 * df["mom_score"] + 0.3 * (df["breadth_ma20"] * 100.0)
    df = df.sort_values("score", ascending=False).head(cfg.recommend.num_sectors)

    picks: list[SectorPick] = []
    for _, r in df.iterrows():
        picks.append(
            SectorPick(
                name=str(r["Sector"]),
                score=round(float(r["score"]), 2),
                momentum_20d=round(float(r["pct_20d"]), 2),
                rationale=(
                    f"20일 모멘텀 {round(float(r['pct_20d']), 1)}%, "
                    f"20일선 상회 비중 {round(float(r['breadth_ma20']) * 100, 0):.0f}%, "
                    f"구성 {int(r['n'])}종목 기준 상대강도 상위."
                ),
            )
        )

    state["sectors"] = picks
    state["errors"] = errors
    return state
