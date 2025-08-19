# Excelly 프로젝트 운영 계획서 및 업그레이드 가이드

Excelly는 Excel 관련 문제를 AI로 해결하는 FastAPI 기반 웹 애플리케이션입니다. 본 문서는 현재 기능과 적용 방법, 운영 모범사례, 그리고 향후 발전 계획을 정리하여, 업그레이드 시 참고 가능한 단일 플레이북을 제공합니다.

---

## 목차
- [1. 개요](#1-개요)
- [2. 아키텍처](#2-아키텍처)
- [3. 주요 기능](#3-주요-기능)
- [4. 설치 및 실행](#4-설치-및-실행)
- [5. 환경 설정](#5-환경-설정)
- [6. API 사용법](#6-api-사용법)
- [7. 데이터 흐름과 상태 관리](#7-데이터-흐름과-상태-관리)
- [8. 개발 가이드](#8-개발-가이드)
- [9. 배포 가이드](#9-배포-가이드)
- [10. 보안 & 운영(로깅/모니터링)](#10-보안--운영로깅모니터링)
- [11. 테스트 전략](#11-테스트-전략)
- [12. 문제 해결 가이드](#12-문제-해결-가이드)
- [13. 업그레이드 이력(핵심 변경)](#13-업그레이드-이력핵심-변경)
- [14. 로드맵(발전 계획)](#14-로드맵발전-계획)
- [부록 A. 프롬프트(persona) 개요](#부록-a-프롬프트persona-개요)

---

## 1. 개요
- 목적: Excel 함수/수식, VBA, 데이터 분석, 오류 디버깅까지 지원하는 AI 챗봇
- 핵심: OpenAI + Google Gemini 모델을 질문 유형에 따라 지능적으로 라우팅
- 기술 스택: Python 3.11+, FastAPI, SQLAlchemy(SQLite), Pandas, Jinja2(프론트), OpenAI & Gemini API
- 저장소 루트 주요 파일:
  - `app/` 백엔드 패키지 (API/서비스/모델/설정)
  - `templates/index.html` 프론트 UI(바닐라 JS)
  - `static/` 정적 리소스
  - `requirements.txt` 의존성, `Procfile`/`render.yaml` 배포 스펙
  - `README.md` 프로젝트 소개, `plan.md` 운영/업그레이드 가이드(본 문서)

---

## 2. 아키텍처
디렉토리 개요
```
excelwizard-project/
├── app/
│   ├── api/                # FastAPI 라우터: `chat.py`, `files.py`
│   ├── services/           # 비즈니스 로직: AI/파일/대화/세션
│   ├── models/             # Pydantic & SQLAlchemy 모델
│   └── core/               # 설정, 예외, DB 초기화
├── templates/index.html    # UI (Vanilla JS)
├── static/                 # 정적 자원 (이미지/스타일)
├── main.py                 # uvicorn 실행 진입점
└── README.md, plan.md, requirements.txt, Procfile
```

기능 구성
- API 계층: `app/api/chat.py`, `app/api/files.py`
- 서비스 계층: `app/services/ai_service.py`, `conversation_service.py`, `file_service.py`, `session_service.py`
- 모델 계층: `app/models/chat.py`(대화/응답/상태), `app/models/excel.py`(엑셀 분석), `app/models/database.py`(DB ORM)
- 코어: `app/core/config.py`(설정), `app/core/database.py`(엔진/세션/테이블생성), `app/core/exceptions.py`

---

## 3. 주요 기능
### 3.1 대화형 명확화 시스템(v6.0)
- 초기 질문이 모호한 경우, 유형(`file_structure`, `data_format`, `goal`, `constraints`)에 맞춰 1개씩 추가 질문
- 진행 상태는 `ConversationState`로 관리: `initial → clarifying → planning → executing → completed`
- 최대 명확화 횟수 제한(`conversation_service.max_clarifications`)

### 3.2 지능형 AI 라우팅
- 분류 기준: `simple | complex | creative | analytical | debugging`
- 모델 사용 전략(기본값):
  - 분류/간단 답변/이미지 분석: Gemini 2.0 Flash
  - 창의/분석/계획: Gemini 2.0 Pro
  - 코드 생성/디버깅: OpenAI `gpt-4o-mini`

### 3.3 파일 처리(엑셀/CSV/이미지)
- 업로드 검증(확장자/크기)
- 엑셀/CSV 시트 목록 분석, 특정 시트 미리보기(상위 5행)
- CSV 인코딩 자동 추정(`charset-normalizer`) 후 로드
- 이미지 메타/베이스64 추출, 이미지 기반 오류 분석(멀티모달)

### 3.4 세션/메시지 영속화
- SQLite(`excelly.db`) + SQLAlchemy
- 세션 메타데이터(`metadata_json`)에 대화 맥락(`conversation_context`) 저장·복원
- 메시지에 `message_type`, `metadata` 저장

### 3.5 프론트엔드 UX
- 세션 히스토리, 시트 선택 UI, 코드블록 복사 버튼, 이미지 붙여넣기
- AI 상태 표시(`/api/chat/status`)

### 3.6 시스템/상태 엔드포인트
- `/health`, `/api/status`, `/api/chat/status`

---

## 4. 설치 및 실행
### 4.1 의존성 설치
- Windows PowerShell
```powershell
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
```
- macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4.2 환경 변수 파일
프로젝트 루트에 `.env` 생성
```
OPENAI_API_KEY="sk-..."
GEMINI_API_KEY="AIza..."
DEBUG=True
DATABASE_URL="sqlite:///./excelly.db"
```

### 4.3 실행
- 개발: 
```bash
python main.py
# 또는
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- 접속: `http://127.0.0.1:8000`

---

## 5. 환경 설정
설정 소스: `app/core/config.py`
- 모델 기본값: `OPENAI_MODEL=gpt-4o-mini`, `GEMINI_PRO_MODEL=gemini-2.0-pro`, `GEMINI_FLASH_MODEL=gemini-2.0-flash`
- 파일 업로드: `MAX_FILE_SIZE=10MB`, `ALLOWED_FILE_TYPES=[.xlsx,.xls,.csv]` (+ 이미지 처리 `.png,.jpg,.jpeg`는 `file_service`에서 지원)
- 세션: `SESSION_TIMEOUT=3600`
- 요청 타임아웃: `AI_REQUEST_TIMEOUT=60`, `MAX_TOKENS=4000`
- DB: `DATABASE_URL`(기본 sqlite)

---

## 6. API 사용법
기본 경로는 루트(`/`) + 라우터 prefix를 따릅니다.

### 6.1 채팅 API (`/api/chat`)
- `GET /sessions` 모든 세션 목록
- `GET /history/{session_id}` 세션 대화 + 대화 맥락
- `POST /analyze-sheets` 업로드된 파일 시트 목록 분석
- `POST /ask` 메인 질의(옵션: `selected_sheet`, `is_feedback`, `image`)
- `DELETE /sessions/all` 전체 삭제
- `DELETE /sessions/{session_id}` 특정 세션 삭제
- `DELETE /sessions/{session_id}/messages` 특정 세션 메시지만 삭제
- `GET /status` AI/세션 서비스 상태

예시(Windows PowerShell)
```powershell
$sid = "session_$(Get-Random)"
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/chat/ask -Method Post -Form @{ 
  session_id=$sid; question='VLOOKUP은 어떻게 쓰나요?' 
}
Invoke-RestMethod http://127.0.0.1:8000/api/chat/history/$sid | ConvertTo-Json -Depth 5
```

### 6.2 파일 API (`/api/files`)
- `POST /upload` 파일 업로드 검증
- `POST /analyze` 파일 상세 분석
- `POST /extract-sheet` 특정 시트 데이터 추출
- `POST /process-image` 이미지 처리
- `GET /supported-formats` 지원 포맷과 `max_file_size_mb`

예시(curl)
```bash
curl -F "file=@sample.xlsx" http://127.0.0.1:8000/api/files/analyze
```

### 6.3 시스템 API
- `GET /health`
- `GET /api/status`

---

## 7. 데이터 흐름과 상태 관리
1) 사용자가 질문 제출 → 세션 생성/검증(`session_service.create_session/get_session`)
2) 사용자 메시지 저장(`add_message`), 파일이 있으면 `temp_file_content`에 보관
3) 질문 분류(`ai_service.classify_question`) 후 분기
   - 명확화 필요: `conversation_service`가 1개 질문을 생성 → 상태 `clarifying`
   - 바로 처리: 계획/코드/분석/디버깅 경로로 응답 생성
4) 응답 저장(`message_type`, `metadata` 포함) → 클라이언트로 전송
5) 대화 맥락 업데이트 시 `metadata_json`에 `conversation_context` 저장·복원

---

## 8. 개발 가이드
### 8.1 기능 추가 절차
1. 모델 정의: `app/models/` (Pydantic)
2. 서비스 로직: `app/services/` (비즈니스 규칙)
3. API 라우트: `app/api/` (FastAPI Router)
4. 설정: `app/core/config.py` (필요 변수 추가)

### 8.2 세션/메시지 메타 정책
- 세션 메타: `metadata_json`에 JSON 문자열로 저장 (키: `conversation_context`)
- 메시지 메타: `DBMessage.message_type`, `DBMessage.metadata_json` 저장 → 조회 시 역직렬화

### 8.3 파일 처리 주의
- 업로드 크기 검증: `settings.MAX_FILE_SIZE`
- CSV 인코딩: `charset-normalizer` 결과 우선 적용, 실패 시 UTF-8 fallback
- 대용량/민감 파일은 DB BLOB 저장 대신 외부 스토리지로 이관 고려(로드맵 참고)

---

## 9. 배포 가이드
- 개발/로컬: `uvicorn app.main:app`
- Render/Procfile:
  - `Procfile`: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
  - `main.py`는 `app.main:app`을 로드
- DB 초기화: 앱 스타트업 이벤트에서 `init_db()` 자동 실행 → 최초 실행 시 테이블 생성 보장

---

## 10. 보안 & 운영(로깅/모니터링)
### 10.1 보안 권장
- CORS 도메인 제한(현재 `*` → 운영 환경에서 화이트리스트)
- 간단 토큰 인증/레이트 리밋(Reverse Proxy 또는 FastAPI 미들웨어) 도입
- 업로드 크기 서버 레벨 제한(Nginx/Proxy) 병행
- API 키는 `.env`/시크릿 관리(
  - 소스 커밋 금지, 환경 주입 사용)

### 10.2 로깅/모니터링
- Python `logging`으로 구조화 로그, 요청 ID/세션 ID 포함 권장
- `/api/status` 주기 호출로 헬스·지표 수집 (Prometheus/Grafana 연계 고려)

---

## 11. 테스트 전략
- 유닛 테스트: 서비스 레이어 단위(`file_service`, `conversation_service`)
- 통합 테스트: 테스트 DB를 사용한 세션/메시지 흐름 검증
- E2E 스모크: 주요 API 경로(ask/analyze-sheets/extract-sheet/status)
- 프롬프트 회귀: 대표 질문 세트에 대한 출력 품질 점검(샘플 스냅샷 비교)

---

## 12. 문제 해결 가이드
### 12.1 `/health` 503
- 원인: API 키 미설정 → `.env` 확인, `settings.validate()` 실패

### 12.2 파일 업로드 실패(형식/크기)
- 원인: 미지원 확장자, `MAX_FILE_SIZE` 초과
- 조치: `/api/files/supported-formats` 확인, 설정값 조정

### 12.3 CSV 한글 깨짐
- 조치: 자동 인코딩 추정(`charset-normalizer`) 적용됨. 실패 시 파일 인코딩 재저장(UTF-8) 권장

### 12.4 대화 맥락 소실
- 조치: DB `sessions.metadata_json` 확인(키 `conversation_context`)

---

## 13. 업그레이드 이력(핵심 변경)
- 대화 맥락 저장 개선: `conversation_context`를 세션 `metadata_json`에 저장/복원
- 메시지 메타 저장: `message_type`/`metadata` DB 영속화 및 조회 반영
- 포맷 정보 정확화: `/api/files/supported-formats`에서 `max_file_size_mb`를 설정값 기준으로 반환
- DB 초기화 보장: 앱 스타트업 훅에서 `init_db()` 자동 실행
- CSV 인코딩 견고화: `charset-normalizer`로 인코딩 추정 후 로드

---

## 14. 로드맵(발전 계획)
### 14.1 단기(1~2주)
- 간단 답변 모드 도입: 프론트 토글 + 백엔드 `answer_style=concise` 지원, 토큰 상한/프롬프트 요약 규칙 적용
- 업로드 UX 개선: 진행률/에러상세, 대용량 샘플 가이드
- 모델 호출 리트라이/부분 시간초과 대비(서킷 브레이커)
- 수식/VBA 시각화 데모(프론트 중심): Demo JSON 파서, 간단 수식 계산기, Mermaid 다이어그램 렌더

### 14.2 중기(1~2개월)
- 파일 저장소 분리: DB BLOB → 파일시스템/오브젝트 스토리지(S3 호환) + 만료 정책
- 인증/레이트 리밋: 토큰 인증, IP/세션 기반 속도 제한
- 로깅/지표: 구조화 로그, Prometheus 메트릭, 알림(Webhook/Slack)
- 테스트 확충: 프롬프트 회귀/시나리오 테스트 자동화
- 시트/열 자동 탐지 강화: 헤더 추론/추천 질문 고도화

### 14.3 장기(3개월+)
- 팀 협업 기능: 세션 공유/즐겨찾기/템플릿(매크로 레시피) 라이브러리
- 코드 실행 샌드박스 연계(생성된 VBA/수식 검증 시뮬레이터)
- 역할 기반 접근 제어(RBAC), 다중 테넌시, 조직 과금/모니터링

성공 지표(KPI) 예시
- 첫 응답까지의 평균 지연, 대화당 명확화 횟수, 피드백(👍/👎) 비율, 재방문률, 오류율(5xx)

---

## 15. 확장성 제안(적용 우선)
프로젝트의 목표(실용적·정확한 Excel 문제 해결)와 일치하는, 바로 적용 가능한 확장 기능을 우선 나열합니다.

### 15.1 간단 답변 모드(Concise Mode)
- 목적: 과도한 장문을 방지하고 핵심 위주로 응답
- 백엔드 변경
  - `app/services/ai_service.py`의 `generate_*` 및 `process_chat_request`에 `answer_style: 'concise'|'detailed'` 인자 추가
  - `concise`일 때: 응답 지시(“핵심만, 5줄 이내”), `MAX_TOKENS` 하향(예: 1200), 예시·팁을 최소화
- 프론트 변경
  - `templates/index.html`에 토글 추가 → `/api/chat/ask` 요청 시 `answer_style` 폼 필드 포함
- 성공 기준: 평균 응답 길이 40%↓, 사용성(👍 비율) 유지 또는 개선

### 15.2 스트리밍 응답(SSE/Chunk)
- 목적: 체감 대기시간 감소 및 진행감 제공
- 백엔드: `StreamingResponse` 기반 스트리밍 엔드포인트(`GET /api/chat/stream` 또는 `POST /api/chat/ask?stream=true`)
- 프론트: EventSource/ReadableStream으로 점진 렌더링, 코드블록 하이라이트는 마지막 청크에 적용
- 성공 기준: TTFB(첫 바이트) 60%↓, 이탈률↓

### 15.3 파일 분석 캐시
- 목적: 동일 파일 반복 분석 시 비용/지연 절감
- 구현: `file_service`에 SHA-256 해시 캐시(메모리 또는 DB 테이블) → 동일 해시 시 이전 분석 결과 반환
- 성공 기준: 재분석 요청 평균 지연 70%↓, API 비용 절감

### 15.4 시트/열 자동 감지 & 추천 질문
- 목적: 명확화에 필요한 최소한의 질문 자동화
- 구현: 1행 헤더 추정, 숫자/문자 비율, 고유도/결측률 등으로 대표 열 후보를 산출 → “추천 시트/열” 버튼 제공
- 성공 기준: 명확화 횟수 평균 0.3↓, 성공율 증가

### 15.5 이미지 오류 요약(Top‑3 가설)
- 목적: 장문 분석 억제 + 실행 가능한 가설 중심 대응
- 구현: 이미지 분석 후 3줄 요약 + Top‑3 원인/조치만 출력하도록 프롬프트 가드
- 성공 기준: 디버깅 응답 평균 길이 30%↓, 재질문율↓

---

### 15.6 수식/VBA 시각화 데모(즉시 적용)
- 목적: 사용자가 “전/후” 변화를 눈으로 확인하고, 수식/VBA 동작 원리를 빠르게 이해
- 접근 1) Demo JSON 블록 파서(프론트 전용)
  - AI가 코드펜스에 `excel-demo` JSON을 포함 → 프론트가 파싱해 표와 단계별 변화를 시각화
  - JSON 스키마(초안):
    ```json
    {
      "title": "VLOOKUP 예시",
      "inputs": [
        { "name": "제품표", "data": [["코드","이름","가격"],["A101","노트북",100]] }
      ],
      "steps": [
        {
          "desc": "코드로 가격 찾기",
          "formula": "=VLOOKUP(\"A101\", 제품표!A:C, 3, FALSE)",
          "result": 100,
          "highlight": { "table": "제품표", "cells": ["A2","C2"] }
        }
      ],
      "outputs": [
        { "name": "결과", "data": [["코드","가격"],["A101",100]] }
      ]
    }
    ```
  - 렌더링 규칙: 좌측 입력 테이블, 우측 결과 테이블, 단계별 설명/하이라이트(셀 배경 강조)
- 접근 2) 브라우저 수식 계산기 연결(선택)
  - `hot-formula-parser` CDN 로드 후 SUMIF/VLOOKUP/INDEX-MATCH 등 기본 수식을 소규모 데이터에 적용해 즉시 결과 표시
  - 지원 목록/제한을 명시하고, 미지원은 “시연 불가(설명만)” 처리
- 성공 기준: 체감 이해도 개선(👍 비율↑), 평균 재질문 감소

### 15.7 Mermaid 다이어그램 렌더(즉시 적용)
- 목적: VBA 로직/처리 흐름을 순서도로 직관적으로 설명
- 구현: 답변 내 ` ```mermaid ` 코드펜스를 감지해 Mermaid 렌더(클라이언트에 Mermaid 스크립트 로드)
- 가이드: AI가 “범위 스캔 → 조건 검사 → 값 갱신” 같은 절차를 플로우차트/시퀀스 다이어그램으로 제공하도록 프롬프트에 지시
- 성공 기준: 긴 설명 없이도 로직 이해가 가능(피드백 개선)

### 15.8 서버 미니 시뮬레이터(선택)
- 목적: 복잡 시나리오를 서버에서 pandas로 재현하여 HTML/이미지 스니펫을 생성
- API 초안: `POST /api/demo/preview`
  - 요청: `{ tables: {이름: 데이터(2D 배열)}[], operations: [{type:"vlookup"|"sumif"|... , args:{...}}] }`
  - 응답: `{ html_preview: "...", steps: [...], warnings: [...] }` 또는 구조화 JSON
- 제한/보안: 행/열/용량 상한, 실행 시간 제한, 파일/네트워크 접근 차단
- 성공 기준: 복잡 케이스에서도 일관 프리뷰 제공, 오해 감소

## 16. 모델 라우팅 최적화 가이드(Gemini 2.5 vs GPT‑4o‑mini)
현행 기본 전략에 다음 기준을 추가합니다.

- 분류/간단 답변/이미지 1차 해석: Gemini 2.5 Flash
- 계획·창의·분석: Gemini 2.5 Pro
- 코드·수식 생성: 기본 GPT‑4o‑mini, 단 아래 조건에서 Gemini 2.5 Pro 승급
  - 다시티/다시트 맥락 등 장문 컨텍스트, 복합 제약(버전·매크로·언어 혼용)
- 디버깅: 이미지 포함 시 Gemini 2.5 분석 → 코드 수정은 GPT‑4o‑mini로 정리

프롬프트 가드라인
- 2.5 사용 시: “간단/핵심 중심, 코드/수식만 우선” 가드 추가로 장문화 억제
- 4o‑mini 사용 시: “문맥 핵심 5줄 요약 후 코드”로 장문 맥락 대응

---

## 17. 품질/비용 실험 설계(A/B)
- 지표: 수식 정답률, VBA 정적검사 통과율, 이미지 원인 Top‑3 적중률(휴리스틱), 👍/👎, 지연, 토큰 비용
- 방법: 30~50개 샘플을 라우팅 전략별 A/B로 실행 → 결과/메타를 DB에 저장 → 간단 리포트(세션 통계 확장)
- 적용: `session_service.add_message` 메타 확장으로 전략/모델/토큰/지연 기록, `/api/status`에 간단 리포트 추가 가능

## 부록 A. 프롬프트(persona) 개요
- `PLANNING_PERSONA_PROMPT`: 추측 금지, 문제 재정의, 해결 계획 제시, 동의 유도
- `CODING_PERSONA_PROMPT`: 계획 100% 준수, 완성 코드/수식, 단계별 안내
- `DEBUGGING_PERSONA_PROMPT`: 사과/공감, 원인 추정, 수정안 재제시, 격려
- `CLARIFICATION_PERSONA_PROMPT`: 한 번에 하나, 구체/친근 톤, 유형별 질문

---

### 변경 제안 적용 체크리스트(요약)
- [x] 대화 맥락 메타 저장/복원 반영
- [x] 메시지 `message_type`/`metadata` 저장/조회 반영
- [x] 지원 포맷의 `max_file_size_mb` 정확화
- [x] 앱 스타트업 DB 초기화
- [x] CSV 인코딩 자동 추정

### 빠른 점검 커맨드(Windows PowerShell)
```powershell
# 상태
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/status

# 간단 질의
$sid = "session_$(Get-Random)"
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/chat/ask -Method Post -Form @{ session_id=$sid; question='VLOOKUP은 어떻게 쓰나요?' }
Invoke-RestMethod http://127.0.0.1:8000/api/chat/history/$sid | ConvertTo-Json -Depth 5

# 포맷
Invoke-RestMethod http://127.0.0.1:8000/api/files/supported-formats
```

이 문서는 업그레이드 시 의사결정과 구현 방향의 기준 문서로 활용됩니다. 변경 발생 시 본 문서도 함께 업데이트하세요.


