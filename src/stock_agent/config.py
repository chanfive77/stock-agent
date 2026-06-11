"""애플리케이션 설정 로딩.

- 비밀이 아닌 값: config.yaml
- 비밀 값(API 키, 메일 비밀번호): 환경변수(.env)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config.yaml"


@dataclass
class MarketConfig:
    universe: str = "ALL"
    top_n_by_marketcap: int = 300
    lookback_days: int = 200


@dataclass
class RecommendConfig:
    num_sectors: int = 3
    stocks_per_sector: int = 3


@dataclass
class ScheduleConfig:
    run_at: str = "16:00"
    timezone: str = "Asia/Seoul"
    skip_non_trading_days: bool = True


@dataclass
class LLMConfig:
    enabled: bool = True
    temperature: float = 0.3
    model: str = "gpt-4o-mini"
    api_key: str | None = None


@dataclass
class ReportConfig:
    include_charts: bool = True
    output_dir: str = "output"


@dataclass
class MailConfig:
    subject_prefix: str = "[데일리 주식 리포트]"
    delivery: str = "inline"
    gmail_address: str | None = None
    gmail_app_password: str | None = None
    recipients: list[str] = field(default_factory=list)


@dataclass
class Config:
    market: MarketConfig
    recommend: RecommendConfig
    schedule: ScheduleConfig
    llm: LLMConfig
    report: ReportConfig
    mail: MailConfig

    @property
    def output_path(self) -> Path:
        p = ROOT_DIR / self.report.output_dir
        p.mkdir(parents=True, exist_ok=True)
        return p


def _clean_app_password(raw: str | None) -> str | None:
    # Gmail 앱 비밀번호는 4자리씩 공백 구분되어 표시되므로 공백 제거
    if not raw:
        return None
    return "".join(raw.split())


def _split_recipients(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def load_config(path: str | Path | None = None) -> Config:
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    data: dict = {}
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    market = MarketConfig(**(data.get("market") or {}))
    recommend = RecommendConfig(**(data.get("recommend") or {}))
    schedule = ScheduleConfig(**(data.get("schedule") or {}))

    llm_data = data.get("llm") or {}
    llm = LLMConfig(
        enabled=llm_data.get("enabled", True),
        temperature=llm_data.get("temperature", 0.3),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    report = ReportConfig(**(data.get("report") or {}))

    mail_data = data.get("mail") or {}
    mail = MailConfig(
        subject_prefix=mail_data.get("subject_prefix", "[데일리 주식 리포트]"),
        delivery=mail_data.get("delivery", "inline"),
        gmail_address=os.getenv("GMAIL_ADDRESS"),
        gmail_app_password=_clean_app_password(os.getenv("GMAIL_APP_PASSWORD")),
        recipients=_split_recipients(os.getenv("MAIL_RECIPIENTS")),
    )

    return Config(
        market=market,
        recommend=recommend,
        schedule=schedule,
        llm=llm,
        report=report,
        mail=mail,
    )
