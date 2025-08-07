# 🤖 AI 엑셀 해결사 '엑셀리(Excelly)'

**엑셀에 관한 모든 질문, 이제 AI 파트너 '엑셀리'와 함께 해결하세요!**

이 프로젝트는 OpenAI의 GPT-4 모델과 Google의 Gemini 모델을 혼합 활용하여, 사용자의 엑셀 관련 질문에 최적의 답변을 제공하는 지능형 웹 챗봇입니다. 단순한 함수 설명을 넘어, 복잡한 VBA 코드 생성, 데이터 분석, 그리고 사용자의 문제 해결 과정을 돕는 피드백 시스템까지 갖추고 있습니다.

 
*(추후 실제 서비스 스크린샷 이미지 링크로 교체하세요)*

---

## ✨ 핵심 기능 (v1.1)

*   **지능형 하이브리드 AI 엔진**
    *   **의도 분석 라우팅:** 사용자의 질문을 분석하여 '코드 생성', '복잡한 수식', '데이터 분석', '일반 대화' 등 의도를 파악합니다.
    *   **최적 모델 할당:** 의도에 따라 논리/정확성이 중요한 작업은 **GPT-4 Turbo**에, 컨텍스트 이해 및 요약이 중요한 작업은 **Gemini 1.5 Pro**에 자동으로 할당하여 최상의 결과물을 생성합니다.
    *   **AI 협업 모델:** 파일이 첨부된 복잡한 요청의 경우, Gemini Pro가 먼저 파일의 핵심을 요약하고 GPT-4 Turbo가 이를 바탕으로 정밀한 코드를 생성하는 '하이브리드 모드'가 작동합니다.

*   **'엑셀리' 페르소나**
    *   **친근한 멘토:** 딱딱한 기계가 아닌, 유머와 위트를 겸비한 친절한 엑셀 전문가 '엑셀리'가 사용자를 맞이합니다.
    *   **체계적인 답변:** 모든 답변은 [공감] → [핵심 해결책] → [더 나은 대안 제시] → [격려]의 4단계 구조로 제공되어 사용자의 문제 해결뿐만 아니라 실력 향상까지 돕습니다.

*   **상호작용 가능한 피드백 시스템**
    *   **디버깅 모드:** AI가 제안한 해결책이 실패했을 경우, 사용자는 '문제가 있다'고 피드백을 보낼 수 있습니다.
    *   **이미지 인식:** 오류가 발생한 화면을 캡처하여 붙여넣으면, AI가 이미지를 분석하여 문제의 원인을 파악하고 수정된 해결책을 제시합니다.
    *   **세션 기반 대화:** 모든 대화는 세션별로 기록되어, AI가 이전 대화 내용을 기억하고 맥락에 맞는 피드백 처리를 수행합니다.

*   **사용자 편의 기능**
    *   **원클릭 코드 복사:** 생성된 모든 VBA 및 코드 블록에는 '복사' 버튼이 제공됩니다.
    *   **이미지 붙여넣기:** 클립보드에 있는 이미지를 채팅창에 바로 붙여넣기(Ctrl+V)하여 질문할 수 있습니다.

---

## 🛠️ 기술 스택

*   **Backend:** Python, FastAPI
*   **Frontend:** HTML, CSS, JavaScript (Vanilla)
*   **AI APIs:**
    *   OpenAI API (`gpt-4-turbo`)
    *   Google Gemini API (`gemini-1.5-pro-latest`, `gemini-1.5-flash-latest`)
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
    git clone https://github.com/YourUsername/excel-ai-chatbot.git
    cd excel-ai-chatbot
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
    *(아직 `requirements.txt`가 없다면, `pip install "fastapi[all]" openai python-dotenv pandas Pillow google-generativeai` 명령어를 사용하세요.)*

4.  **.env 파일 생성:**
    프로젝트 루트에 `.env` 파일을 생성하고 아래 내용을 채워넣으세요.
    ```
    OPENAI_API_KEY="sk-..."
    GEMINI_API_KEY="AIzaSy..."
    ```

5.  **서버 실행:**
    ```bash
    uvicorn main:app --reload
    ```

6.  **접속:**
    웹 브라우저를 열고 `http://127.0.0.1:8000` 주소로 접속합니다.

---

## 📝 개발 로그

이 프로젝트의 상세한 개발 과정 및 의사결정 기록은 [PROJECT_LOG.md](PROJECT_LOG.md) 파일에서 확인할 수 있습니다.