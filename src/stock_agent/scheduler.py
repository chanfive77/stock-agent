"""매일 지정 시각(KST) 파이프라인 실행 스케줄러.

외부 의존성 없이 표준 라이브러리만 사용한다.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import Config
from .orchestrator import run_once

log = logging.getLogger(__name__)


def _next_run(now: datetime, run_at: str, skip_weekends: bool) -> datetime:
    hh, mm = (int(x) for x in run_at.split(":"))
    candidate = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    if skip_weekends:
        while candidate.weekday() >= 5:  # 5=토, 6=일
            candidate += timedelta(days=1)
    return candidate


def run_forever(cfg: Config) -> None:
    tz = ZoneInfo(cfg.schedule.timezone)
    log.info("스케줄러 시작: 매일 %s (%s)", cfg.schedule.run_at, cfg.schedule.timezone)
    while True:
        now = datetime.now(tz)
        nxt = _next_run(now, cfg.schedule.run_at, cfg.schedule.skip_non_trading_days)
        sleep_s = (nxt - now).total_seconds()
        log.info("다음 실행: %s (%.0f분 후)", nxt.isoformat(), sleep_s / 60)
        time.sleep(max(1, sleep_s))
        try:
            run_once(cfg, dry_run=False)
        except Exception as e:  # noqa: BLE001
            log.exception("파이프라인 실행 중 오류: %s", e)
