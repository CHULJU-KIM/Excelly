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
from prompts import PLANNING_PERSONA_PROMPT, CODING_PERSONA_PROMPT, DEBUGGING_PERSONA_PROMPT

class AIService:
    """Service for managing AI model interactions with intelligent routing"""
    
    def __init__(self):
        self.openai_client = None
        self.gemini_model = None
        self.gemini_flash_model = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AI clients with optimized model selection"""
        try:
            # Initialize OpenAI client
            if settings.OPENAI_API_KEY:
                self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                print(f"✅ OpenAI 클라이언트 초기화 성공: {settings.OPENAI_MODEL}")
            
            # Initialize Gemini client
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                # Initialize Gemini Pro model (for creative and analytical tasks)
                try:
                    self.gemini_model = genai.GenerativeModel(settings.GEMINI_PRO_MODEL)
                    print(f"✅ Gemini Pro 모델 초기화 성공: {settings.GEMINI_PRO_MODEL}")
                except Exception as e:
                    print(f"⚠️ Gemini Pro 모델 초기화 실패: {e}")
                    # Fallback to 2.0 Pro, then 1.5 Pro
                    try:
                        self.gemini_model = genai.GenerativeModel(settings.GEMINI_2_0_PRO_FALLBACK)
                        print(f"✅ Gemini 2.0 Pro 모델로 대체: {settings.GEMINI_2_0_PRO_FALLBACK}")
                    except Exception as e2:
                        print(f"⚠️ Gemini 2.0 Pro 모델 초기화 실패: {e2}")
                        try:
                            self.gemini_model = genai.GenerativeModel(settings.GEMINI_1_5_PRO_FALLBACK)
                            print(f"✅ Gemini 1.5 Pro 모델로 대체: {settings.GEMINI_1_5_PRO_FALLBACK}")
                        except Exception as e3:
                            print(f"❌ Gemini Pro 계열 모델 초기화 실패: {e3}")
                            self.gemini_model = None
                
                # Initialize Gemini Flash model (for fast processing and classification)
                try:
                    self.gemini_flash_model = genai.GenerativeModel(settings.GEMINI_FLASH_MODEL)
                    print(f"✅ Gemini Flash 모델 초기화 성공: {settings.GEMINI_FLASH_MODEL}")
                except Exception as e:
                    print(f"⚠️ Gemini Flash 모델 초기화 실패: {e}")
                    # Fallback to 2.0 Flash, then 1.5 Flash
                    try:
                        self.gemini_flash_model = genai.GenerativeModel(settings.GEMINI_2_0_FLASH_FALLBACK)
                        print(f"✅ Gemini 2.0 Flash 모델로 대체: {settings.GEMINI_2_0_FLASH_FALLBACK}")
                    except Exception as e2:
                        print(f"⚠️ Gemini 2.0 Flash 모델 초기화 실패: {e2}")
                        try:
                            self.gemini_flash_model = genai.GenerativeModel(settings.GEMINI_1_5_FLASH_FALLBACK)
                            print(f"✅ Gemini 1.5 Flash 모델로 대체: {settings.GEMINI_1_5_FLASH_FALLBACK}")
                        except Exception as e3:
                            print(f"❌ Gemini Flash 계열 모델 초기화 실패: {e3}")
                            self.gemini_flash_model = None
                
        except Exception as e:
            print(f"⚠️ AI 클라이언트 초기화 중 오류: {str(e)}")
            # Don't raise exception, continue with available models
    
    async def classify_question(self, question: str) -> QuestionClassification:
        """Enhanced question classification with optimized model selection"""
        try:
            prompt = f"""다음 사용자 질문을 분석하여 적절한 AI 모델과 처리 방식을 결정하세요.

질문: "{question}"

다음 기준으로 분류하세요:
1. **simple**: 간단한 사실 질문, 함수 사용법, 기본 문법
2. **complex**: 복잡한 로직, 여러 단계 작업, 파일 분석
3. **creative**: 창의적 아이디어, 새로운 접근법, 최적화 제안
4. **analytical**: 데이터 분석, 패턴 찾기, 통계적 분석
5. **debugging**: 오류 해결, 문제 진단, 코드 수정

