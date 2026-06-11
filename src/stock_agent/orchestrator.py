"""오케스트레이터 — LangGraph 파이프라인 구성 및 실행.

데이터 수집 → 시황 분석 → 섹터 추천 → 종목 추천 → 리포트 생성 → 메일 발송
순서로 6개 에이전트를 연결하고, 매일 정해진 시각에 실행한다.
"""

from __future__ import annotations

import datetime as dt
import logging

from langgraph.graph import END, START, StateGraph

from .agents import (
    data_collector,
    mailer,
    market_analyst,
    report_generator,
    sector_selector,
    stock_selector,
)
from .config import Config
from .state import PipelineState

log = logging.getLogger(__name__)


def build_graph(cfg: Config, dry_run: bool = False):
    g = StateGraph(PipelineState)

    g.add_node("collect", lambda s: data_collector.run(s, cfg))
    g.add_node("analyze", lambda s: market_analyst.run(s, cfg))
    g.add_node("sectors", lambda s: sector_selector.run(s, cfg))
    g.add_node("stocks", lambda s: stock_selector.run(s, cfg))
    g.add_node("report", lambda s: report_generator.run(s, cfg))
    g.add_node("mail", lambda s: mailer.run(s, cfg, dry_run=dry_run))

    g.add_edge(START, "collect")
    g.add_edge("collect", "analyze")
    g.add_edge("analyze", "sectors")
    g.add_edge("sectors", "stocks")
    g.add_edge("stocks", "report")
    g.add_edge("report", "mail")
    g.add_edge("mail", END)
    return g.compile()


def run_once(cfg: Config, dry_run: bool = False) -> PipelineState:
    app = build_graph(cfg, dry_run=dry_run)
    today = dt.date.today().strftime("%Y-%m-%d")
    init: PipelineState = {"as_of": today, "errors": []}
    log.info("파이프라인 시작 (as_of=%s, dry_run=%s)", today, dry_run)
    final: PipelineState = app.invoke(init)
    n_sectors = len(final.get("sectors", []))
    n_picks = len(final.get("picks", []))
    log.info("파이프라인 완료: 섹터 %d, 종목 %d, 메일 %s", n_sectors, n_picks, final.get("mail_result"))
    for e in final.get("errors", []):
        log.warning("경고: %s", e)
    return final
