# ExcelWizard - AI 기반 Excel 전문 도우미 🚀

## 📋 **프로젝트 개요**

ExcelWizard는 **초보자부터 고급자까지** 모든 사용자를 위한 AI 기반 Excel 전문 도우미입니다. 
Google Gemini와 OpenAI의 최신 AI 모델을 활용하여 사용자 수준에 맞는 맞춤형 Excel 솔루션을 제공합니다.

## ✨ **주요 특징**

### 🤖 **수준별 맞춤 AI 모델 시스템**
- **초보자**: Gemini 2.0 Flash (친화적 설명, 단계별 가이드)
- **중급자**: Gemini 2.5 Flash (빠른 분석, 구조화된 해결책)
- **고급자**: Gemini 2.5 Pro (복잡한 VBA, 함수조합, 최적화)

### 📊 **다양한 파일 분석 기능**
- **Excel 파일**: 다중 시트 분석, 데이터 추출, 구조 파악
- **이미지 분석**: 스크린샷, 차트, 표 분석
- **실시간 처리**: 업로드 즉시 분석 및 시트 선택

### 💬 **지능형 대화 시스템**
- **연속성 감지**: 이전 대화 맥락 유지
- **문제 인식**: 사용자 수준에 따른 적응형 응답
- **하이브리드 처리**: 복잡한 작업의 다중 모델 협업

## 🛠 **기술 스택**

### **Backend**
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Python 3.11+**: 최신 Python 기능 활용
- **Uvicorn**: ASGI 서버

### **AI 모델**
- **Google Gemini 2.5 Pro**: 최고 성능 (복잡한 코딩, VBA)
- **Google Gemini 2.5 Flash**: 빠른 분석 (데이터 분석, 계획 수립)
- **Google Gemini 2.0 Flash**: 비용 효율 (초보자 친화적 설명)
- **OpenAI GPT-4o-mini**: 보조적 역할 (문제 해결, 최적화)

### **데이터 처리**
- **Pandas**: Excel 파일 처리 및 데이터 분석
- **OpenPyXL**: Excel 파일 읽기/쓰기
- **PIL**: 이미지 처리 및 분석

### **데이터베이스**
- **SQLite**: 세션 관리 및 대화 기록
- **Alembic**: 데이터베이스 마이그레이션

## 🚀 **설치 및 실행**

### **1. 저장소 클론**
```bash
git clone https://github.com/CHULJU-KIM/excelly.git
cd excelly
```

### **2. 가상환경 생성 및 활성화**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### **3. 의존성 설치**
```bash
pip install -r requirements.txt
```

### **4. 환경 변수 설정**
`.env` 파일을 생성하고 다음 내용을 추가:
```env
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### **5. 서버 실행**
```bash
python main.py
# 또는
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### **6. 웹 접속**
브라우저에서 `http://localhost:8000` 접속

## 📖 **사용 방법**

### **1. 파일 업로드**
- Excel 파일(.xlsx, .xls)을 드래그 앤 드롭 또는 파일 선택
- 자동으로 시트 목록 분석 및 표시

### **2. 시트 선택**
- 분석하고 싶은 시트 클릭
- 해당 시트의 데이터 구조 및 내용 자동 분석

### **3. 질문하기**
- **초보자**: "합계 어떻게 구하는지 모르겠어요"
- **중급자**: "매출 데이터를 월별로 분석하고 차트로 만들어주세요"
- **고급자**: "복잡한 VLOOKUP과 INDEX MATCH를 결합한 동적 함수와 VBA 매크로를 함께 만들어줘"

## 🎯 **AI 모델 분류 시스템**

### **자동 수준 분류**
```python
# 초보자 키워드 감지
beginner_keywords = [
    "모르겠", "모르는", "모름", "처음", "초보", "어떻게", "방법", "도와줘", 
    "안되", "안돼", "오류", "에러", "문제", "틀렸", "잘못", "이상해", "왜"
]

# 고급 사용자 키워드 감지  
advanced_keywords = [
    "vlookup", "index", "match", "pivot", "매크로", "vba", "함수조합", 
    "배열수식", "동적", "자동화", "최적화", "알고리즘"
]
```

### **모델 선택 전략**
- **beginner_help**: Gemini 2.0 Flash (친화적, 비용효율)
- **analysis**: Gemini 2.5 Flash (빠른 데이터 분석)
- **planning**: Gemini 2.5 Flash (구조화된 계획 수립)
- **coding**: Gemini 2.5 Pro (VBA, 복잡한 함수조합)
- **hybrid**: 2.5 Pro + OpenAI 조합 (최고 품질)

