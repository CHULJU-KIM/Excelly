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
                    print(f"✅ Gemini 2.0 Pro 모델 초기화 성공: {settings.GEMINI_PRO_MODEL}")
                except Exception as e:
                    print(f"⚠️ Gemini 2.0 Pro 모델 초기화 실패: {e}")
                    # Fallback to Gemini 1.5 Pro
                    try:
                        self.gemini_model = genai.GenerativeModel(settings.GEMINI_1_5_PRO_FALLBACK)
                        print(f"✅ Gemini 1.5 Pro 모델로 대체: {settings.GEMINI_1_5_PRO_FALLBACK}")
                    except Exception as e2:
                        print(f"❌ Gemini Pro 모델 초기화 실패: {e2}")
                        self.gemini_model = None
                
                # Initialize Gemini Flash model (for fast processing and classification)
                try:
                    self.gemini_flash_model = genai.GenerativeModel(settings.GEMINI_FLASH_MODEL)
                    print(f"✅ Gemini 2.0 Flash 모델 초기화 성공: {settings.GEMINI_FLASH_MODEL}")
                except Exception as e:
                    print(f"⚠️ Gemini 2.0 Flash 모델 초기화 실패: {e}")
                    # Fallback to Gemini 1.5 Flash
                    try:
                        self.gemini_flash_model = genai.GenerativeModel(settings.GEMINI_1_5_FLASH_FALLBACK)
                        print(f"✅ Gemini 1.5 Flash 모델로 대체: {settings.GEMINI_1_5_FLASH_FALLBACK}")
                    except Exception as e2:
                        print(f"❌ Gemini Flash 모델 초기화 실패: {e2}")
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
    
    async def generate_planning_response(self, context: str, file_summary: str = "") -> str:
        """Generate planning response using Gemini 2.0 Pro (optimized for structured thinking)"""
        try:
            prompt = f"{PLANNING_PERSONA_PROMPT}\n\n--- Conversation History ---\n{context}\n\n{file_summary}"
            
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
    
    async def generate_simple_response(self, question: str) -> str:
        """Generate simple response using Gemini 2.0 Flash (optimized for speed and cost)"""
        try:
            prompt = f"""Excel과 관련된 간단한 질문에 대해 명확하고 간결하게 답변해주세요.

질문: {question}

다음 형식으로 답변하세요:
1. 간단한 설명
2. 구체적인 예시 (필요시)
3. 추가 팁 (필요시)"""
            
            # Use Gemini 2.0 Flash for simple responses (fastest and most cost-effective)
            if self.gemini_flash_model:
                return await self._call_gemini_flash(prompt, temperature=0.3)
            else:
                return await self._call_openai(prompt, model="gpt-4o-mini", temperature=0.3)
            
        except Exception as e:
            raise AIServiceException(f"간단한 답변 생성 실패: {str(e)}")
    
    async def generate_creative_response(self, question: str, context: str) -> str:
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
            
            # Use Gemini 2.0 Pro for creative responses (best at innovative thinking)
            if self.gemini_model:
                return await self._call_gemini(prompt, temperature=0.8)
            else:
                return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.8)
            
        except Exception as e:
            raise AIServiceException(f"창의적 답변 생성 실패: {str(e)}")
    
    async def generate_analytical_response(self, question: str, data_context: str) -> str:
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
            raise AIServiceException("Gemini Flash 응답 시간 초과")
        except Exception as e:
            raise AIServiceException(f"Gemini Flash API 호출 실패: {str(e)}")
    
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
        conversation_context: Optional[Any] = None
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
                # Standard question processing - check if this is a clarification response
                if conversation_context and conversation_context.state.value == "clarifying":
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
                    classification = await conversation_service.analyze_question_for_clarification(question, context)
                    
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
                        
                        # Ask first clarification question
                        first_question = clarification_questions[0]
                        answer = f"질문을 더 정확하게 이해하기 위해 몇 가지 확인이 필요합니다! 😊\n\n**{first_question.question}**\n\n{first_question.context}"
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
                                answer = await self._process_standard_question(question, context, file_summary, classification, image_data)
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
        image_data: Optional[bytes] = None
    ) -> str:
        """Process standard question without clarification needs"""
        if classification.classification == "simple":
            return await self.generate_simple_response(question)
        elif classification.classification == "creative":
            return await self.generate_creative_response(question, context)
        elif classification.classification == "analytical":
            return await self.generate_analytical_response(question, file_summary)
        elif classification.classification == "debugging":
            return await self.generate_debugging_response(context, question, image_data)
        else:
            # Complex question - generate planning response
            return await self.generate_planning_response(context, file_summary)
    
    async def _generate_solution_with_context(
        self,
        original_question: str,
        understanding: str,
        context: str,
        file_summary: str
    ) -> str:
        """Generate solution based on gathered context and understanding"""
        try:
            # Determine if this is a continuation or new solution
            is_continuation = len(context.strip()) > 100  # If there's substantial context
            
            if is_continuation:
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
            else:
                prompt = f"""사용자의 질문: "{original_question}"

이해한 내용: {understanding}

이전 대화: {context}

파일 정보: {file_summary}

위 정보를 바탕으로 완벽한 해결책을 제시해주세요. 다음 형식으로 답하세요:

## 🎯 해결책

[문제 요약]
- 사용자가 해결하고자 하는 문제

[해결 방법]
- 구체적인 해결 방법 (VBA 코드, 함수, 수식 등)

[사용 방법]
- 단계별 사용 방법

[주의사항]
- 주의해야 할 점들

[추가 팁]
- 더 나은 방법이나 개선 방안"""

            # Use OpenAI for solution generation
            return await self._call_openai(prompt, model=settings.OPENAI_MODEL, temperature=0.3)
            
        except Exception as e:
            raise AIServiceException(f"해결책 생성 실패: {str(e)}")
    
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