다음 JSON 형식으로 답하세요:
{{
    "classification": "simple|complex|creative|analytical|debugging",
    "confidence": 0.0-1.0,
    "reasoning": "분류 이유",
    "recommended_model": "openai|gemini_pro|gemini_flash",
    "estimated_tokens": 100-4000
}}"""
            
            # Use Gemini 2.0 Flash for classification (fastest and most cost-effective)
            if self.gemini_flash_model:
                response = await self._call_gemini_flash(prompt, temperature=0.0)
            else:
                response = await self._call_openai(prompt, model="gpt-4o-mini", temperature=0.0)
            
            try:
                result = json.loads(response)
                return QuestionClassification(
                    classification=result.get("classification", "complex"),
                    confidence=result.get("confidence", 0.5),
                    reasoning=result.get("reasoning", ""),
                    recommended_model=result.get("recommended_model", "openai"),
                    estimated_tokens=result.get("estimated_tokens", 1000)
                )
            except json.JSONDecodeError:
                # Fallback parsing
                classification = self._fallback_classification(response)
                return QuestionClassification(
                    classification=classification,
                    confidence=0.7,
                    reasoning="JSON 파싱 실패로 기본 분류 사용",
                    recommended_model="openai",
                    estimated_tokens=1000
                )
                
        except Exception as e:
            return QuestionClassification(
                classification="complex",
                confidence=0.5,
                reasoning=f"분류 실패: {str(e)}",
                recommended_model="openai",
                estimated_tokens=1000
            )
    
    def _fallback_classification(self, response: str) -> str:
        """Fallback classification when JSON parsing fails"""
        response_lower = response.lower()
        if any(word in response_lower for word in ["simple", "간단", "기본"]):
            return "simple"
        elif any(word in response_lower for word in ["creative", "창의", "새로운"]):
            return "creative"
        elif any(word in response_lower for word in ["analytical", "분석", "통계"]):
            return "analytical"
        elif any(word in response_lower for word in ["debugging", "오류", "문제"]):
            return "debugging"
        else:
            return "complex"
    
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
            if self.gemini_flash_model:
                response = await self._call_gemini_flash(prompt, temperature=0.0)
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
    
    async def generate_planning_response(self, context: str, file_summary: str = "", answer_style: Optional[str] = None) -> str:
        """Generate planning response using Gemini 2.0 Pro (optimized for structured thinking)"""
        try:
            style_guard = "\n\n[응답 스타일] 핵심만 간결히 5줄 이내로 요약" if (answer_style=="concise") else ""
            prompt = f"{PLANNING_PERSONA_PROMPT}{style_guard}\n\n--- Conversation History ---\n{context}\n\n{file_summary}"
            
            # Use Gemini 2.0 Pro for planning (best at structured thinking and planning)
            if self.gemini_model:
                return await self._call_gemini(prompt, temperature=0.7)
            else:
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.7)
            
        except Exception as e:
            raise AIServiceException(f"계획 생성 실패: {str(e)}")
    
    async def generate_coding_response(self, context: str, task: str) -> str:
        """Generate coding response using OpenAI (optimized for code generation)"""
        try:
            prompt = f"{CODING_PERSONA_PROMPT}\n\n--- Previous Conversation ---\n{context}\n\n--- Final Task ---\n{task}"
            
            # Use OpenAI for coding (best at code generation and VBA)
            return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.3)
            
        except Exception as e:
            raise AIServiceException(f"코드 생성 실패: {str(e)}")
    
    async def generate_simple_response(self, question: str, answer_style: Optional[str] = None) -> str:
        """Generate simple response using Gemini 2.0 Flash (optimized for speed and cost)"""
        try:
            prompt = f"""Excel과 관련된 간단한 질문에 대해 명확하고 간결하게 답변해주세요.

질문: {question}

다음 형식으로 답변하세요:
1. 간단한 설명
2. 구체적인 예시 (필요시)
3. 추가 팁 (필요시)"""
            if answer_style == "concise":
                prompt += "\n\n[응답 스타일] 핵심만 간결히, 5줄 이내"
            
            # Use Gemini 2.0 Flash for simple responses (fastest and most cost-effective)
            if self.gemini_flash_model:
                return await self._call_gemini_flash(prompt, temperature=0.3)
            else:
                return await self._call_openai(prompt, model="gpt-4o-mini", temperature=0.3)
            
        except Exception as e:
            raise AIServiceException(f"간단한 답변 생성 실패: {str(e)}")
    
    async def generate_creative_response(self, question: str, context: str, answer_style: Optional[str] = None) -> str:
        """Generate creative response using Gemini 2.0 Pro (optimized for innovative thinking)"""
        try:
            prompt = f"""창의적이고 혁신적인 Excel 솔루션을 제안해주세요.

사용자 질문: {question}
이전 대화: {context}