## 📁 **프로젝트 구조**

```
excelwizard-project/
├── app/
│   ├── api/
│   │   ├── chat.py          # 채팅 API 엔드포인트
│   │   └── files.py         # 파일 처리 API
│   ├── core/
│   │   ├── config.py        # 설정 관리
│   │   ├── database.py      # 데이터베이스 연결
│   │   └── exceptions.py    # 예외 처리
│   ├── models/
│   │   ├── chat.py          # 채팅 모델
│   │   ├── database.py      # 데이터베이스 모델
│   │   └── excel.py         # Excel 모델
│   ├── services/
│   │   ├── ai_service.py    # AI 서비스 (핵심)
│   │   ├── file_service.py  # 파일 처리 서비스
│   │   └── session_service.py # 세션 관리
│   └── main.py              # FastAPI 앱
├── static/                  # 정적 파일
├── templates/               # HTML 템플릿
├── prompts.py              # AI 프롬프트 정의
├── requirements.txt        # 의존성 목록
└── main.py                 # 실행 파일
```

## 🔧 **API 엔드포인트**

### **파일 분석**
- `POST /api/chat/analyze-sheets`: Excel 파일 업로드 및 시트 분석
- `POST /api/files/analyze`: 파일 상세 분석
- `POST /api/files/extract-sheet`: 특정 시트 데이터 추출

### **채팅**
- `POST /api/chat/ask`: AI 질의응답
- `GET /api/chat/sessions`: 세션 목록 조회
- `GET /api/chat/history/{session_id}`: 대화 기록 조회
- `GET /api/chat/status`: AI 서비스 상태 확인

### **이미지 처리**
- `POST /api/files/process-image`: 이미지 분석

## 🎨 **UI 기능**

### **메인 화면**
- 파일 업로드 영역
- AI 모델 상태 표시
- 실시간 채팅 인터페이스

### **파일 분석**
- 시트 목록 표시
- 시트별 데이터 미리보기
- 선택된 시트 하이라이트

### **채팅 인터페이스**
- 실시간 메시지 표시
- AI 응답 스타일 선택
- 대화 기록 저장

## 🔒 **보안 및 개인정보**

- **API 키 보안**: 환경 변수를 통한 안전한 관리
- **세션 관리**: 사용자별 독립적인 대화 세션
- **파일 처리**: 임시 저장 후 자동 삭제
- **데이터 보호**: 개인정보 수집 없음

## 🚀 **성능 최적화**

### **AI 모델 최적화**
- **비용 효율**: 난이도별 모델 선택으로 비용 최적화
- **응답 속도**: Flash 모델로 빠른 응답
- **품질 보장**: Pro 모델로 복잡한 작업 처리

### **파일 처리 최적화**
- **이미지 압축**: 업로드 시 자동 리사이징
- **메모리 관리**: 대용량 파일 처리 최적화
- **캐싱**: 세션별 파일 데이터 캐싱

## 🐛 **문제 해결**

### **일반적인 문제**
1. **서버 연결 안됨**: 포트 8000 확인, 방화벽 설정
2. **API 키 오류**: .env 파일 설정 확인
3. **파일 업로드 실패**: 파일 형식 및 크기 확인

### **로그 확인**
```bash
# 서버 로그 실시간 확인
tail -f logs/app.log
```

## 📈 **향후 계획**

### **단기 목표**
- [ ] 더 많은 Excel 함수 지원
- [ ] 차트 자동 생성 기능
- [ ] VBA 매크로 템플릿 추가

### **장기 목표**
- [ ] 실시간 협업 기능
- [ ] 모바일 앱 개발
- [ ] 엔터프라이즈 버전

## 🤝 **기여하기**

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 **라이선스**

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 **연락처**

- **프로젝트 링크**: [https://github.com/CHULJU-KIM/excelly](https://github.com/CHULJU-KIM/excelly)
- **이슈 리포트**: [GitHub Issues](https://github.com/CHULJU-KIM/excelly/issues)

## 🙏 **감사의 말**

- Google Gemini API 팀
- OpenAI API 팀
- FastAPI 개발팀
- 모든 기여자들

---

**ExcelWizard** - Excel 작업을 더욱 스마트하게! 🚀
