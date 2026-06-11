"""Agent 6 — 메일 발송 (Gmail SMTP)."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Template

from ..config import Config
from ..state import MarketView, PipelineState, SectorPick, StockReport

log = logging.getLogger(__name__)

DIGEST_TEMPLATE = Template(
    """
<div style="font-family:Apple SD Gothic Neo,Malgun Gothic,sans-serif;max-width:620px;margin:0 auto;color:#111827;">
  <h1 style="font-size:20px;">📊 데일리 주식 리포트 <span style="color:#6b7280;font-size:14px;">{{ as_of }}</span></h1>

  {% if view %}
  <div style="background:#f9fafb;border-radius:10px;padding:14px;margin:12px 0;">
    <h3 style="margin:0 0 6px;">시황 요약 · 스탠스: {{ stance_kr }}</h3>
    <p style="margin:4px 0;font-size:14px;"><b>단기</b> {{ view.short_term }}</p>
    <p style="margin:4px 0;font-size:14px;"><b>중기</b> {{ view.mid_term }}</p>
    {% if view.commentary %}<p style="margin:6px 0 0;font-size:13px;color:#374151;">💬 {{ view.commentary }}</p>{% endif %}
  </div>
  {% endif %}

  <div style="margin:12px 0;">
    <h3 style="margin:0 0 6px;">추천 섹터 ({{ sectors|length }})</h3>
    <ul style="font-size:14px;padding-left:18px;">
    {% for s in sectors %}
      <li style="margin:3px 0;"><b>{{ s.name }}</b> · 점수 {{ s.score }} · 20일 {{ s.momentum_20d }}% — {{ s.rationale }}</li>
    {% endfor %}
    </ul>
  </div>

  <h3 style="margin:14px 0 0;">종목별 리포트 ({{ reports|length }})</h3>
  {{ body }}

  <p style="font-size:11px;color:#9ca3af;margin-top:18px;border-top:1px solid #e5e7eb;padding-top:10px;">
    본 리포트는 자동 생성된 투자 참고 자료이며 투자 권유가 아닙니다. 투자 판단과 책임은 투자자 본인에게 있습니다.
  </p>
</div>
"""
)

_STANCE_KR = {"bullish": "강세", "neutral": "중립", "bearish": "약세"}


def build_digest_html(
    as_of: str,
    view: MarketView | None,
    sectors: list[SectorPick],
    reports: list[StockReport],
) -> str:
    body = "\n".join(r.html for r in reports)
    return DIGEST_TEMPLATE.render(
        as_of=as_of,
        view=view,
        stance_kr=_STANCE_KR.get(view.stance, view.stance) if view else "-",
        sectors=sectors,
        reports=reports,
        body=body,
    )


def _build_message(cfg: Config, subject: str, html: str, reports: list[StockReport]) -> MIMEMultipart:
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = cfg.mail.gmail_address or ""
    msg["To"] = ", ".join(cfg.mail.recipients)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText("HTML 형식의 리포트입니다. HTML 보기를 지원하는 메일 앱에서 확인하세요.", "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    for r in reports:
        if r.chart_path and Path(r.chart_path).exists():
            with open(r.chart_path, "rb") as f:
                img = MIMEImage(f.read())
            img.add_header("Content-ID", f"<chart_{r.ticker}>")
            img.add_header("Content-Disposition", "inline", filename=f"chart_{r.ticker}.png")
            msg.attach(img)
    return msg


def run(state: PipelineState, cfg: Config, dry_run: bool = False) -> PipelineState:
    as_of = state.get("as_of", "")
    view = state.get("market_view")
    sectors = state.get("sectors", [])
    reports = state.get("reports", [])
    errors = list(state.get("errors", []))

    html = build_digest_html(as_of, view, sectors, reports)

    # 항상 산출물을 디스크에 저장 (감사/디버깅용)
    digest_path = cfg.output_path / f"digest_{as_of or 'latest'}.html"
    digest_path.write_text(html, encoding="utf-8")

    subject = f"{cfg.mail.subject_prefix} {as_of} · 추천 {len(reports)}종목"

    if dry_run:
        state["mail_result"] = {"sent": False, "dry_run": True, "digest": str(digest_path)}
        return state

    if not cfg.mail.gmail_address or not cfg.mail.gmail_app_password:
        errors.append("Gmail 자격증명 미설정 — 메일 발송 생략 (digest 파일만 저장)")
        state["mail_result"] = {"sent": False, "reason": "no_credentials", "digest": str(digest_path)}
        state["errors"] = errors
        return state

    if not cfg.mail.recipients:
        errors.append("수신자 미설정 — 메일 발송 생략")
        state["mail_result"] = {"sent": False, "reason": "no_recipients", "digest": str(digest_path)}
        state["errors"] = errors
        return state

    msg = _build_message(cfg, subject, html, reports)
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(cfg.mail.gmail_address, cfg.mail.gmail_app_password)
            server.sendmail(cfg.mail.gmail_address, cfg.mail.recipients, msg.as_string())
        log.info("메일 발송 완료: %s", cfg.mail.recipients)
        state["mail_result"] = {"sent": True, "recipients": cfg.mail.recipients, "digest": str(digest_path)}
    except Exception as e:  # noqa: BLE001
        errors.append(f"메일 발송 실패: {e}")
        state["mail_result"] = {"sent": False, "reason": str(e), "digest": str(digest_path)}

    state["errors"] = errors
    return state