다음 관점에서 접근해주세요:
1. 새로운 Excel 기능 활용
2. 자동화 가능성
3. 효율성 개선 방안
4. 사용자 경험 향상"""
            if answer_style == "concise":
                prompt += "\n\n[응답 스타일] 핵심만 간결히, 5줄 이내"
            # Use Gemini 2.0 Pro for creative responses (best at innovative thinking)
            if self.gemini_model:
                return await self._call_gemini(prompt, temperature=0.8)
            else:
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.8)
            
        except Exception as e:
            raise AIServiceException(f"창의적 답변 생성 실패: {str(e)}")
    
    async def generate_analytical_response(self, question: str, data_context: str, answer_style: Optional[str] = None) -> str:
        """Generate analytical response using Gemini 2.0 Pro (optimized for data analysis)"""
        try:
            prompt = f"""데이터 분석 관점에서 Excel 작업을 도와주세요.

분석 요청: {question}
데이터 컨텍스트: {data_context}

다음 분석을 제공해주세요:
1. 데이터 패턴 분석
2. 통계적 인사이트
3. 시각화 제안
4. 추가 분석 방향"""
            if answer_style == "concise":
                prompt += "\n\n[응답 스타일] 핵심만 간결히, 5줄 이내"
            # Use Gemini 2.0 Pro for analytical responses (best at pattern recognition)
            if self.gemini_model:
                return await self._call_gemini(prompt, temperature=0.5)
            else:
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.5)
            
        except Exception as e:
            raise AIServiceException(f"분석 답변 생성 실패: {str(e)}")
    
    async def generate_debugging_response(self, context: str, feedback: str, image_data: Optional[bytes] = None) -> str:
        """Generate debugging response using OpenAI (optimized for problem-solving)"""
        try:
            # If image is provided, use Gemini 2.0 Flash for image analysis
            image_analysis = ""
            if image_data:
                if self.gemini_flash_model:
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
    
    async def _call_gemini(self, prompt: str, temperature: float = 0.7) -> str:
        """Make Gemini API call"""
        if not self.gemini_model:
            raise AIServiceException("Gemini 모델이 초기화되지 않았습니다.")
        
        try:
            response = await asyncio.wait_for(
                self.gemini_model.generate_content_async(prompt),
                timeout=settings.AI_REQUEST_TIMEOUT
            )
            
            return response.text.strip()
            
        except asyncio.TimeoutError:
            raise AIServiceException("Gemini 응답 시간 초과")
        except Exception as e:
            raise AIServiceException(f"Gemini API 호출 실패: {str(e)}")
    
    async def _call_gemini_flash(self, prompt: str, temperature: float = 0.7) -> str:
        """Make Gemini Flash API call (faster model)"""
        if not self.gemini_flash_model:
            raise AIServiceException("Gemini Flash 모델이 초기화되지 않았습니다.")
        
        try:
            response = await asyncio.wait_for(
                self.gemini_flash_model.generate_content_async(prompt),
                timeout=30  # Shorter timeout for flash model
            )
            
            return response.text.strip()
            
        except asyncio.TimeoutError:
            # Fallback to OpenAI on timeout
            try:
                return await self._call_openai(prompt, model="gpt-4o-mini", temperature=temperature)
            except Exception as e2:
                raise AIServiceException(f"Gemini Flash 응답 시간 초과 및 OpenAI 폴백 실패: {str(e2)}")
        except Exception as e:
            # Fallback to OpenAI on general error
            try:
                return await self._call_openai(prompt, model="gpt-4o-mini", temperature=temperature)
            except Exception as e2:
                raise AIServiceException(f"Gemini Flash API 실패 및 OpenAI 폴백 실패: {str(e2)}")
    
    async def _analyze_image_with_gemini(self, image_data: bytes) -> str:
        """Analyze image using Gemini 2.0 Flash (optimized for image analysis)"""
        # Use Gemini 2.0 Flash for image analysis (fastest and most cost-effective)
        model_to_use = self.gemini_flash_model or self.gemini_model
        
        if not model_to_use:
            return "[이미지 분석 기능을 사용할 수 없습니다. Gemini API 키가 필요합니다.]"
        
        try:
            image = Image.open(io.BytesIO(image_data))
            
            prompt = """이 이미지를 Excel 관련 관점에서 분석해주세요:

