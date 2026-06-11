# stock-agent

매일 국내 주식(KOSPI/KOSDAQ)의 **단기/중기 시황을 분석**하고, **3개 섹터 + 섹터별 3개 종목(총 9종목)**을 추천한 뒤, **종목별 리포트를 이메일로 발송**하는 멀티 에이전트 시스템입니다.

LangGraph로 6개의 에이전트(데이터 수집 → 시황 분석 → 섹터 추천 → 종목 추천 → 리포트 생성 → 메일 발송)를 연결하고, 이를 매일 자동 실행·관리하는 오케스트레이터를 둡니다.

## 구성

| 에이전트 | 역할 |
|---|---|
| 1. Data Collector | pykrx/FinanceDataReader로 지수·섹터·종목 데이터 수집 |
| 2. Market Analyst | 단기(1~5일)·중기(1~3개월) 시황 분석 |
| 3. Sector Selector | 섹터 모멘텀 기반 상위 3개 섹터 선정 |
| 4. Stock Selector | 섹터별 기술적+모멘텀 스코어로 3개 종목 선정 |
| 5. Report Generator | 종목별 HTML 리포트(차트 포함) 생성 |
| 6. Mailer | Gmail SMTP로 리포트 발송 |
| Orchestrator | 전체 파이프라인 실행 + 매일 16:00(KST) 스케줄링 |

## 설치

```bash
uv venv && uv pip install -e .
cp .env.example .env   # 키/메일 정보 입력
```

## 실행

```bash
# 1회 즉시 실행
stock-agent run

# 메일 발송 없이 콘솔 출력만 (드라이런)
stock-agent run --dry-run

# 매일 16:00(KST) 스케줄 데몬
stock-agent schedule
```

## 설정

- 비밀 값(API 키, 메일 비밀번호)은 `.env`
- 그 외 동작 설정은 `config.yaml`

## 면책

본 시스템의 산출물은 투자 참고용이며 투자 권유가 아닙니다.
