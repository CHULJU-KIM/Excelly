# app/services/ai_service.py
# AI model management service

import time
import asyncio
import json
from typing import Optional, Dict, Any, List, Tuple
from openai import AsyncOpenAI
import google.generativeai as genai
from PIL import Image
import io

from app.core.config import settings
from app.core.exceptions import AIServiceException
from app.models.chat import QuestionClassification, UserIntent, AIResponse, ConversationState
from prompts import PLANNING_PERSONA_PROMPT, CODING_PERSONA_PROMPT, DEBUGGING_PERSONA_PROMPT, PYTHON_PERSONA_PROMPT

class AIService:
    """Service for managing AI model interactions with intelligent routing"""
    
    def __init__(self):
        self.openai_client = None
        self.gemini_pro_model = None  # 2.5 Pro - 최상위 난이도
        self.gemini_2_5_flash_model = None  # 2.5 Flash - 중간 난이도
        self.gemini_2_0_flash_model = None  # 2.0 Flash - 일반 난이도
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AI clients with difficulty-based model selection"""
        try:
            # Initialize OpenAI client (auxiliary role)
            if settings.OPENAI_API_KEY:
                self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                print(f"✅ OpenAI 클라이언트 초기화 성공: {settings.OPENAI_MODEL}")
            
            # Initialize Gemini client
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                # Initialize Gemini 2.5 Pro (highest difficulty - creative, innovative)
                try:
                    self.gemini_pro_model = genai.GenerativeModel(settings.GEMINI_PRO_MODEL)
                    print(f"✅ Gemini 2.5 Pro 모델 초기화 성공: {settings.GEMINI_PRO_MODEL}")
                except Exception as e:
                    print(f"⚠️ Gemini 2.5 Pro 모델 초기화 실패: {e}")
                    try:
                        self.gemini_pro_model = genai.GenerativeModel(settings.GEMINI_2_0_PRO_FALLBACK)
                        print(f"✅ Gemini 2.0 Pro 모델로 대체: {settings.GEMINI_2_0_PRO_FALLBACK}")
                    except Exception as e2:
                        print(f"❌ Gemini Pro 계열 모델 초기화 실패: {e2}")
                        self.gemini_pro_model = None
                
                # Initialize Gemini 2.5 Flash (medium difficulty - complex analysis, planning)
                try:
                    self.gemini_2_5_flash_model = genai.GenerativeModel(settings.GEMINI_2_5_FLASH_MODEL)
                    print(f"✅ Gemini 2.5 Flash 모델 초기화 성공: {settings.GEMINI_2_5_FLASH_MODEL}")
                except Exception as e:
                    print(f"⚠️ Gemini 2.5 Flash 모델 초기화 실패: {e}")
                    try:
                        self.gemini_2_5_flash_model = genai.GenerativeModel(settings.GEMINI_1_5_FLASH_FALLBACK)
                        print(f"✅ Gemini 1.5 Flash 모델로 대체: {settings.GEMINI_1_5_FLASH_FALLBACK}")
                    except Exception as e2:
                        print(f"❌ Gemini 2.5 Flash 모델 초기화 실패: {e2}")
                        self.gemini_2_5_flash_model = None
                
                # Initialize Gemini 2.0 Flash (general difficulty - simple questions, classification)
                try:
                    self.gemini_2_0_flash_model = genai.GenerativeModel(settings.GEMINI_2_0_FLASH_MODEL)
                    print(f"✅ Gemini 2.0 Flash 모델 초기화 성공: {settings.GEMINI_2_0_FLASH_MODEL}")
                except Exception as e:
                    print(f"⚠️ Gemini 2.0 Flash 모델 초기화 실패: {e}")
                    try:
                        self.gemini_2_0_flash_model = genai.GenerativeModel(settings.GEMINI_1_5_FLASH_FALLBACK)
                        print(f"✅ Gemini 1.5 Flash 모델로 대체: {settings.GEMINI_1_5_FLASH_FALLBACK}")
                    except Exception as e2:
                        print(f"❌ Gemini 2.0 Flash 모델 초기화 실패: {e2}")
                        self.gemini_2_0_flash_model = None
                
        except Exception as e:
            print(f"⚠️ AI 클라이언트 초기화 중 오류: {str(e)}")
            # Don't raise exception, continue with available models
    
    async def classify_question(self, question: str, context: str = "") -> QuestionClassification:
        """User-level aware question classification with problem recognition"""
        try:
            # 사용자 수준 및 문제 유형 감지
            question_lower = question.lower().strip()
            
            # 초보자 표현 키워드 감지
            beginner_keywords = [
                "모르겠", "모르는", "모름", "처음", "초보", "어떻게", "방법", "도와줘", "도와주세요",
                "안되", "안돼", "오류", "에러", "문제", "틀렸", "잘못", "이상해", "왜",
                "뭐가", "어디서", "어떤", "무엇", "언제", "어느", "뭘", "뭔지"
            ]
            
            # 고급 사용자 표현 키워드 감지  
            advanced_keywords = [
                "vlookup", "index", "match", "pivot", "매크로", "vba", "함수조합", "배열수식",
                "동적", "자동화", "최적화", "알고리즘", "정규식", "api", "sql"
            ]
            
            # 파이썬 관련 키워드 감지 (파이썬 솔루션을 명시적으로 요청하는 경우)
            python_keywords = [
                "파이썬", "python", "pandas", "numpy", "matplotlib", "openpyxl", "xlrd",
                "스크립트", "프로그램", "코딩", "개발", "라이브러리", "모듈", "import",
                "데이터프레임", "dataframe", "시리즈", "series", "for문", "while문",
                "함수정의", "def", "클래스", "class", "객체", "object"
            ]
            
            # 복잡한 작업 키워드 감지 (고급 코딩/복잡한 로직)
            complex_keywords = [
                "복잡한", "고급", "정교한", "최적화", "성능", "대용량", "통합", "연동",
                "자동화", "매크로", "vba", "스크립트", "프로그램", "함수조합", "배열수식",
                "동적", "실시간", "다중", "병렬", "비동기", "이벤트", "콜백"
            ]
            
            # 대화 연결성 키워드 감지
            continuation_keywords = [
                "계속", "계속해", "이어서", "그리고", "또한", "추가로", "더", "다음",
                "위에서", "앞에서", "이전", "방금", "아까", "그거", "그것", "이것"
            ]
            
            # 사용자 수준 판단
            is_beginner = any(keyword in question_lower for keyword in beginner_keywords)
            is_advanced = any(keyword in question_lower for keyword in advanced_keywords)
            is_complex = any(keyword in question_lower for keyword in complex_keywords)
            is_continuation = any(keyword in question for keyword in continuation_keywords)
            is_python_request = any(keyword in question_lower for keyword in python_keywords)
            has_context = bool(context and context.strip())
            
            # 문제 유형 분석
            problem_indicators = {
                "formula_error": ["#n/a", "#value", "#ref", "#div/0", "#name", "오류", "에러"],
                "data_issue": ["중복", "빈칸", "공백", "누락", "정렬", "필터"],
                "calculation": ["합계", "평균", "개수", "최대", "최소", "계산"],
                "lookup": ["찾기", "검색", "조회", "매칭", "일치"],
                "formatting": ["서식", "색깔", "굵게", "정렬", "크기"],
                "automation": ["자동", "반복", "일괄", "한번에", "매크로"]
            }
            
            detected_problems = []
            for problem_type, indicators in problem_indicators.items():
                if any(indicator in question_lower for indicator in indicators):
                    detected_problems.append(problem_type)
            
            # 분류 로직 개선 (파이썬 요청 우선 처리)
            if is_python_request:
                classification = "python_coding"  # 파이썬 전용 분류
                confidence = 0.95
                recommended_model = "gemini_pro"
            elif is_continuation and has_context:
                classification = "continuation"
                confidence = 0.9
                recommended_model = "gemini_2_5_flash"
            elif is_complex or (is_advanced and len(detected_problems) > 2):
                classification = "advanced_coding"  # 새로운 분류
                confidence = 0.9
                recommended_model = "gemini_pro"
            elif is_beginner or not detected_problems:
                classification = "beginner_help"
                confidence = 0.8
                recommended_model = "gemini_2_0_flash"
            elif "automation" in detected_problems or is_advanced:
                classification = "coding"
                confidence = 0.8
                recommended_model = "gemini_2_5_flash"
            elif len(detected_problems) > 2:
                classification = "hybrid"
                confidence = 0.7
                recommended_model = "gemini_2_5_flash"
            elif "lookup" in detected_problems or "calculation" in detected_problems:
                classification = "analysis"
                confidence = 0.7
                recommended_model = "gemini_2_5_flash"
            else:
                classification = "simple"
                confidence = 0.6
                recommended_model = "gemini_2_0_flash"
            
            return QuestionClassification(
                classification=classification,
                confidence=confidence,
                reasoning=f"사용자 수준: {'초보' if is_beginner else '고급' if is_advanced else '일반'}, 복잡도: {'복잡' if is_complex else '일반'}, 감지된 문제: {detected_problems}",
                recommended_model=recommended_model,
                estimated_tokens=500,
                needs_clarification=False,
                clarification_reasons=[]
            )
            
        except Exception as e:
            return QuestionClassification(
                classification="beginner_help",
                confidence=0.5,
                reasoning=f"분류 실패, 초보자 모드로 처리: {str(e)}",
                recommended_model="gemini_2_0_flash",
                estimated_tokens=500
            )
    
    def _fallback_classification(self, response: str) -> str:
        """Fallback classification when JSON parsing fails"""
        response_lower = response.lower()
        if any(word in response_lower for word in ["beginner", "초보", "모르", "도와", "어떻게"]):
            return "beginner_help"
        elif any(word in response_lower for word in ["coding", "vba", "매크로", "코드", "함수"]):
            return "coding"
        elif any(word in response_lower for word in ["analysis", "분석", "통계", "데이터"]):
            return "analysis"
        elif any(word in response_lower for word in ["planning", "계획", "구조", "설계"]):
            return "planning"
        elif any(word in response_lower for word in ["simple", "간단", "기본"]):
            return "simple"
        elif any(word in response_lower for word in ["hybrid", "복합", "조합"]):
            return "hybrid"
        elif any(word in response_lower for word in ["continuation", "연결", "이어", "계속"]):
            return "continuation"
        elif any(word in response_lower for word in ["debugging", "오류", "문제"]):
            return "debugging"
        else:
            return "beginner_help"  # Default to beginner help
    
    async def analyze_user_intent(self, plan: str, user_reply: str) -> UserIntent:
        """Analyze user's intent using Gemini 2.0 Flash (optimized for fast analysis)"""
        try:
            prompt = f"""AI의 계획: "{plan[:200]}..."
사용자 답변: "{user_reply}"

사용자 답변을 분석하여 의도를 파악하세요:
- "agreement": 계획에 동의하고 진행
- "modification": 계획 수정 요청
- "clarification": 추가 설명 요청
- "rejection": 계획 거부

다음 JSON 형식으로 답하세요:
{{
    "intent": "agreement|modification|clarification|rejection",
    "confidence": 0.0-1.0,
    "reasoning": "의도 분석 이유"
}}"""
            
            # Use Gemini 2.0 Flash for intent analysis (fastest and most cost-effective)
            if self.gemini_2_0_flash_model:
                response = await self._call_gemini_2_0_flash(prompt, temperature=0.0)
            else:
                response = await self._call_openai(prompt, model="gpt-4o-mini", temperature=0.0)
            
            try:
                result = json.loads(response)
                return UserIntent(
                    intent=result.get("intent", "other"),
                    confidence=result.get("confidence", 0.5),
                    reasoning=result.get("reasoning", "")
                )
            except json.JSONDecodeError:
                intent = self._fallback_intent_analysis(response)
                return UserIntent(
                    intent=intent,
                    confidence=0.7,
                    reasoning="JSON 파싱 실패로 기본 분석 사용"
                )
                
        except Exception as e:
            return UserIntent(
                intent="other",
                confidence=0.5,
                reasoning=f"의도 분석 실패: {str(e)}"
            )
    
    def _fallback_intent_analysis(self, response: str) -> str:
        """Fallback intent analysis when JSON parsing fails"""
        response_lower = response.lower()
        if any(word in response_lower for word in ["agreement", "동의", "좋다", "진행"]):
            return "agreement"
        elif any(word in response_lower for word in ["modification", "수정", "변경"]):
            return "modification"
        elif any(word in response_lower for word in ["clarification", "설명", "이해"]):
            return "clarification"
        elif any(word in response_lower for word in ["rejection", "거부", "아니"]):
            return "rejection"
        else:
            return "other"
    

    
    async def generate_simple_response(self, question: str, answer_style: Optional[str] = None) -> str:
        """Generate simple response using Gemini 2.0 Flash (cost-effective for basic queries)"""
        try:
            prompt = f"""Excel 질문에 간결하게 답변하세요: {question}

**출력 형식**:
📝 **핵심 설명** (2-3줄)
💡 **구체적 예시** (필요시)
⚡ **추가 팁** (1줄)"""
            
            if answer_style == "concise":
                prompt += "\n\n[스타일] 핵심만 3줄 이내"
            
            # Use Gemini 2.0 Flash for basic queries (fastest and most cost-effective)
            if self.gemini_2_0_flash_model:
                print("🤖 기본 질의 처리: Gemini 2.0 Flash 사용")
                return await self._call_gemini_2_0_flash(prompt, temperature=0.3)
            elif self.gemini_2_5_flash_model:
                print("🤖 기본 질의 처리: Gemini 2.5 Flash 폴백")
                return await self._call_gemini_2_5_flash(prompt, temperature=0.3)
            else:
                print("🤖 기본 질의 처리: OpenAI 폴백")
                return await self._call_openai(prompt, model="gpt-4o-mini", temperature=0.3)
            
        except Exception as e:
            raise AIServiceException(f"간단한 답변 생성 실패: {str(e)}")
    
    async def generate_coding_response(self, question: str, context: str, file_summary: str, answer_style: Optional[str] = None) -> str:
        """Generate coding response using Gemini 2.5 Flash (optimized for basic formulas and coding)"""
        try:
            prompt = f"""Excel 코딩 작업을 해결해주세요.

**질문**: {question}
**파일 정보**: {file_summary}

**출력 형식**:
🔧 **코드 구조** (VBA/함수 설계)
📋 **구현 코드** (완전한 코드)
📖 **사용 방법** (단계별 설명)
⚠️ **주의사항** (코드 실행 시 주의점)
🚀 **최적화 팁** (성능 개선 방안)"""
            
            if answer_style == "concise":
                prompt += "\n\n[스타일] 핵심만 5줄 이내"
            
            # Use Gemini 2.5 Flash for basic coding (fast and accurate)
            if self.gemini_2_5_flash_model:
                print("🔧 기본 수식/코딩 처리: Gemini 2.5 Flash 사용")
                return await self._call_gemini_2_5_flash(prompt, temperature=0.3)
            elif self.gemini_pro_model:
                print("🔧 기본 수식/코딩 처리: Gemini 2.5 Pro 폴백")
                return await self._call_gemini_pro(prompt, temperature=0.3)
            else:
                print("🔧 기본 수식/코딩 처리: OpenAI 폴백")
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.3)
            
        except Exception as e:
            raise AIServiceException(f"코딩 답변 생성 실패: {str(e)}")
    
    async def generate_advanced_coding_response(self, question: str, context: str, file_summary: str, answer_style: Optional[str] = None) -> str:
        """Generate advanced coding response using Gemini 2.5 Pro (for complex VBA and advanced functions)"""
        try:
            prompt = f"""고급 Excel 코딩 작업을 해결해주세요.

**질문**: {question}
**파일 정보**: {file_summary}

**출력 형식**:
🎯 **고급 접근법** (복잡한 로직 설계)
🔧 **정교한 코드** (최적화된 VBA/함수)
📖 **상세한 가이드** (단계별 설명)
⚠️ **고급 주의사항** (복잡한 시나리오 고려)
🚀 **성능 최적화** (대용량 데이터 처리)
💡 **확장성 고려** (재사용 가능한 구조)"""
            
            if answer_style == "concise":
                prompt += "\n\n[스타일] 핵심만 5줄 이내"
            
            # Use Gemini 2.5 Pro for advanced coding (highest quality)
            if self.gemini_pro_model:
                print("🚀 고급/복잡한 작업 처리: Gemini 2.5 Pro 사용")
                return await self._call_gemini_pro(prompt, temperature=0.3)
            elif self.gemini_2_5_flash_model:
                print("🚀 고급/복잡한 작업 처리: Gemini 2.5 Flash 폴백")
                return await self._call_gemini_2_5_flash(prompt, temperature=0.3)
            else:
                print("🚀 고급/복잡한 작업 처리: OpenAI 폴백")
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.3)
            
        except Exception as e:
            raise AIServiceException(f"고급 코딩 답변 생성 실패: {str(e)}")
    
    async def generate_analysis_response(self, question: str, context: str, file_summary: str, answer_style: Optional[str] = None) -> str:
        """Generate analysis response using Gemini 2.5 Flash (optimized for data analysis)"""
        try:
            prompt = f"""Excel 데이터 분석을 수행해주세요.

**질문**: {question}
**파일 정보**: {file_summary}

**출력 형식**:
🔍 **분석 방법** (접근법 설명)
📊 **분석 결과** (구체적 결과)
📈 **시각화 제안** (차트/그래프)
💡 **인사이트** (발견된 패턴)
🎯 **추천사항** (다음 단계)"""
            
            if answer_style == "concise":
                prompt += "\n\n[스타일] 핵심만 5줄 이내"
            
            # Use Gemini 2.5 Flash for analysis (fast and accurate)
            if self.gemini_2_5_flash_model:
                return await self._call_gemini_2_5_flash(prompt, temperature=0.5)
            elif self.gemini_2_0_flash_model:
                return await self._call_gemini_2_0_flash(prompt, temperature=0.5)
            else:
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.5)
            
        except Exception as e:
            raise AIServiceException(f"분석 답변 생성 실패: {str(e)}")
    
    async def generate_planning_response(self, context: str, file_summary: str = "", answer_style: Optional[str] = None) -> str:
        """Generate planning response using Gemini 2.5 Flash (structured thinking)"""
        try:
            style_guard = "\n\n[응답 스타일] 핵심만 간결히 5줄 이내로 요약" if (answer_style=="concise") else ""
            prompt = f"{PLANNING_PERSONA_PROMPT}{style_guard}\n\n--- Conversation History ---\n{context}\n\n{file_summary}"
            
            # Use Gemini 2.5 Flash for planning (structured thinking)
            if self.gemini_2_5_flash_model:
                return await self._call_gemini_2_5_flash(prompt, temperature=0.7)
            elif self.gemini_2_0_flash_model:
                return await self._call_gemini_2_0_flash(prompt, temperature=0.7)
            else:
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.7)
            
        except Exception as e:
            raise AIServiceException(f"계획 생성 실패: {str(e)}")
    
    async def generate_hybrid_response(self, question: str, context: str, file_summary: str, answer_style: Optional[str] = None) -> str:
        """Generate hybrid response using multiple models for best quality"""
        try:
            # Step 1: Use Gemini 2.5 Pro for initial solution
            initial_prompt = f"""Excel 작업의 핵심 해결책을 제시해주세요: {question}

파일 정보: {file_summary}

**출력 형식**:
🎯 **핵심 접근법** (2줄)
🔧 **주요 해결책** (3줄)
📋 **구현 방법** (2줄)"""
            
            if self.gemini_pro_model:
                initial_response = await self._call_gemini_pro(initial_prompt, temperature=0.5)
            else:
                initial_response = await self._call_openai(initial_prompt, model=settings.OPENAI_MODEL, temperature=0.5)
            
            # Step 2: Use OpenAI for refinement and optimization
            refinement_prompt = f"""다음 Excel 해결책을 최적화하고 보완해주세요:

**원본 해결책**:
{initial_response}

**요청사항**: {question}

**최적화 요청**:
1. 코드 품질 향상
2. 오류 처리 추가
3. 성능 최적화
4. 사용자 친화적 설명

**출력 형식**:
✅ **최적화된 해결책** (개선된 코드/방법)
🔍 **상세 설명** (단계별 가이드)
⚠️ **주의사항** (실행 시 주의점)
💡 **추가 팁** (고급 활용법)"""
            
            if self.openai_client:
                refined_response = await self._call_openai(refinement_prompt, model=settings.OPENAI_MODEL, temperature=0.3)
            else:
                refined_response = initial_response
            
            # Step 3: Combine and format final response
            final_response = f"""🚀 **하이브리드 AI 최적화 솔루션**

{refined_response}

---
*이 답변은 Gemini 2.5 Pro와 OpenAI의 장점을 결합하여 생성되었습니다.*"""
            
            return final_response
            
        except Exception as e:
            raise AIServiceException(f"하이브리드 답변 생성 실패: {str(e)}")
    
    async def generate_python_response(self, question: str, context: str, file_summary: str, answer_style: Optional[str] = None) -> str:
        """Generate Python-specific response using Python persona prompt"""
        try:
            style_guard = "\n\n[응답 스타일] 핵심만 간결히 5줄 이내로 요약" if (answer_style=="concise") else ""
            prompt = f"{PYTHON_PERSONA_PROMPT}{style_guard}\n\n--- Conversation History ---\n{context}\n\n--- File Analysis ---\n{file_summary}\n\n--- Current Question ---\n{question}"
            
            # Use Gemini Pro for Python coding (highest capability)
            if self.gemini_pro_model:
                return await self._call_gemini_pro(prompt, temperature=0.3)
            elif self.gemini_2_5_flash_model:
                return await self._call_gemini_2_5_flash(prompt, temperature=0.3)
            else:
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.3)
            
        except Exception as e:
            raise AIServiceException(f"파이썬 답변 생성 실패: {str(e)}")
    
    async def generate_continuation_response(self, question: str, context: str, file_summary: str, answer_style: Optional[str] = None) -> str:
        """Generate continuation response maintaining conversation context"""
        try:
            prompt = f"""이전 대화와 연결하여 답변해주세요.

**현재 질문**: {question}
**이전 대화**: {context}
**파일 정보**: {file_summary}

**출력 형식**:
🔗 **연결된 내용** (이전 대화와의 연결점)
📝 **추가 설명** (현재 질문에 대한 답변)
🎯 **구체적 방법** (실행 가능한 단계)
💡 **보완 사항** (추가로 고려할 점)

이전 대화의 맥락을 유지하면서 자연스럽게 이어가세요."""
            
            if answer_style == "concise":
                prompt += "\n\n[스타일] 핵심만 5줄 이내"
            
            # Use Gemini 2.5 Flash for continuation (context-aware processing)
            if self.gemini_2_5_flash_model:
                return await self._call_gemini_2_5_flash(prompt, temperature=0.6)
            elif self.gemini_2_0_flash_model:
                return await self._call_gemini_2_0_flash(prompt, temperature=0.6)
            else:
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.6)
            
        except Exception as e:
            raise AIServiceException(f"연결 답변 생성 실패: {str(e)}")
    
    async def generate_beginner_response(self, question: str, context: str, file_summary: str, answer_style: Optional[str] = None) -> str:
        """Generate beginner-friendly response with problem understanding"""
        try:
            # 문제 상황을 이해하고 쉬운 해결책 제시
            prompt = f"""초보자를 위한 Excel 문제 해결 도우미로서 답변해주세요.

**사용자 질문**: {question}
**파일 정보**: {file_summary}

**답변 방식**:
1. 먼저 사용자가 겪고 있는 문제 상황을 정확히 파악하고 공감해주세요
2. 전문 용어는 쉬운 말로 풀어서 설명해주세요  
3. 단계별로 따라할 수 있도록 구체적으로 안내해주세요
4. 왜 그렇게 해야 하는지 이유도 간단히 설명해주세요

**출력 형식**:
😊 **문제 파악**: (사용자 상황 이해 및 공감)
📝 **쉬운 설명**: (전문용어 없이 쉽게 설명)
👆 **따라하기**: (1단계, 2단계... 구체적 안내)
💡 **추가 팁**: (실수하기 쉬운 부분이나 유용한 팁)
🤔 **더 궁금하다면**: (관련해서 더 물어볼 수 있는 것들)

친근하고 이해하기 쉽게, 마치 옆에서 직접 도와주는 것처럼 설명해주세요."""
            
            if answer_style == "concise":
                prompt += "\n\n[스타일] 핵심만 간단히 3단계 이내"
            
            # Use Gemini 2.0 Flash for beginner-friendly responses (cost-effective and gentle)
            if self.gemini_2_0_flash_model:
                return await self._call_gemini_2_0_flash(prompt, temperature=0.4)
            elif self.gemini_2_5_flash_model:
                return await self._call_gemini_2_5_flash(prompt, temperature=0.4)
            else:
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.4)
            
        except Exception as e:
            raise AIServiceException(f"초보자 답변 생성 실패: {str(e)}")
    
    async def handle_problem_report(self, previous_answer: str, user_feedback: str, context: str = "") -> str:
        """Handle 'problem report' button functionality for answer refinement"""
        try:
            prompt = f"""사용자가 이전 답변에 문제가 있다고 보고했습니다. 개선된 답변을 제공하세요.

**이전 답변**: {previous_answer}
**사용자 피드백**: {user_feedback}
**대화 맥락**: {context}

**개선 요청사항**:
1. 이전 답변의 문제점 분석
2. 사용자 피드백 반영
3. 더 정확하고 실용적인 해결책 제시
4. 단계별 검증 방법 포함

**출력 형식**:
🔍 **문제점 분석** (이전 답변의 부족한 부분)
✅ **개선된 해결책** (수정된 방법)
📋 **단계별 가이드** (구체적 실행 방법)
🧪 **검증 방법** (결과 확인 방법)
⚠️ **주의사항** (실행 시 주의점)

더 신중하고 검증된 답변을 제공해주세요."""
            
            # Use hybrid approach for problem resolution (highest quality)
            if self.gemini_pro_model and self.openai_client:
                # Step 1: Gemini 2.5 Pro for analysis
                analysis_response = await self._call_gemini_pro(prompt, temperature=0.3)
                
                # Step 2: OpenAI for refinement
                refinement_prompt = f"""다음 분석을 바탕으로 최종 개선안을 제시하세요:

{analysis_response}

사용자의 구체적 요구사항을 완전히 충족하는 실용적인 해결책을 제공하세요."""
                
                refined_response = await self._call_openai(refinement_prompt, model=settings.OPENAI_MODEL, temperature=0.2)
                
                return f"""🚨 **문제 해결 - 개선된 답변**

{refined_response}

---
*이 답변은 사용자 피드백을 반영하여 Gemini 2.5 Pro와 OpenAI가 협력하여 개선했습니다.*"""
                
            elif self.gemini_pro_model:
                return await self._call_gemini_pro(prompt, temperature=0.3)
            else:
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.3)
            
        except Exception as e:
            raise AIServiceException(f"문제 해결 답변 생성 실패: {str(e)}")

    
    async def generate_debugging_response(self, context: str, feedback: str, image_data: Optional[bytes] = None) -> str:
        """Generate debugging response using OpenAI (optimized for problem-solving)"""
        try:
            # If image is provided, use Gemini 2.0 Flash for image analysis
            image_analysis = ""
            if image_data:
                if self.gemini_2_0_flash_model or self.gemini_2_5_flash_model:
                    try:
                        image_analysis = await self._analyze_image_with_gemini(image_data)
                    except Exception as e:
                        image_analysis = f"[이미지 분석 실패: {str(e)}]"
                else:
                    image_analysis = "[이미지가 첨부되었습니다. VLOOKUP 서식 불일치 문제로 추정됩니다.]"
            
            # Add debugging persona prompt with feedback acknowledgment
            debugging_prompt = f"""아이고, 제가 드린 방법이 통하지 않았군요. 정말 죄송해요! 😭 사용자의 피드백을 잘 받았고, 함께 문제를 해결해 보도록 할게요.

{DEBUGGING_PERSONA_PROMPT}

--- Previous Context ---
{context}

--- User Feedback ---
{feedback}

--- Image Analysis ---
{image_analysis}"""
            
            # Use OpenAI for debugging (best at problem-solving and code analysis)
            return await self._call_openai(debugging_prompt, model=settings.OPENAI_MODEL, temperature=0.5)
            
        except Exception as e:
            raise AIServiceException(f"디버깅 응답 생성 실패: {str(e)}")
    
    async def _call_openai(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        """Make OpenAI API call with enhanced error handling"""
        if not self.openai_client:
            raise AIServiceException("OpenAI 클라이언트가 초기화되지 않았습니다.")
        
        try:
            response = await asyncio.wait_for(
                self.openai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=settings.MAX_TOKENS
                ),
                timeout=settings.AI_REQUEST_TIMEOUT
            )
            
            return response.choices[0].message.content.strip()
            
        except asyncio.TimeoutError:
            raise AIServiceException("OpenAI 응답 시간 초과")
        except Exception as e:
            raise AIServiceException(f"OpenAI API 호출 실패: {str(e)}")
    
    async def _call_gemini_pro(self, prompt: str, temperature: float = 0.7) -> str:
        """Make Gemini 2.5 Pro API call (highest difficulty)"""
        if not self.gemini_pro_model:
            print("❌ Gemini 2.5 Pro 모델이 초기화되지 않음")
            raise AIServiceException("Gemini 2.5 Pro 모델이 초기화되지 않았습니다.")
        
        try:
            print(f"🚀 Gemini 2.5 Pro API 호출 시작 (프롬프트 길이: {len(prompt)} 문자)")
            response = await asyncio.wait_for(
                self.gemini_pro_model.generate_content_async(prompt),
                timeout=settings.AI_REQUEST_TIMEOUT
            )
            print(f"✅ Gemini 2.5 Pro 응답 성공 (응답 길이: {len(response.text)} 문자)")
            return response.text.strip()
        except asyncio.TimeoutError:
            print("⏰ Gemini 2.5 Pro 응답 시간 초과")
            raise AIServiceException("Gemini 2.5 Pro 응답 시간 초과")
        except Exception as e:
            print(f"❌ Gemini 2.5 Pro API 호출 실패: {str(e)}")
            raise AIServiceException(f"Gemini 2.5 Pro API 호출 실패: {str(e)}")
    
    async def _call_gemini_2_5_flash(self, prompt: str, temperature: float = 0.7) -> str:
        """Make Gemini 2.5 Flash API call (medium difficulty)"""
        if not self.gemini_2_5_flash_model:
            print("❌ Gemini 2.5 Flash 모델이 초기화되지 않음")
            raise AIServiceException("Gemini 2.5 Flash 모델이 초기화되지 않았습니다.")
        
        try:
            print(f"🚀 Gemini 2.5 Flash API 호출 시작 (프롬프트 길이: {len(prompt)} 문자)")
            response = await asyncio.wait_for(
                self.gemini_2_5_flash_model.generate_content_async(prompt),
                timeout=45  # Medium timeout
            )
            print(f"✅ Gemini 2.5 Flash 응답 성공 (응답 길이: {len(response.text)} 문자)")
            return response.text.strip()
        except asyncio.TimeoutError:
            print("⏰ Gemini 2.5 Flash 응답 시간 초과, 2.0 Flash로 폴백")
            # Fallback to 2.0 Flash
            try:
                return await self._call_gemini_2_0_flash(prompt, temperature)
            except Exception as e2:
                print(f"❌ Gemini 2.5 Flash 폴백 실패: {str(e2)}")
                raise AIServiceException(f"Gemini 2.5 Flash 응답 시간 초과 및 폴백 실패: {str(e2)}")
        except Exception as e:
            print(f"❌ Gemini 2.5 Flash API 호출 실패: {str(e)}, 2.0 Flash로 폴백")
            # Fallback to 2.0 Flash
            try:
                return await self._call_gemini_2_0_flash(prompt, temperature)
            except Exception as e2:
                print(f"❌ Gemini 2.5 Flash 폴백 실패: {str(e2)}")
                raise AIServiceException(f"Gemini 2.5 Flash API 실패 및 폴백 실패: {str(e2)}")
    
    async def _call_gemini_2_0_flash(self, prompt: str, temperature: float = 0.7) -> str:
        """Make Gemini 2.0 Flash API call (general difficulty)"""
        if not self.gemini_2_0_flash_model:
            print("❌ Gemini 2.0 Flash 모델이 초기화되지 않음")
            raise AIServiceException("Gemini 2.0 Flash 모델이 초기화되지 않았습니다.")
        
        try:
            print(f"🚀 Gemini 2.0 Flash API 호출 시작 (프롬프트 길이: {len(prompt)} 문자)")
            response = await asyncio.wait_for(
                self.gemini_2_0_flash_model.generate_content_async(prompt),
                timeout=30  # Fast timeout
            )
            print(f"✅ Gemini 2.0 Flash 응답 성공 (응답 길이: {len(response.text)} 문자)")
            return response.text.strip()
        except asyncio.TimeoutError:
            print("⏰ Gemini 2.0 Flash 응답 시간 초과, OpenAI로 폴백")
            # Fallback to OpenAI
            try:
                return await self._call_openai(prompt, model="gpt-4o-mini", temperature=temperature)
            except Exception as e2:
                print(f"❌ Gemini 2.0 Flash OpenAI 폴백 실패: {str(e2)}")
                raise AIServiceException(f"Gemini 2.0 Flash 응답 시간 초과 및 OpenAI 폴백 실패: {str(e2)}")
        except Exception as e:
            print(f"❌ Gemini 2.0 Flash API 호출 실패: {str(e)}, OpenAI로 폴백")
            # Fallback to OpenAI
            try:
                return await self._call_openai(prompt, model="gpt-4o-mini", temperature=temperature)
            except Exception as e2:
                print(f"❌ Gemini 2.0 Flash OpenAI 폴백 실패: {str(e2)}")
                raise AIServiceException(f"Gemini 2.0 Flash API 실패 및 OpenAI 폴백 실패: {str(e2)}")
    
    async def _analyze_image_with_gemini(self, image_data: bytes) -> str:
        """Analyze Excel image using optimized Gemini Flash models with enhanced prompts"""
        # 우선순위: Gemini 2.0 Flash > Gemini 2.5 Flash > Gemini Pro
        # Flash 모델이 이미지 분석에 최적화되어 있음
        model_to_use = None
        
        # 1순위: Gemini 2.0 Flash (가장 빠르고 비용 효율적 - 기초 이미지 처리)
        if self.gemini_2_0_flash_model:
            model_to_use = self.gemini_2_0_flash_model
            print("🖼️ 이미지 분석: Gemini 2.0 Flash 사용 (기초 이미지 처리)")
        # 2순위: Gemini 2.5 Flash (더 정확한 분석)
        elif self.gemini_2_5_flash_model:
            model_to_use = self.gemini_2_5_flash_model
            print("🖼️ 이미지 분석: Gemini 2.5 Flash 사용")
        # 3순위: Gemini Pro (최고 품질, 하지만 느림)
        elif self.gemini_pro_model:
            model_to_use = self.gemini_pro_model
            print("🖼️ 이미지 분석: Gemini Pro 사용")
        
        if not model_to_use:
            return "[이미지 분석 기능을 사용할 수 없습니다. Gemini API 키가 필요합니다.]"
        
        try:
            image = Image.open(io.BytesIO(image_data))
            print(f"🖼️ 이미지 크기: {image.width}x{image.height}, 형식: {image.format}")
            
            # 이미지 최적화 (Flash 모델에 최적화)
            if image.width > 1920 or image.height > 1080:
                image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                print(f"🖼️ 이미지 크기 조정: {image.width}x{image.height}")
            
            # Flash 모델에 최적화된 프롬프트
            prompt = """Excel 화면 이미지를 정확하게 분석해주세요:

**분석 요청사항**:
1. 화면에 표시된 Excel 기능이나 오류 메시지 식별
2. 데이터 구조와 셀 내용 파악
3. 발견된 문제점과 오류 원인 분석
4. 구체적인 해결 방법 제시

**출력 형식**:
🖼️ **화면 내용**: (Excel 기능, 시트명, 주요 요소)
📋 **데이터 분석**: (셀 범위, 데이터 타입, 수식 등)
⚠️ **발견된 문제**: (오류 메시지, 서식 불일치, 공백 등)
🔧 **해결 방안**: (단계별 해결책, 수식 수정, 설정 변경 등)
💡 **추가 제안**: (최적화 방법, 주의사항)

특히 VLOOKUP, INDEX/MATCH, 조건부 서식, 데이터 검증 관련 문제를 중점적으로 분석해주세요."""
            
            # Flash 모델에 최적화된 타임아웃 설정
            timeout = 30 if model_to_use == self.gemini_2_0_flash_model else 45
            
            response = await asyncio.wait_for(
                model_to_use.generate_content_async([prompt, image]),
                timeout=timeout
            )
            
            result = response.text.strip()
            print(f"🖼️ 이미지 분석 완료: {len(result)} 문자")
            return result
            
        except asyncio.TimeoutError:
            print("⏰ 이미지 분석 시간 초과")
            return "[이미지 분석 시간 초과: 이미지가 너무 복잡하거나 크기가 큽니다.]"
        except Exception as e:
            print(f"❌ 이미지 분석 실패: {e}")
            return f"[이미지 분석 실패: {str(e)}. 이미지 형식을 확인해주세요.]"
    
    async def process_chat_request(
        self, 
        question: str, 
        context: str, 
        file_summary: str = "",
        is_feedback: bool = False,
        image_data: Optional[bytes] = None,
        conversation_context: Optional[Any] = None,
        answer_style: Optional[str] = None
    ) -> AIResponse:
        """Process complete chat request with intelligent model routing"""
        start_time = time.time()
        
        try:
            if is_feedback:
                # Handle feedback with debugging persona
                answer = await self.generate_debugging_response(context, question, image_data)
                model_used = "OpenAI GPT-4o"
                response_type = "normal"
                next_action = None
                conversation_state = None
            else:
                # Special flow: if a sheet was selected and we have file summary, provide detailed analysis
                if (file_summary and file_summary.strip()) and (
                    (not question) or 
                    question.strip().startswith("[시트선택]") or
                    (len(question.strip()) <= 2 and question.strip().isdigit())
                ):
                    # Extract sheet name from file summary
                    sheet_name = "선택된 시트"
                    if "선택된 시트: '" in file_summary:
                        start_idx = file_summary.find("선택된 시트: '") + len("선택된 시트: '")
                        end_idx = file_summary.find("'", start_idx)
                        if end_idx > start_idx:
                            sheet_name = file_summary[start_idx:end_idx]
                    
                    answer = f"""📊 **{sheet_name} 시트 분석 완료!**

{file_summary}

---

🎯 **이제 무엇을 도와드릴까요?**

1️⃣ **수식/함수 만들기** - VLOOKUP, SUMIF, INDEX/MATCH 등
2️⃣ **데이터 정리** - 중복 제거, 정렬, 필터링
3️⃣ **요약/분석** - 피벗 테이블, 통계 분석
4️⃣ **시각화** - 차트, 그래프 만들기
5️⃣ **자동화** - VBA 매크로, 반복 작업 자동화

번호로 답하시거나, 구체적으로 원하시는 작업을 말씀해 주세요!
예: "A열의 중복을 제거하고 B열로 정렬해줘" 또는 "매출 데이터로 피벗 테이블 만들어줘"
"""
                    model_used = "conversation"
                    response_type = "clarification"
                    next_action = "wait_for_clarification"
                    conversation_state = ConversationState.CLARIFYING
                    
                    processing_time = time.time() - start_time
                    return AIResponse(
                        answer=answer,
                        session_id="",
                        model_used=model_used,
                        processing_time=processing_time,
                        response_type=response_type,
                        next_action=next_action,
                        conversation_state=conversation_state
                    )
                
                # Check if user selected a task option (1-5)
                elif file_summary and file_summary.strip() and question.strip() in ["1", "2", "3", "4", "5"]:
                    # User selected a task option
                    task_map = {
                        "1": "수식/함수 만들기",
                        "2": "데이터 정리", 
                        "3": "요약/분석",
                        "4": "시각화",
                        "5": "자동화"
                    }
                    selected_task = task_map[question.strip()]
                    
                    answer = f"""🎯 **{selected_task} 작업을 선택하셨습니다!**

{self._get_task_examples(selected_task)}

**구체적으로 어떤 작업을 원하시나요?**
예시를 참고하여 자세히 말씀해 주세요.

예: "VLOOKUP으로 다른 시트에서 데이터 가져오기" 또는 "중복 데이터 제거하고 정렬하기"
"""
                    model_used = "conversation"
                    response_type = "clarification"
                    next_action = "wait_for_task_details"
                    conversation_state = ConversationState.CLARIFYING
                    
                    processing_time = time.time() - start_time
                    return AIResponse(
                        answer=answer,
                        session_id="",
                        model_used=model_used,
                        processing_time=processing_time,
                        response_type=response_type,
                        next_action=next_action,
                        conversation_state=conversation_state
                    )
                
                # Process with AI based on question complexity
                else:
                    # Check for file generation request first
                    if self._is_file_generation_request(question):
                        print("📁 파일 생성 요청 감지됨")
                        # Use Gemini 2.5 Pro for file generation (complex analysis)
                        ai_response = await self._generate_solution_with_context(
                            question, question, context, file_summary
                        )
                        answer = ai_response.answer
                        model_used = ai_response.model_used
                        response_type = "file_generation"
                        next_action = "generate_file"
                        conversation_state = ai_response.conversation_state
                        model_info = ai_response.model_info
                    elif image_data:
                        # 이미지가 첨부된 Excel 질문 처리
                        print("🖼️ 이미지가 첨부된 Excel 질문: 이미지 분석 + Excel 해결책 제공")
                        
                        # 이미지 분석 수행
                        image_analysis = await self._analyze_image_with_gemini(image_data)
                        
                        # Excel 질문에 대한 해결책 생성
                        enhanced_question = f"{question}\n\n[이미지 분석 결과]\n{image_analysis}"
                        
                        # Excel 해결책 생성 (이미지 분석 결과 포함)
                        if self._is_complex_task(question):
                            print("🚀 복잡한 Excel 작업: Gemini 2.5 Pro 사용")
                            ai_response = await self._generate_solution_with_context(
                                enhanced_question, enhanced_question, context, file_summary
                            )
                            answer = ai_response.answer
                            model_used = ai_response.model_used
                            response_type = "solution_with_image"
                            next_action = ai_response.next_action
                            conversation_state = ai_response.conversation_state
                            model_info = ai_response.model_info
                        else:
                            print("⚡ 기본 Excel 작업: Gemini 2.5 Flash 사용")
                            answer = await self.generate_coding_response(enhanced_question, context, file_summary, answer_style)
                            model_used = "Gemini 2.5 Flash"
                            response_type = "solution_with_image"
                            next_action = "complete"
                            conversation_state = ConversationState.COMPLETED
                    elif self._is_complex_task(question):
                        # Complex task - use Gemini 2.5 Pro
                        print("🚀 복잡한 작업 감지: Gemini 2.5 Pro 사용")
                        print(f"🔍 질문 내용: {question}")
                        ai_response = await self._generate_solution_with_context(
                            question, question, context, file_summary
                        )
                        answer = ai_response.answer
                        model_used = ai_response.model_used
                        response_type = ai_response.response_type
                        next_action = ai_response.next_action
                        conversation_state = ai_response.conversation_state
                        model_info = ai_response.model_info
                    else:
                        # Basic task - use Gemini 2.5 Flash
                        print("⚡ 기본 작업 감지: Gemini 2.5 Flash 사용")
                        print(f"🔍 질문 내용: {question}")
                        answer = await self.generate_coding_response(question, context, file_summary, answer_style)
                        model_used = "Gemini 2.5 Flash"
                        response_type = "solution"
                        next_action = "complete"
                        conversation_state = ConversationState.COMPLETED
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create model info if not provided
            if 'model_info' not in locals():
                model_info = {
                    "model_name": model_used.lower().replace(" ", "_"),
                    "model_type": model_used,
                    "processing_time": processing_time,
                    "classification": "basic" if "Flash" in model_used else "complex"
                }
            
            return AIResponse(
                answer=answer,
                session_id="",
                model_used=model_used,
                processing_time=processing_time,
                response_type=response_type,
                next_action=next_action,
                conversation_state=conversation_state,
                model_info=model_info
            )
            
        except Exception as e:
            print(f"❌ process_chat_request 오류: {e}")
            raise AIServiceException(f"채팅 요청 처리 실패: {str(e)}")
    
    async def _process_standard_question(
        self, 
        question: str, 
        context: str, 
        file_summary: str,
        classification: QuestionClassification,
        image_data: Optional[bytes] = None,
        answer_style: Optional[str] = None
    ) -> str:
        """Process standard question without clarification needs"""
        # 이미지가 첨부된 경우 Flash 모델 우선 사용
        if image_data:
            print("🖼️ 이미지가 첨부된 질문: Flash 모델 우선 처리")
            try:
                # 이미지 분석 수행
                image_analysis = await self._analyze_image_with_gemini(image_data)
                
                # 이미지 분석 결과를 포함한 질문 처리
                enhanced_question = f"{question}\n\n[이미지 분석 결과]\n{image_analysis}"
                
                # Flash 모델로 처리 (이미지 분석에 최적화)
                if self.gemini_2_0_flash_model:
                    return await self._call_gemini_2_0_flash(enhanced_question, temperature=0.7)
                elif self.gemini_2_5_flash_model:
                    return await self._call_gemini_2_5_flash(enhanced_question, temperature=0.7)
                else:
                    # Flash 모델이 없으면 기존 로직 사용
                    print("⚠️ Flash 모델 없음: 기존 로직 사용")
            except Exception as e:
                print(f"❌ 이미지 처리 실패: {e}, 기존 로직으로 폴백")
        
        # If question is specific enough, generate solution directly
        if self._is_specific_enough(question):
            return await self._generate_solution_with_context(
                question,  # Use the question as the task
                question,  # Use the question as understanding
                context,
                file_summary
            )
        
        # Otherwise, use classification-based processing with user-level awareness
        if classification.classification == "beginner_help":
            print(f"🤖 분류: 초보자 도움 - {classification.recommended_model} 사용")
            return await self.generate_beginner_response(question, context, file_summary, answer_style)
        elif classification.classification == "coding":
            print(f"🔧 분류: 기본 수식/코딩 - {classification.recommended_model} 사용")
            return await self.generate_coding_response(question, context, file_summary, answer_style)
        elif classification.classification == "advanced_coding":
            print(f"🚀 분류: 고급/복잡한 작업 - {classification.recommended_model} 사용")
            return await self.generate_advanced_coding_response(question, context, file_summary, answer_style)
        elif classification.classification == "analysis":
            print(f"📊 분류: 데이터 분석 - {classification.recommended_model} 사용")
            return await self.generate_analysis_response(question, context, file_summary, answer_style)
        elif classification.classification == "planning":
            print(f"📋 분류: 계획 수립 - {classification.recommended_model} 사용")
            return await self.generate_planning_response(context, file_summary, answer_style)
        elif classification.classification == "simple":
            print(f"💡 분류: 기본 질의 - {classification.recommended_model} 사용")
            return await self.generate_simple_response(question, answer_style)
        elif classification.classification == "hybrid":
            print(f"🔄 분류: 하이브리드 처리 - {classification.recommended_model} 사용")
            return await self.generate_hybrid_response(question, context, file_summary, answer_style)
        elif classification.classification == "continuation":
            print(f"🔗 분류: 대화 연결 - {classification.recommended_model} 사용")
            return await self.generate_continuation_response(question, context, file_summary, answer_style)
        elif classification.classification == "debugging":
            print(f"�� 분류: 디버깅 - OpenAI 사용")
            return await self.generate_debugging_response(context, question, image_data)
        else:
            # Default to beginner help for unknown classifications
            print(f"❓ 분류: 알 수 없음 - 기본 모델 사용")
            return await self.generate_beginner_response(question, context, file_summary, answer_style)
    
    async def _generate_solution_with_context(
        self,
        original_question: str,
        understanding: str,
        context: str,
        file_summary: str
    ) -> AIResponse:
        """Generate solution based on gathered context and understanding"""
        start_time = time.time()
        
        try:
            # Use Gemini 2.5 Pro for complex solutions
            if self.gemini_pro_model:
                print("🚀 복잡한 솔루션 생성: Gemini 2.5 Pro 사용")
                
                # 파일 생성 요청인지 확인
                is_file_generation = self._is_file_generation_request(original_question)
                
                if is_file_generation:
                    prompt = f"""제공된 Excel 시트 데이터를 기반으로 실제 분석을 수행하고 파일을 생성해주세요.

**질문**: {original_question}
**시트 데이터**: {file_summary}

**⚠️ 매우 중요한 지침**:
1. **반드시 제공된 시트 데이터의 실제 내용만 사용하세요**
2. **가상의 이름이나 데이터를 절대 사용하지 마세요**
3. **원본 데이터의 정확한 값(학생 1, 학생 2 등)을 그대로 사용하세요**
4. **실제 데이터가 없는 경우 "데이터 없음"으로 표시하세요**

**출력 형식**:
🎯 **데이터 분석** (제공된 데이터 기반 분석)
🔧 **구체적 계산** (합계, 평균, 순위 등 실제 계산)
📋 **실행 단계** (Excel에서 직접 실행 가능한 단계)
💡 **결과 해석** (분석 결과의 의미)
📊 **시각화 제안** (차트/피벗테이블 생성 방법)

**파일 생성**:
- 분석이 완료되었으므로 다음 링크를 반드시 포함하세요:

[결과 파일 다운로드] analysis_result.xlsx

**주의**: 일반적인 설명이 아닌, 제공된 데이터에 직접 적용 가능한 구체적인 분석을 제공하세요.
"""
                else:
                    prompt = f"""제공된 Excel 시트 데이터를 기반으로 실제 분석을 수행해주세요.

**질문**: {original_question}
**시트 데이터**: {file_summary}

**⚠️ 매우 중요한 지침**:
1. **반드시 제공된 시트 데이터의 실제 내용만 사용하세요**
2. **가상의 이름이나 데이터를 절대 사용하지 마세요**
3. **원본 데이터의 정확한 값(학생 1, 학생 2 등)을 그대로 사용하세요**
4. **실제 데이터가 없는 경우 "데이터 없음"으로 표시하세요**

**출력 형식**:
🎯 **데이터 분석** (제공된 데이터 기반 분석)
🔧 **구체적 계산** (합계, 평균, 순위 등 실제 계산)
📋 **실행 단계** (Excel에서 직접 실행 가능한 단계)
💡 **결과 해석** (분석 결과의 의미)
📊 **시각화 제안** (차트/피벗테이블 생성 방법)

**주의**: 일반적인 설명이 아닌, 제공된 데이터에 직접 적용 가능한 구체적인 분석을 제공하세요.
"""
                
                try:
                    response = await self._call_gemini_pro(prompt, temperature=0.3)
                    print("✅ Gemini 2.5 Pro 솔루션 생성 성공")
                    processing_time = time.time() - start_time
                    return AIResponse(
                        answer=response,
                        session_id="",
                        model_used="Gemini 2.5 Pro",
                        processing_time=processing_time,
                        response_type="solution",
                        next_action="complete",
                        conversation_state=ConversationState.COMPLETED,
                        model_info={
                            "model_name": "gemini-2.5-pro",
                            "model_type": "Gemini 2.5 Pro (고급/복잡한 작업)",
                            "processing_time": processing_time,
                            "classification": "complex"
                        }
                    )
                except Exception as e:
                    print(f"❌ Gemini 2.5 Pro 솔루션 생성 실패: {e}")
                    
                    # 1차 폴백: Gemini 2.5 Flash 시도
                    try:
                        print("🔄 Gemini 2.5 Flash로 1차 폴백")
                        fallback_response = await self._call_gemini_2_5_flash(prompt, temperature=0.3)
                        processing_time = time.time() - start_time
                        return AIResponse(
                            answer=fallback_response,
                            session_id="",
                            model_used="Gemini 2.5 Flash",
                            processing_time=processing_time,
                            response_type="solution",
                            next_action="complete",
                            conversation_state=ConversationState.COMPLETED,
                            model_info={
                                "model_name": "gemini-2.5-flash",
                                "model_type": "Gemini 2.5 Flash (1차 폴백)",
                                "processing_time": processing_time,
                                "classification": "fallback"
                            }
                        )
                    except Exception as flash_error:
                        print(f"❌ Gemini 2.5 Flash 폴백 실패: {flash_error}")
                        
                        # 2차 폴백: OpenAI
                        try:
                            print("🔄 OpenAI로 2차 폴백")
                            fallback_response = await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.3)
                            processing_time = time.time() - start_time
                            return AIResponse(
                                answer=fallback_response,
                                session_id="",
                                model_used="OpenAI GPT-4o",
                                processing_time=processing_time,
                                response_type="solution",
                                next_action="complete",
                                conversation_state=ConversationState.COMPLETED,
                                model_info={
                                    "model_name": "gpt-4o-mini",
                                    "model_type": "OpenAI GPT-4o (2차 폴백)",
                                    "processing_time": processing_time,
                                    "classification": "fallback"
                                }
                            )
                        except Exception as openai_error:
                            print(f"❌ OpenAI 폴백도 실패: {openai_error}")
                            raise AIServiceException(f"모든 AI 모델 폴백 실패: {str(e)}")
            else:
                print("🚀 복잡한 솔루션 생성: OpenAI 사용 (Gemini Pro 없음)")
                prompt = f"""Excel 문제를 해결해주세요.

**질문**: {original_question}
**파일 정보**: {file_summary}

**출력 형식**:
🎯 **문제 분석** (문제점과 원인)
🔧 **해결 방법** (단계별 접근)
📋 **구체적 단계** (실행 가능한 단계)
💡 **추가 팁** (주의사항과 최적화)
📊 **결과 확인** (예상 결과)

[결과 파일 다운로드] analysis_result.xlsx"""
                response = await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.3)
                processing_time = time.time() - start_time
                return AIResponse(
                    answer=response,
                    session_id="",
                    model_used="OpenAI GPT-4o",
                    processing_time=processing_time,
                    response_type="solution",
                    next_action="complete",
                    conversation_state=ConversationState.COMPLETED,
                    model_info={
                        "model_name": "gpt-4o-mini",
                        "model_type": "OpenAI GPT-4o (보조/롤백)",
                        "processing_time": processing_time,
                        "classification": "fallback"
                    }
                )
                
        except Exception as e:
            print(f"❌ 솔루션 생성 중 예외 발생: {e}")
            raise AIServiceException(f"솔루션 생성 실패: {str(e)}")
    
    def _is_new_question(self, question: str, context: str) -> bool:
        """Check if the question is new or a continuation"""
        question_lower = question.lower()
        
        # Keywords that indicate a new question
        new_question_indicators = [
            "추가", "또", "그리고", "또한", "다음", "이번에는", "이제", "새로",
            "다른", "별도", "추가로", "부가로", "그 다음", "그리고 나서",
            "e열", "f열", "g열", "새 열", "다른 열", "다른 시트", "새 시트"
        ]
        
        # Check if question contains new question indicators
        has_new_indicators = any(indicator in question_lower for indicator in new_question_indicators)
        
        # Check if question mentions different columns/sheets than previous context
        context_lower = context.lower()
        has_different_targets = self._has_different_targets(question_lower, context_lower)
        
        # Check if question is about a different function/operation
        has_different_operation = self._has_different_operation(question_lower, context_lower)
        
        return has_new_indicators or has_different_targets or has_different_operation
    
    def _has_different_targets(self, question: str, context: str) -> bool:
        """Check if question targets different columns/sheets than context"""
        # Extract column/sheet references
        import re
        
        # Find column references (A열, B열, etc.)
        question_cols = re.findall(r'[a-z]열', question)
        context_cols = re.findall(r'[a-z]열', context)
        
        # If question mentions columns not in context, it's likely new
        if question_cols and context_cols:
            return not any(col in context_cols for col in question_cols)
        
        return False
    
    def _has_different_operation(self, question: str, context: str) -> bool:
        """Check if question is about a different operation than context"""
        # Different function keywords
        functions = {
            "vlookup": ["vlookup", "vlookup"],
            "xlookup": ["xlookup", "xlookup"],
            "if": ["if", "조건", "확인"],
            "isnumber": ["isnumber", "숫자인지", "숫자 확인"],
            "istext": ["istext", "문자인지", "문자 확인"],
            "sumif": ["sumif", "조건합계"],
            "countif": ["countif", "조건개수"]
        }
        
        # Find functions mentioned in question and context
        question_funcs = []
        context_funcs = []
        
        for func_name, keywords in functions.items():
            if any(keyword in question for keyword in keywords):
                question_funcs.append(func_name)
            if any(keyword in context for keyword in keywords):
                context_funcs.append(func_name)
        
        # If question mentions different functions than context, it's likely new
        if question_funcs and context_funcs:
            return not any(func in context_funcs for func in question_funcs)
        
        return False
    
    def _is_specific_task_request(self, question: str) -> bool:
        """Check if the question contains a specific task request"""
        question_lower = question.lower()
        
        # Check for specific function names
        function_keywords = [
            "vlookup", "xlookup", "hlookup", "index", "match", "sumif", "countif", 
            "averageif", "if", "and", "or", "concatenate", "left", "right", "mid",
            "len", "trim", "substitute", "replace", "find", "search", "date", "today",
            "now", "year", "month", "day", "weekday", "eomonth", "datedif",
            "isnumber", "istext", "isna", "isblank", "iserror", "숫자인지", "문자인지", "확인"
        ]
        
        # Check for specific operations
        operation_keywords = [
            "찾아서", "가져와", "연결", "합계", "평균", "개수", "정렬", "필터", 
            "중복 제거", "정리", "분석", "요약", "그래프", "차트", "매크로", "자동화",
            "조건부", "서식", "수식", "함수", "코드", "스크립트", "vba",
            "확인하고", "확인하고 싶어", "알고 싶어", "원해", "필요해"
        ]
        
        # Check for specific Excel terms
        excel_keywords = [
            "열", "행", "셀", "시트", "워크북", "범위", "피벗", "테이블", "데이터",
            "값", "참조", "링크", "복사", "붙여넣기", "삽입", "삭제", "이동"
        ]
        
        # Check for column references (A열, B열, etc.)
        import re
        column_pattern = r'[a-z]열'
        has_column_ref = bool(re.search(column_pattern, question_lower))
        
        # Check if question contains specific function or operation
        has_function = any(func in question_lower for func in function_keywords)
        has_operation = any(op in question_lower for op in operation_keywords)
        has_excel_term = any(term in question_lower for term in excel_keywords)
        
        # Consider it specific if it has:
        # 1. Function names, OR
        # 2. Column references with operations, OR
        # 3. Detailed operations with Excel terms
        return has_function or (has_column_ref and has_operation) or (has_operation and has_excel_term)
    
    def _is_vba_or_complex_request(self, question: str) -> bool:
        """Check if the question is about VBA or complex operations"""
        question_lower = question.lower()
        
        # VBA related keywords (complex programming)
        vba_keywords = [
            "vba", "매크로", "코드", "스크립트", "프로그램", "서브루틴", "함수",
            "for", "while", "if", "then", "else", "end if", "loop", "next", "dim", "set",
            "sub", "function", "call", "exit", "goto", "on error", "resume"
        ]
        
        # Complex operation keywords (advanced features)
        complex_keywords = [
            "통합", "합치기", "병합", "연결", "모든", "전체", "시트", "파일", "년도", "월별",
            "매출", "자료", "데이터", "관리", "정리", "분석", "요약", "집계", "통계",
            "복잡한", "고급", "고급 기능", "조합", "여러", "다중", "연쇄", "연결된",
            "조건부 서식", "데이터 유효성", "피벗 테이블", "차트", "그래프", "시각화",
            "데이터 모델", "관계", "외부 데이터", "쿼리", "sql", "데이터베이스",
            "워크시트 함수", "사용자 정의 함수", "udf", "add-in", "플러그인"
        ]
        
        # Check for VBA keywords
        has_vba_keywords = any(keyword in question_lower for keyword in vba_keywords)
        
        # Check for complex operation keywords
        has_complex_keywords = any(keyword in question_lower for keyword in complex_keywords)
        
        # Check for multiple operations or complex combinations
        operation_count = 0
        if "그리고" in question_lower or "또한" in question_lower or "추가로" in question_lower:
            operation_count += 1
        if "여러" in question_lower or "다중" in question_lower or "복합" in question_lower:
            operation_count += 1
        if "시트" in question_lower and ("여러" in question_lower or "모든" in question_lower):
            operation_count += 1
            
        # Consider it complex if it has VBA keywords, complex keywords, or multiple operations
        return has_vba_keywords or has_complex_keywords or operation_count >= 2
    
    def _is_specific_enough(self, question: str) -> bool:
        """Check if the question is specific enough to process directly"""
        question_lower = question.lower()
        
        # Check for file generation requests (should be processed directly)
        file_generation_keywords = [
            "파일생성", "파일 생성", "파일로", "파일 만들어", "파일 만들기",
            "엑셀파일", "엑셀 파일", "결과파일", "결과 파일", "다운로드", "저장",
            "보고서", "분석결과", "분석 결과", "통계", "차트", "그래프", "시각화",
            "피벗테이블", "피벗 테이블", "조건부서식", "조건부 서식", "데이터분석",
            "데이터 분석", "인사이트", "최적화", "품질진단", "품질 진단"
        ]
        
        # If it's a file generation request, consider it specific enough
        if any(keyword in question_lower for keyword in file_generation_keywords):
            return True
        
        # Check for specific functions, operations, or targets
        specific_indicators = [
            # Functions
            "vlookup", "xlookup", "hlookup", "index", "match", "sumif", "countif",
            "averageif", "if", "and", "or", "concatenate", "left", "right", "mid",
            "len", "trim", "substitute", "replace", "find", "search", "date", "today",
            "now", "year", "month", "day", "weekday", "eomonth", "datedif",
            "isnumber", "istext", "isna", "isblank", "iserror", "숫자인지", "문자인지", "확인",
            
            # Operations
            "찾아서", "가져와", "연결", "합계", "평균", "개수", "정렬", "필터",
            "중복 제거", "정리", "분석", "요약", "그래프", "차트", "매크로", "자동화",
            "조건부", "서식", "수식", "함수", "코드", "스크립트", "vba",
            "확인하고", "확인하고 싶어", "알고 싶어", "원해", "필요해",
            
            # Targets
            "a열", "b열", "c열", "d열", "e열", "f열", "g열", "h열", "i열", "j열",
            "1행", "2행", "3행", "4행", "5행", "시트", "파일", "데이터",
            
            # VBA and complex operations
            "vba", "매크로", "코드", "스크립트", "자동화", "프로그램", "함수", "서브루틴",
            "통합", "합치기", "병합", "연결", "모든", "전체", "년도", "월별",
            "매출", "자료", "관리", "정리", "분석", "요약", "집계", "통계",
            "1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월",
            "각 이름", "각 시트", "여러 시트", "여러 파일", "년도별", "월별"
        ]
        
        # Check if question contains specific indicators
        has_specific_indicators = any(indicator in question_lower for indicator in specific_indicators)
        
        # Check for column references (A열, B열, etc.)
        import re
        column_pattern = r'[a-z]열'
        has_column_ref = bool(re.search(column_pattern, question_lower))
        
        # Check for specific patterns
        has_specific_patterns = any([
            "시트에 저장" in question_lower,
            "파일로 관리" in question_lower,
            "한 시트에 통합" in question_lower,
            "모든 매출자료" in question_lower,
            "년도별로" in question_lower,
            "vba로" in question_lower,
            "매크로로" in question_lower
        ])
        
        return has_specific_indicators or has_column_ref or has_specific_patterns
    
    def _has_multiple_interpretations(self, question: str) -> bool:
        """Check if the question could have multiple interpretations"""
        question_lower = question.lower()
        
        # Ambiguous phrases that could mean different things
        ambiguous_phrases = [
            "정리해줘",  # 데이터 정리? 서식 정리? 
            "분석해줘",  # 어떤 분석?
            "요약해줘",  # 어떤 요약?
            "만들어줘",  # 무엇을 만들까?
            "해줘",      # 너무 일반적
            "도와줘"     # 너무 일반적
        ]
        
        # Check if question contains only ambiguous phrases without specific context
        has_ambiguous = any(phrase in question_lower for phrase in ambiguous_phrases)
        
        # If it has ambiguous phrases but no specific context, it's unclear
        if has_ambiguous and not self._is_specific_enough(question):
            return True
            
        return False
    
    def _get_task_examples(self, task_type: str) -> str:
        """Get examples for specific task type"""
        examples = {
            "수식/함수 만들기": """• VLOOKUP으로 다른 시트에서 데이터 가져오기
• SUMIF로 조건에 맞는 값 합계
• INDEX/MATCH로 유연한 데이터 검색
• IF 함수로 조건부 계산
• COUNTIF로 조건에 맞는 개수 세기""",
            
            "데이터 정리": """• 중복 데이터 제거
• 특정 열 기준으로 정렬
• 빈 셀 정리 및 채우기
• 데이터 형식 통일
• 불필요한 공백 제거""",
            
            "요약/분석": """• 피벗 테이블로 데이터 요약
• 매출/지출 통계 분석
• 월별/분기별 집계
• 평균, 최대, 최소값 계산
• 데이터 패턴 분석""",
            
            "시각화": """• 매출 추이 선그래프
• 카테고리별 막대그래프
• 비율 분석 원형차트
• 데이터 분포 히스토그램
• 상관관계 산점도""",
            
            "자동화": """• 반복 작업 VBA 매크로
• 자동 데이터 정리 스크립트
• 조건부 서식 자동 적용
• 이메일 자동 발송
• 파일 자동 저장 및 백업"""
        }
        return examples.get(task_type, "• 구체적인 작업을 말씀해 주세요")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive AI service status"""
        return {
            "openai_available": self.openai_client is not None,
            "gemini_pro_available": self.gemini_pro_model is not None,
            "gemini_2_5_flash_available": self.gemini_2_5_flash_model is not None,
            "gemini_2_0_flash_available": self.gemini_2_0_flash_model is not None,
            "models": {
                "openai": settings.OPENAI_MODEL,
                "gemini_pro": settings.GEMINI_PRO_MODEL,
                "gemini_2_5_flash": settings.GEMINI_2_5_FLASH_MODEL,
                "gemini_2_0_flash": settings.GEMINI_2_0_FLASH_MODEL
            },
            "capabilities": {
                "text_generation": True,
                "image_analysis": self.gemini_2_0_flash_model is not None,
                "fast_processing": self.gemini_2_0_flash_model is not None,
                "coding_excellence": self.gemini_pro_model is not None,
                "data_analysis": self.gemini_2_5_flash_model is not None,
                "planning": self.gemini_2_5_flash_model is not None,
                "hybrid_processing": self.openai_client is not None and self.gemini_pro_model is not None
            },
            "specialized_roles": {
                "beginner_help": "Gemini 2.0 Flash (초보자 친화적 설명)",
                "coding": "Gemini 2.5 Flash (기본 함수/수식)",
                "analysis": "Gemini 2.5 Flash (빠른 데이터 분석)",
                "planning": "Gemini 2.5 Flash (구조화된 계획 수립)",
                "simple": "Gemini 2.0 Flash (비용 효율적)",
                "complex": "Gemini 2.5 Pro (고급/복잡한 작업)",
                "image_analysis": "Gemini 2.0 Flash (멀티모달)",
                "auxiliary_support": "OpenAI (보조적 역할)"
            }
        }
    
    def _get_model_type(self, model_name: str) -> str:
        """Get human-readable model type for display"""
        if "gemini-2.5-pro" in model_name or "gemini_pro" in model_name:
            return "Gemini 2.5 Pro (고급/복잡한 작업)"
        elif "gemini-2.5-flash" in model_name or "gemini_2_5_flash" in model_name:
            return "Gemini 2.5 Flash (기본 수식/코딩)"
        elif "gemini-2.0-flash" in model_name or "gemini_2_0_flash" in model_name:
            return "Gemini 2.0 Flash (기초 질의/이미지)"
        elif "gpt-4o" in model_name or "openai" in model_name:
            return "OpenAI GPT-4o (보조/롤백)"
        elif "conversation" in model_name:
            return "대화 관리"
        else:
            return "기타 모델"
    
    def _is_basic_task(self, question: str) -> bool:
        """Check if the question is a basic task that can be handled by Flash models"""
        question_lower = question.lower()
        
        # Basic function keywords (simple, single functions)
        basic_function_keywords = [
            "vlookup", "hlookup", "sumif", "countif", "averageif", "if", "and", "or",
            "left", "right", "mid", "len", "trim", "concatenate", "substitute", "replace",
            "isnumber", "istext", "isna", "isblank", "iserror", "숫자인지", "문자인지",
            "sum", "average", "count", "max", "min", "round", "date", "today", "now"
        ]
        
        # Basic operation keywords (simple operations)
        basic_operation_keywords = [
            "찾아서", "가져와", "합계", "평균", "개수", "정렬", "필터", "중복 제거",
            "확인하고", "알고 싶어", "원해", "필요해", "만들어줘", "알려줘", "계산",
            "더하기", "빼기", "곱하기", "나누기", "반올림", "올림", "내림"
        ]
        
        # Simple macro keywords (basic automation)
        simple_macro_keywords = [
            "자동", "반복", "일괄", "복사", "붙여넣기", "서식 복사", "자동 채우기",
            "간단한", "기본", "단순", "자동화"
        ]
        
        # Complex keywords that require Pro model
        complex_keywords = [
            "vba", "매크로", "코드", "스크립트", "프로그램", "서브루틴", "함수",
            "통합", "합치기", "병합", "연결", "모든", "전체", "시트", "파일", "년도", "월별",
            "매출", "자료", "데이터", "관리", "정리", "분석", "요약", "집계", "통계",
            "복잡한", "고급", "고급 기능", "조합", "여러", "다중", "연쇄", "연결된",
            "조건부 서식", "데이터 유효성", "피벗 테이블", "차트", "그래프", "시각화",
            "for", "while", "loop", "next", "dim", "set", "then", "else", "end if"
        ]
        
        # Check for complex keywords first
        has_complex_keywords = any(keyword in question_lower for keyword in complex_keywords)
        if has_complex_keywords:
            return False
        
        # Check for basic functions or operations
        has_basic_function = any(func in question_lower for func in basic_function_keywords)
        has_basic_operation = any(op in question_lower for op in basic_operation_keywords)
        has_simple_macro = any(macro in question_lower for macro in simple_macro_keywords)
        
        # Check for column references (A열, B열, etc.)
        import re
        column_pattern = r'[a-z]열'
        has_column_ref = bool(re.search(column_pattern, question_lower))
        
        # Consider it basic if it has:
        # 1. Basic function names, OR
        # 2. Basic operations with column references, OR
        # 3. Simple operations without complex keywords, OR
        # 4. Simple macro requests
        return (has_basic_function or 
                (has_column_ref and has_basic_operation) or 
                has_basic_operation or 
                has_simple_macro)
    
    def _is_specific_task_request(self, question: str) -> bool:
        """Check if the question contains a specific task request"""
        question_lower = question.lower()
        
        # Check for specific function names
        function_keywords = [
            "vlookup", "xlookup", "hlookup", "index", "match", "sumif", "countif", 
            "averageif", "if", "and", "or", "concatenate", "left", "right", "mid",
            "len", "trim", "substitute", "replace", "find", "search", "date", "today",
            "now", "year", "month", "day", "weekday", "eomonth", "datedif",
            "isnumber", "istext", "isna", "isblank", "iserror", "숫자인지", "문자인지", "확인"
        ]
        
        # Check for specific operations
        operation_keywords = [
            "찾아서", "가져와", "연결", "합계", "평균", "개수", "정렬", "필터", 
            "중복 제거", "정리", "분석", "요약", "그래프", "차트", "매크로", "자동화",
            "조건부", "서식", "수식", "함수", "코드", "스크립트", "vba",
            "확인하고", "확인하고 싶어", "알고 싶어", "원해", "필요해"
        ]
        
        # Check for specific Excel terms
        excel_keywords = [
            "열", "행", "셀", "시트", "워크북", "범위", "피벗", "테이블", "데이터",
            "값", "참조", "링크", "복사", "붙여넣기", "삽입", "삭제", "이동"
        ]
        
        # Check for column references (A열, B열, etc.)
        import re
        column_pattern = r'[a-z]열'
        has_column_ref = bool(re.search(column_pattern, question_lower))
        
        # Check if question contains specific function or operation
        has_function = any(func in question_lower for func in function_keywords)
        has_operation = any(op in question_lower for op in operation_keywords)
        has_excel_term = any(term in question_lower for term in excel_keywords)
        
        # Consider it specific if it has:
        # 1. Function names, OR
        # 2. Column references with operations, OR
        # 3. Detailed operations with Excel terms
        return has_function or (has_column_ref and has_operation) or (has_operation and has_excel_term)
    
    def _is_file_generation_request(self, question: str) -> bool:
        """Check if the question is a file generation request - 매우 엄격한 기준"""
        question_lower = question.lower()
        
        # 매우 명시적인 파일 생성 요청 키워드만 감지
        explicit_file_generation_keywords = [
            "파일로 만들어줘", "파일 만들어줘", "파일로 만들어달라", "파일로 만들어달라고",
            "파일로 만들어달라고요", "파일로 만들어달라구요", "파일로 만들어달라구",
            "파일생성해줘", "파일 생성해줘", "파일생성해달라", "파일 생성해달라",
            "다운로드해줘", "저장해줘", "파일로 저장해줘", "파일로 다운로드해줘",
            "엑셀파일로 만들어줘", "엑셀 파일로 만들어줘", "결과파일로 만들어줘", "결과 파일로 만들어줘"
        ]
        
        # 매우 명시적인 파일 생성 요청만 감지 (정확히 일치하는 경우만)
        for keyword in explicit_file_generation_keywords:
            if keyword in question_lower:
                print(f"✅ 파일 생성 요청 감지: '{keyword}' 키워드 발견")
                return True
        
        # 인코딩 문제로 깨진 "파일생성" 감지
        if "íŒŒì" in question or "ìƒ" in question or "ì„±" in question:
            print("✅ 파일 생성 요청 감지: 인코딩 문제로 깨진 키워드 발견")
            return True
            
        print(f"❌ 파일 생성 요청 아님: '{question}'")
        return False
    
    def _is_complex_task(self, question: str) -> bool:
        """Check if the question is a complex task requiring Gemini 2.5 Pro"""
        question_lower = question.lower()
        
        # Complex keywords that require Pro model
        complex_keywords = [
            "vba", "매크로", "코드", "스크립트", "프로그램", "서브루틴", "함수",
            "통합", "합치기", "병합", "연결", "모든", "전체", "시트", "년도", "월별",
            "복잡한", "고급", "고급 기능", "조합", "여러", "다중", "연쇄", "연결된",
            "조건부 서식", "데이터 유효성", "피벗 테이블", "차트", "그래프", "시각화",
            "데이터 모델", "관계", "외부 데이터", "쿼리", "sql", "데이터베이스",
            "for", "while", "loop", "next", "dim", "set", "then", "else", "end if",
            # 고급 Excel 기능 키워드 추가
            "통계분석", "통계 분석", "데이터분석", "데이터 분석", "인사이트", "최적화",
            "품질진단", "품질 진단", "이상치", "이상 치", "결측치", "결측 치",
            "상관관계", "상관 관계", "분포", "왜도", "첨도", "기술통계", "기술 통계",
            "데이터시각화", "데이터 시각화", "대시보드", "리포트", "보고서"
        ]
        
        # Check for complex keywords
        has_complex_keywords = any(keyword in question_lower for keyword in complex_keywords)
        
        # Check for multiple operations
        operation_count = 0
        if "그리고" in question_lower or "또한" in question_lower or "추가로" in question_lower:
            operation_count += 1
        if "여러" in question_lower or "다중" in question_lower or "복합" in question_lower:
            operation_count += 1
        if "시트" in question_lower and ("여러" in question_lower or "모든" in question_lower):
            operation_count += 1
            
        return has_complex_keywords or operation_count >= 2

# Global AI service instance
ai_service = AIService()