1. **화면 구성**: 어떤 Excel 화면인지 (워크시트, 차트, 피벗 테이블 등)
2. **데이터 구조**: 표시된 데이터의 구조와 특징
3. **문제점**: 오류 메시지, 잘못된 수식, 데이터 불일치 등
4. **개선 방안**: 발견된 문제에 대한 해결책 제안

특히 오류가 발생한 부분이나 문제가 되는 부분을 강조해서 알려주세요."""
            
            response = await asyncio.wait_for(
                model_to_use.generate_content_async([prompt, image]),
                timeout=30
            )
            
            return response.text
            
        except Exception as e:
            return f"[이미지 분석 실패: {str(e)}]"
    
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
        """Process complete chat request with intelligent model routing and conversation management"""
        start_time = time.time()
        
        try:
            if is_feedback:
                # Handle feedback with debugging persona
                answer = await self.generate_debugging_response(context, question, image_data)
                model_used = settings.OPENAI_MODEL
                response_type = "normal"
                next_action = None
                conversation_state = None
            else:
                # Special flow: if a sheet was selected and we have file summary, provide detailed analysis
                # ONLY if question is empty, starts with [시트선택], or is very short (like "1", "2", etc.)
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
                    # Return immediately to avoid being overwritten by later branches
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
                # Check if user provided a specific task request (contains function names, specific operations)
                elif file_summary and file_summary.strip() and self._is_specific_task_request(question):
                    # User provided a specific task - process directly
                    answer = await self._generate_solution_with_context(
                        question,  # Use the question as the task
                        question,  # Use the question as understanding
                        context,
                        file_summary
                    )
                    model_used = settings.OPENAI_MODEL
                    response_type = "solution"
                    next_action = "complete"
                    conversation_state = ConversationState.COMPLETED
                # Check if user mentioned VBA or specific complex operations
                elif file_summary and file_summary.strip() and self._is_vba_or_complex_request(question):
                    # User requested VBA or complex operations - process directly
                    answer = await self._generate_solution_with_context(
                        question,  # Use the question as the task
                        question,  # Use the question as understanding
                        context,
                        file_summary
                    )
                    model_used = settings.OPENAI_MODEL
                    response_type = "solution"
                    next_action = "complete"
                    conversation_state = ConversationState.COMPLETED
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
                    selected_task = task_map.get(question.strip(), "일반 작업")
                    
                    answer = f"""✅ **{selected_task}를 선택하셨습니다!**

현재 파일 정보:
{file_summary}

구체적으로 어떤 작업을 원하시나요?

**{selected_task} 예시:**
{self._get_task_examples(selected_task)}

