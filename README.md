# 🤖 AI 엑셀 해결사 '엑셀리(Excelly)' v6.0 (Gemini 2.0)

**엑셀에 관한 모든 질문, 이제 AI 파트너 '엑셀리'와 함께 해결하세요!**

이 프로젝트는 OpenAI의 GPT-4 모델과 Google의 Gemini 모델을 지능적으로 라우팅하여, 사용자의 엑셀 관련 질문에 최적의 답변을 제공하는 고도화된 웹 챗봇입니다. 단순한 함수 설명을 넘어, 복잡한 VBA 코드 생성, 데이터 분석, 창의적 솔루션 제안, 그리고 사용자의 문제 해결 과정을 돕는 피드백 시스템까지 갖추고 있습니다.

## 🏗️ 새로운 아키텍처 (v5.1 최종 완료)

### 모듈화된 구조
```
excelwizard-project/
├── app/                          # 메인 애플리케이션 패키지
│   ├── __init__.py
│   ├── main.py                   # FastAPI 앱 설정
│   ├── core/                     # 핵심 설정 및 유틸리티
│   │   ├── __init__.py
│   │   ├── config.py             # 설정 관리
│   │   └── exceptions.py         # 커스텀 예외 클래스
│   ├── models/                   # 데이터 모델
│   │   ├── __init__.py
│   │   ├── chat.py               # 채팅 관련 모델
│   │   └── excel.py              # 엑셀 관련 모델
│   ├── services/                 # 비즈니스 로직 서비스
│   │   ├── __init__.py
│   │   ├── ai_service.py         # AI 모델 관리
│   │   ├── file_service.py       # 파일 처리
│   │   └── session_service.py    # 세션 관리
│   └── api/                      # API 엔드포인트
│       ├── __init__.py
│       ├── chat.py               # 채팅 API
│       └── files.py              # 파일 API
├── templates/                    # HTML 템플릿
│   └── index.html               # 메인 UI
├── static/                      # 정적 파일
├── main.py                      # 애플리케이션 진입점
├── main_old.py                  # 이전 버전 (백업)
├── prompts.py                   # AI 프롬프트 정의
├── requirements.txt             # 의존성 목록
└── README.md                    # 프로젝트 문서
```

### 주요 개선사항
- **모듈화된 구조**: 기능별로 분리된 서비스와 API
- **타입 안전성**: Pydantic 모델을 통한 데이터 검증
- **에러 처리**: 체계적인 예외 처리 및 사용자 친화적 메시지
- **설정 관리**: 중앙화된 설정 관리 시스템
- **확장성**: 새로운 기능 추가가 용이한 구조

---

## ✨ 핵심 기능

*   **대화형 질문 명확화 시스템 (v6.0 신규)**
    *   **3-5회 대화형 명확화:** 사용자의 의도를 정확히 파악하기 위해 필요한 정보를 단계적으로 수집합니다.
    *   **지능형 질문 생성:** 질문 유형(file_structure, data_format, goal, constraints)에 따라 최적의 명확화 질문을 생성합니다.
    *   **맥락 유지:** 대화 과정에서 수집된 정보를 기억하고 활용하여 정확한 해결책을 제공합니다.
    *   **자동 상태 관리:** 명확화 → 계획 → 실행 → 완료의 단계별 상태를 자동으로 관리합니다.

*   **지능형 AI 라우터 (v6.0 - Gemini 2.0 최적화)**
    *   **5단계 질문 분류:** simple, complex, creative, analytical, debugging으로 질문을 정교하게 분류합니다.
    *   **모델별 최적화:** 각 질문 유형에 맞는 최적의 AI 모델을 자동으로 선택합니다.
        *   **OpenAI GPT-4o-mini:** 코드 생성, 디버깅, 정밀한 문제 해결 (최고 정확도)
        *   **Gemini 2.0 Pro:** 창의적 솔루션, 데이터 분석, 계획 수립 (혁신적 사고)
        *   **Gemini 2.0 Flash:** 빠른 분류, 간단한 답변, 이미지 분석 (최고 속도/비용 효율)
    *   **실시간 모델 정보:** 어떤 AI 모델이 사용되었는지 실시간으로 표시합니다.

*   **향상된 하이브리드 AI 엔진**
    *   **의도 분석 라우팅:** 사용자의 질문을 분석하여 '코드 생성', '복잡한 수식', '데이터 분석', '창의적 제안' 등 의도를 파악합니다.
    *   **AI 협업 모델:** 파일이 첨부된 복잡한 요청의 경우, Gemini Pro가 먼저 파일의 핵심을 요약하고 GPT-4 Turbo가 이를 바탕으로 정밀한 코드를 생성하는 '하이브리드 모드'가 작동합니다.

