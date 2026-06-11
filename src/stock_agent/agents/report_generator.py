"""Agent 5 — 종목별 리포트 생성 (HTML + 차트)."""

from __future__ import annotations

import logging

from jinja2 import Template

from ..config import Config
from ..data import DataProvider
from ..llm import complete
from ..state import MarketView, PipelineState, StockPick, StockReport

log = logging.getLogger(__name__)

SYSTEM = (
    "너는 증권사 리서치 애널리스트다. 주어진 종목 지표와 시황을 근거로 "
    "투자 참고용 코멘트를 3~4문장으로 한국어로 작성한다. 단정적 수익 보장 표현은 피하고 "
    "단기/중기 관점과 리스크를 균형있게 서술한다."
)

STOCK_TEMPLATE = Template(
    """
<div style="font-family:Apple SD Gothic Neo,Malgun Gothic,sans-serif;border:1px solid #e5e7eb;border-radius:10px;padding:18px;margin:14px 0;">
  <h2 style="margin:0 0 4px;font-size:18px;">{{ p.name }} <span style="color:#6b7280;font-size:13px;">({{ p.ticker }}) · {{ p.sector }}</span></h2>
  <div style="font-size:13px;color:#374151;margin-bottom:10px;">
    종가 <b>{{ "{:,.0f}".format(p.last_close) }}</b>원
    · 1D <b style="color:{{ '#dc2626' if p.pct_1d>=0 else '#2563eb' }};">{{ p.pct_1d }}%</b>
    · 5D {{ p.pct_5d }}% · 20D {{ p.pct_20d }}%
    · RSI {{ p.rsi14 }}
    · 관점 <b>{{ '단기' if p.horizon=='short' else '중기' }}</b>
  </div>
  {% if chart_cid %}<img src="cid:{{ chart_cid }}" alt="chart" style="width:100%;max-width:560px;border:1px solid #f3f4f6;border-radius:6px;"/>{% endif %}
  <p style="font-size:14px;line-height:1.6;color:#111827;">{{ summary }}</p>
  <div style="font-size:12px;color:#6b7280;">
    <div>📈 추천 근거: {{ p.rationale }}</div>
    <div>⚠️ 리스크: {{ p.risk }}</div>
  </div>
</div>
"""
)


def _make_chart(provider: DataProvider, p: StockPick, out_dir) -> str | None:
    df = provider.stock_ohlcv(p.ticker)
    if df is None or "Close" not in df.columns or len(df) < 30:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        close = df["Close"].dropna().tail(120)
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        fig, ax = plt.subplots(figsize=(6.2, 2.6), dpi=110)
        ax.plot(close.index, close.values, color="#111827", linewidth=1.2, label="Close")
        ax.plot(ma20.index, ma20.values, color="#f59e0b", linewidth=0.9, label="MA20")
        ax.plot(ma60.index, ma60.values, color="#2563eb", linewidth=0.9, label="MA60")
        ax.legend(fontsize=7, loc="upper left")
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.2)
        fig.tight_layout()
        path = out_dir / f"chart_{p.ticker}.png"
        fig.savefig(path)
        plt.close(fig)
        return str(path)
    except Exception as e:  # noqa: BLE001
        log.warning("차트 생성 실패 %s: %s", p.ticker, e)
        return None


def _summary(cfg: Config, p: StockPick, view: MarketView | None) -> str:
    stance = view.stance if view else "neutral"
    out = complete(
        cfg.llm,
        SYSTEM,
        f"종목: {p.name}({p.ticker}), 섹터: {p.sector}\n"
        f"지표: 종가 {p.last_close:,.0f}, 1D {p.pct_1d}%, 5D {p.pct_5d}%, 20D {p.pct_20d}%, "
        f"RSI {p.rsi14}, MA20상회 {p.above_ma20}, MA60상회 {p.above_ma60}, 관점 {p.horizon}\n"
        f"시장 스탠스: {stance}\n"
        "위 정보를 바탕으로 투자 참고 코멘트를 작성하라.",
    )
    if out:
        return out
    return (
        f"{p.name}은(는) 최근 5일 {p.pct_5d}%, 20일 {p.pct_20d}%의 흐름을 보이며 "
        f"{'단기 모멘텀' if p.horizon == 'short' else '중기 추세'} 관점에서 관심 구간입니다. "
        f"{p.rationale} {p.risk}."
    )


def run(state: PipelineState, cfg: Config) -> PipelineState:
    picks: list[StockPick] = state.get("picks", [])
    view = state.get("market_view")
    out_dir = cfg.output_path
    provider = DataProvider(lookback_days=cfg.market.lookback_days)

    reports: list[StockReport] = []
    for p in picks:
        chart_path = _make_chart(provider, p, out_dir) if cfg.report.include_charts else None
        chart_cid = f"chart_{p.ticker}" if chart_path else None
        summary = _summary(cfg, p, view)
        html = STOCK_TEMPLATE.render(p=p, summary=summary, chart_cid=chart_cid)
        reports.append(
            StockReport(
                ticker=p.ticker,
                name=p.name,
                sector=p.sector,
                html=html,
                summary=summary,
                chart_path=chart_path,
            )
        )

    state["reports"] = reports
    return state