원하시는 작업을 구체적으로 말씀해 주세요!
예: "VLOOKUP으로 다른 시트와 연결해줘" 또는 "A열 중복 제거해줘"
"""
                    model_used = "conversation"
                    response_type = "task_selection"
                    next_action = "wait_for_task_details"
                    conversation_state = ConversationState.CLARIFYING
                # Standard question processing - check if this is a clarification response
                elif conversation_context and conversation_context.state.value == "clarifying":
                    # Process clarification response
                    from app.services.conversation_service import conversation_service
                    updated_context = await conversation_service.process_clarification_response(
                        conversation_context, question
                    )
                    
                    if updated_context.state.value == "clarifying":
                        # Still need more clarifications
                        next_question = updated_context.pending_clarifications[0]
                        answer = f"감사합니다! 다음 질문입니다:\n\n**{next_question.question}**\n\n{next_question.context}"
                        model_used = "conversation"
                        response_type = "clarification"
                        next_action = "wait_for_clarification"
                        conversation_state = updated_context.state
                    else:
                        # Ready to generate solution
                        answer = await self._generate_solution_with_context(
                            updated_context.original_question,
                            updated_context.current_understanding,
                            context,
                            file_summary
                        )
                        model_used = settings.OPENAI_MODEL
                        response_type = "solution"
                        next_action = "complete"
                        conversation_state = updated_context.state
                else:
                    # New question - analyze for clarification needs
                    from app.services.conversation_service import conversation_service
                    
                    # STRICT clarification logic - only clarify when absolutely necessary
                    needs_clarification = False
                    clarification_reasons = []
                    
                    # Case 1: Empty or very short question with file
                    if (file_summary and file_summary.strip()) and (not question or len(question.strip()) < 2):
                        needs_clarification = True
                        clarification_reasons = ["goal"]
                    # Case 2: Question is too vague (no specific function, operation, or target mentioned)
                    elif not self._is_specific_enough(question):
                        needs_clarification = True
                        clarification_reasons = ["goal"]
                    # Case 3: Question mentions multiple possible interpretations
                    elif self._has_multiple_interpretations(question):
                        needs_clarification = True
                        clarification_reasons = ["goal"]
                    
                    # Create classification based on strict rules
                    if needs_clarification:
                        classification = QuestionClassification(
                            classification="complex",
                            confidence=0.9,
                            reasoning="구체적인 요청이 부족하여 명확화 필요",
                            recommended_model="openai",
                            estimated_tokens=300,
                            needs_clarification=True,
                            clarification_reasons=clarification_reasons
                        )
                    else:
                        classification = QuestionClassification(
                            classification="complex",
                            confidence=0.8,
                            reasoning="구체적인 요청으로 바로 처리 가능",
                            recommended_model="openai",
                            estimated_tokens=300,
                            needs_clarification=False,
                            clarification_reasons=[]
                        )
                    
                    # Only clarify if absolutely necessary
                    if classification.needs_clarification and not conversation_context:
                        # Start clarification process
                        clarification_type = classification.clarification_reasons[0] if classification.clarification_reasons else "goal"
                        clarification_questions = await conversation_service.generate_clarification_questions(
                            question, clarification_type, context
                        )
                        
                        # Create conversation context
                        conversation_context = conversation_service.create_conversation_context(question)
                        conversation_context.pending_clarifications = clarification_questions
                        conversation_context.state = ConversationState.CLARIFYING
                        
                        # Ask first clarification question (very short & user-friendly)
                        first_question = clarification_questions[0]
                        answer = f"좋아요! 정확히 도와드리려면 한 가지만 알려주세요.\n\n**{first_question.question}**\n\n{first_question.context}"
                        model_used = "conversation"
                        response_type = "clarification"
                        next_action = "wait_for_clarification"
                        conversation_state = conversation_context.state
                    else:
                        # Direct answer or continue with existing context
                        if conversation_context and conversation_context.state.value == "planning":
                            # Generate solution with existing context
                            answer = await self._generate_solution_with_context(
                                conversation_context.original_question,
                                conversation_context.current_understanding,
                                context,
                                file_summary
                            )
                            model_used = settings.OPENAI_MODEL
                            response_type = "solution"
                            next_action = "complete"
                            conversation_state = ConversationState.COMPLETED
                        else:
                            # Standard processing with context awareness
                            if conversation_context and conversation_context.state.value in ["planning", "executing"]:
                                # Continue with existing conversation context
                                answer = await self._generate_solution_with_context(
                                    conversation_context.original_question,
                                    conversation_context.current_understanding or question,
                                    context,
                                    file_summary
                                )
                                model_used = settings.OPENAI_MODEL
                                response_type = "solution"
                                next_action = "complete"
                                conversation_state = ConversationState.COMPLETED
                            else:
                                # Standard processing for new questions
                                answer = await self._process_standard_question(question, context, file_summary, classification, image_data, answer_style)
                                model_used = classification.recommended_model or settings.OPENAI_MODEL
                                response_type = "normal"
                                next_action = None
                                conversation_state = None
            
            processing_time = time.time() - start_time
            
            return AIResponse(
                answer=answer,
                session_id="",  # Will be set by caller
                model_used=model_used,
                processing_time=processing_time,
                response_type=response_type,
                next_action=next_action,
                conversation_state=conversation_state
            )
            
        except Exception as e:
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
        # If question is specific enough, generate solution directly
        if self._is_specific_enough(question):
            return await self._generate_solution_with_context(
                question,  # Use the question as the task
                question,  # Use the question as understanding
                context,
                file_summary
            )
        
        # Otherwise, use classification-based processing
        if classification.classification == "simple":
            return await self.generate_simple_response(question, answer_style)
        elif classification.classification == "creative":
            return await self.generate_creative_response(question, context, answer_style)
        elif classification.classification == "analytical":
            return await self.generate_analytical_response(question, file_summary, answer_style)
        elif classification.classification == "debugging":
            return await self.generate_debugging_response(context, question, image_data)
        else:
            # Complex question - generate planning response
            return await self.generate_planning_response(context, file_summary, answer_style)
    
    async def _generate_solution_with_context(
        self,
        original_question: str,
        understanding: str,
        context: str,
        file_summary: str
    ) -> str:
        """Generate solution based on gathered context and understanding"""
        try:
            # Check if this is a new question or continuation
            is_new_question = self._is_new_question(original_question, context)
            
            if is_new_question:
                # This is a new question - treat it as a fresh request
                prompt = f"""사용자의 새로운 질문: "{original_question}"