*   **'엑셀리' 페르소나**
    *   **친근한 멘토:** 딱딱한 기계가 아닌, 유머와 위트를 겸비한 친절한 엑셀 전문가 '엑셀리'가 사용자를 맞이합니다.
    *   **체계적인 답변:** 모든 답변은 [공감] → [핵심 해결책] → [더 나은 대안 제시] → [격려]의 4단계 구조로 제공되어 사용자의 문제 해결뿐만 아니라 실력 향상까지 돕습니다.

*   **상호작용 가능한 피드백 시스템**
    *   **디버깅 모드:** AI가 제안한 해결책이 실패했을 경우, 사용자는 '문제가 있다'고 피드백을 보낼 수 있습니다.
    *   **이미지 인식:** 오류가 발생한 화면을 캡처하여 붙여넣으면, AI가 이미지를 분석하여 문제의 원인을 파악하고 수정된 해결책을 제시합니다.
    *   **세션 기반 대화:** 모든 대화는 세션별로 기록되어, AI가 이전 대화 내용을 기억하고 맥락에 맞는 피드백 처리를 수행합니다.

*   **사용자 편의 기능**
    *   **AI 상태 모니터링:** 사용 가능한 AI 모델 정보를 실시간으로 확인할 수 있습니다.
    *   **원클릭 코드 복사:** 생성된 모든 VBA 및 코드 블록에는 '복사' 버튼이 제공됩니다.
    *   **이미지 붙여넣기:** 클립보드에 있는 이미지를 채팅창에 바로 붙여넣기(Ctrl+V)하여 질문할 수 있습니다.
    *   **대화 기록 관리:** 세션별로 대화 기록을 관리하고 이전 대화를 불러올 수 있습니다.

---

## 🛠️ 기술 스택

*   **Backend:** Python 3.11+, FastAPI
*   **Frontend:** HTML, CSS, JavaScript (Vanilla)
*   **AI APIs:**
    *   OpenAI API (`gpt-4o-mini`) - 최고 정확도의 코드 생성 및 디버깅
    *   Google Gemini API (`gemini-2.0-pro`, `gemini-2.0-flash`) - 혁신적 사고 및 빠른 처리
*   **Core Libraries:**
    *   `pandas`: 엑셀 파일 분석
    *   `Pillow`: 이미지 처리
    *   `python-dotenv`: 환경 변수 관리
    *   `uvicorn`: ASGI 서버
*   **Frontend Libraries:**
    *   `Marked.js`: 마크다운 렌더링
    *   `Highlight.js`: 코드 구문 강조

---

## 🚀 시작하는 방법

1.  **저장소 복제:**
    ```bash
    git clone https://github.com/CHULJU-KIM/Excelly.git
    cd Excelly
    ```

2.  **가상환경 생성 및 활성화:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **필요 라이브러리 설치:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **.env 파일 생성:**
    프로젝트 루트에 `.env` 파일을 생성하고 아래 내용을 채워넣으세요.
    ```
    OPENAI_API_KEY="sk-..."
    GEMINI_API_KEY="AIzaSy..."
    DEBUG=True
    ```

5.  **서버 실행:**
    ```bash
    python main.py
    ```

6.  **접속:**
    웹 브라우저를 열고 `http://127.0.0.1:8000` 주소로 접속합니다.

---

## 📡 API 엔드포인트

### 채팅 API (`/api/chat/`)
- `GET /sessions` - 모든 세션 목록 조회
- `GET /history/{session_id}` - 특정 세션의 대화 기록 조회
- `POST /analyze-sheets` - 엑셀 파일 시트 분석
- `POST /ask` - 메인 채팅 엔드포인트 (지능형 AI 라우터)
- `DELETE /sessions/{session_id}` - 세션 삭제
- `GET /status` - AI 서비스 상태 및 모델 정보 확인

### 파일 API (`/api/files/`)
- `POST /upload` - 파일 업로드 및 검증
- `POST /analyze` - 파일 상세 분석
- `POST /extract-sheet` - 특정 시트 데이터 추출
- `POST /process-image` - 이미지 처리
- `GET /supported-formats` - 지원 파일 형식 조회

### 시스템 API
- `GET /health` - 헬스 체크
- `GET /api/status` - 전체 서비스 상태
- `GET /docs` - API 문서 (개발 모드)

---

## 🔧 개발 가이드

### 새로운 기능 추가
1. **모델 정의**: `app/models/`에 새로운 Pydantic 모델 추가
2. **서비스 로직**: `app/services/`에 비즈니스 로직 구현
3. **API 엔드포인트**: `app/api/`에 새로운 라우터 추가
4. **설정 추가**: `app/core/config.py`에 필요한 설정 추가

### 테스트
```bash
# 서비스 상태 확인
curl http://localhost:8000/health

# API 문서 확인 (개발 모드)
curl http://localhost:8000/docs
```

---

## 📝 개발 로그

이 프로젝트의 상세한 개발 과정 및 의사결정 기록은 [PROJECT_LOG.md](PROJECT_LOG.md) 파일에서 확인할 수 있습니다.

---

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.
