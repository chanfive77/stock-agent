"""CLI 진입점."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import load_config
from .orchestrator import run_once
from .scheduler import run_forever


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # 외부 라이브러리 디버그 로그 억제
    for noisy in ("matplotlib", "urllib3", "httpx", "httpcore", "PIL", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _print_summary(state) -> None:
    view = state.get("market_view")
    print("\n" + "=" * 60)
    if view:
        print(f"[시황] 스탠스={view.stance}")
        print(f"  단기: {view.short_term}")
        print(f"  중기: {view.mid_term}")
    print("\n[추천 섹터]")
    for s in state.get("sectors", []):
        print(f"  - {s.name} (점수 {s.score}, 20일 {s.momentum_20d}%)")
    print("\n[추천 종목]")
    for p in state.get("picks", []):
        print(f"  - [{p.sector}] {p.name}({p.ticker}) 점수 {p.score} · 5D {p.pct_5d}% 20D {p.pct_20d}% · {p.horizon}")
    print(f"\n[메일] {state.get('mail_result')}")
    if state.get("errors"):
        print("\n[경고]")
        for e in state["errors"]:
            print(f"  ! {e}")
    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stock-agent", description="국내 주식 시황 분석·추천·메일 발송 멀티 에이전트")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-c", "--config", default=None, help="config.yaml 경로")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="파이프라인 1회 실행")
    p_run.add_argument("--dry-run", action="store_true", help="메일 발송 없이 산출물만 생성")
    p_run.add_argument("--limit", type=int, default=None, help="유니버스 종목 수 제한(테스트용)")

    sub.add_parser("schedule", help="매일 지정 시각 자동 실행 데몬")

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    cfg = load_config(args.config)

    if args.command == "run":
        if args.limit:
            cfg.market.top_n_by_marketcap = args.limit
        state = run_once(cfg, dry_run=args.dry_run)
        _print_summary(state)
        return 0

    if args.command == "schedule":
        run_forever(cfg)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