이전 대화 맥락:
{context}

파일 정보: {file_summary}

이것은 이전 질문과 다른 새로운 요청입니다. 이전 답변을 반복하지 말고, 새로운 질문에 대한 해결책을 제공해주세요.

## 🎯 새로운 해결책

[새로운 문제 요약]
- 사용자가 새로 요청한 문제

[해결 방법]
- 구체적인 해결 방법 (함수, 수식, 코드 등)

[사용 방법]
- 단계별 사용 방법

[주의사항]
- 주의해야 할 점들

[추가 팁]
- 더 나은 방법이나 개선 방안"""
            else:
                # This is a continuation or clarification
                prompt = f"""이전 대화를 이어서 진행하겠습니다.

원래 질문: "{original_question}"
현재 상황: {understanding}

이전 대화 내용:
{context}

파일 정보: {file_summary}

이전 대화를 고려하여 다음 중 하나로 응답해주세요:

1. **이전 답변에 대한 추가 설명이나 보완**이 필요한 경우
2. **새로운 질문이나 요청**이 있는 경우
3. **이전 해결책의 실행 결과**에 대한 피드백이 있는 경우

자연스럽게 대화를 이어가며 사용자의 요구에 맞는 답변을 제공해주세요."""

            # Use Gemini 2.5 Pro for VBA and complex code generation
            return await self._call_gemini(prompt, temperature=0.3)
            
        except Exception as e:
            raise AIServiceException(f"해결책 생성 실패: {str(e)}")
    
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
        
        # VBA related keywords
        vba_keywords = [
            "vba", "매크로", "코드", "스크립트", "자동화", "프로그램", "함수", "서브루틴",
            "for", "while", "if", "then", "else", "end if", "loop", "next", "dim", "set"
        ]
        
        # Complex operation keywords
        complex_keywords = [
            "통합", "합치기", "병합", "연결", "모든", "전체", "시트", "파일", "년도", "월별",
            "매출", "자료", "데이터", "관리", "정리", "분석", "요약", "집계", "통계",
            "1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월",
            "각 이름", "각 시트", "여러 시트", "여러 파일", "년도별", "월별"
        ]
        
        # Check for VBA keywords
        has_vba = any(keyword in question_lower for keyword in vba_keywords)
        
        # Check for complex operation keywords (need multiple matches for complex operations)
        complex_matches = sum(1 for keyword in complex_keywords if keyword in question_lower)
        has_complex_operation = complex_matches >= 3  # At least 3 complex keywords
        
        # Check for specific patterns that indicate complex operations
        has_specific_patterns = any([
            "시트에 저장" in question_lower,
            "파일로 관리" in question_lower,
            "한 시트에 통합" in question_lower,
            "모든 매출자료" in question_lower,
            "년도별로" in question_lower
        ])
        
        return has_vba or has_complex_operation or has_specific_patterns
    
    def _is_specific_enough(self, question: str) -> bool:
        """Check if the question is specific enough to process directly"""
        question_lower = question.lower()
        
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
        """Get comprehensive AI service status with optimized model information"""
        return {
            "openai_available": self.openai_client is not None,
            "gemini_available": self.gemini_model is not None,
            "gemini_flash_available": self.gemini_flash_model is not None,
            "models": {
                "openai": settings.OPENAI_MODEL,
                "gemini": settings.GEMINI_PRO_MODEL,
                "gemini_flash": settings.GEMINI_FLASH_MODEL
            },
            "capabilities": {
                "text_generation": True,
                "image_analysis": self.gemini_flash_model is not None,
                "fast_processing": self.gemini_flash_model is not None,
                "creative_thinking": self.gemini_model is not None,
                "code_generation": self.openai_client is not None,
                "data_analysis": self.gemini_model is not None,
                "planning": self.gemini_model is not None
            },
            "optimization": {
                "classification": "Gemini 2.0 Flash (fastest)",
                "simple_questions": "Gemini 2.0 Flash (cost-effective)",
                "creative_tasks": "Gemini 2.0 Pro (innovative)",
                "analytical_tasks": "Gemini 2.0 Pro (pattern recognition)",
                "coding_tasks": "OpenAI GPT-4o-mini (best code generation)",
                "debugging": "OpenAI GPT-4o-mini (problem-solving)",
                "image_analysis": "Gemini 2.0 Flash (multimodal)",
                "planning": "Gemini 2.0 Pro (structured thinking)"
            }
        }

# Global AI service instance
ai_service = AIService()
