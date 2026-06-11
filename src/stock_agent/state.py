"""에이전트 간 공유되는 데이터 모델 및 LangGraph 파이프라인 상태."""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class MarketView(BaseModel):
    """Agent 2 산출물: 단기/중기 시황 분석."""

    as_of: str = Field(description="분석 기준일 (YYYY-MM-DD)")
    short_term: str = Field(description="단기(1~5일) 시황 요약")
    mid_term: str = Field(description="중기(1~3개월) 시황 요약")
    stance: str = Field(description="종합 스탠스: bullish / neutral / bearish")
    kospi_pct_1d: float = 0.0
    kospi_pct_20d: float = 0.0
    kosdaq_pct_1d: float = 0.0
    kosdaq_pct_20d: float = 0.0
    commentary: str = ""


class SectorPick(BaseModel):
    """Agent 3 산출물: 추천 섹터 1건."""

    name: str
    score: float
    momentum_20d: float = 0.0
    rationale: str = ""


class StockPick(BaseModel):
    """Agent 4 산출물: 추천 종목 1건."""

    ticker: str
    name: str
    sector: str
    score: float
    last_close: float = 0.0
    pct_1d: float = 0.0
    pct_5d: float = 0.0
    pct_20d: float = 0.0
    rsi14: float = 0.0
    above_ma20: bool = False
    above_ma60: bool = False
    horizon: str = "short"  # short / mid
    rationale: str = ""
    risk: str = ""


class StockReport(BaseModel):
    """Agent 5 산출물: 종목별 리포트."""

    ticker: str
    name: str
    sector: str
    html: str
    summary: str = ""
    chart_path: str | None = None


class PipelineState(TypedDict, total=False):
    """LangGraph 전체 파이프라인 상태.

    각 노드(에이전트)가 자신의 산출물을 이 상태에 채워 다음 노드로 전달한다.
    """

    as_of: str
    # Agent 1
    market_data: dict[str, Any]
    # Agent 2
    market_view: MarketView
    # Agent 3
    sectors: list[SectorPick]
    # Agent 4
    picks: list[StockPick]
    # Agent 5
    reports: list[StockReport]
    # Agent 6
    mail_result: dict[str, Any]
    # 공통
    errors: list[str]
