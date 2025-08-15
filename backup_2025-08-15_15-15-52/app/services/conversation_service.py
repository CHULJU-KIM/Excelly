# app/services/conversation_service.py
# Conversation management service for multi-turn dialogue

import json
from typing import List, Optional, Dict, Any
from app.models.chat import (
    ConversationContext, ConversationState, ClarificationQuestion,
    QuestionClassification, AIResponse
)
from app.services.ai_service import ai_service
from app.core.exceptions import ExcellyException

class ConversationService:
    """Service for managing multi-turn conversations and clarification dialogues"""
    
    def __init__(self):
        self.max_clarifications = 2  # 최대 2회로 제한
    
    async def analyze_question_for_clarification(self, question: str, context: str = "") -> QuestionClassification:
        """Analyze if a question needs clarification and what type"""
        try:
            # 즉시 답변 키워드(명확한 Excel 요청)
            immediate_answer_keywords = [
                "VLOOKUP", "HLOOKUP", "INDEX", "MATCH", "IF", "SUM", "COUNT", "AVERAGE",
                "B열", "C열", "D열", "E열", "F열", "G열", "H열", "I열", "J열", "K열", "L열",
                "1행", "2행", "3행", "4행", "5행", "6행", "7행", "8행", "9행", "10행",
                "서식", "불일치", "공백", "오류", "해결", "방법", "어떻게", "왜", "안되",
                "코드", "값", "찾기", "반환", "일치", "정확", "문제", "수정", "개선"
            ]

            # '계속/이어서' 등 이어달라는 의도 키워드 (비내용적)
            continuation_keywords = [
                "계속", "계속해", "계속해줘", "계속해죠", "이어서", "이어", "진행", "진행해", "continue"
            ]

            q = question.strip()
            q_lower = q.lower()
            has_immediate = any(k.lower() in q_lower for k in immediate_answer_keywords)
            is_continuation = any(k in q for k in continuation_keywords)
            is_too_short = len(q) <= 4  # 매우 짧은 일반 발화

            # 1) 명확한 Excel 요청 → 즉시 답변
            if has_immediate:
                return QuestionClassification(
                    classification="debugging" if ("오류" in q or "문제" in q) else "simple",
                    confidence=0.9,
                    reasoning="구체 키워드를 포함한 Excel 요청",
                    recommended_model="openai",
                    estimated_tokens=1000,
                    needs_clarification=False,
                    clarification_reasons=[]
                )

            # 2) 이어서/계속 의도 또는 매우 짧은 일반 발화 → 명확화 필요
            if is_continuation or is_too_short or len(q.split()) <= 2:
                return QuestionClassification(
                    classification="complex",
                    confidence=0.7,
                    reasoning="이어달라는 요청 또는 너무 짧아 의도 불명확",
                    recommended_model="openai",
                    estimated_tokens=500,
                    needs_clarification=True,
                    clarification_reasons=["goal"]
                )

            # 3) 그 외 모호한 요청 → 명확화 필요
            return QuestionClassification(
                classification="complex",
                confidence=0.6,
                reasoning="모호한 요청으로 추가 정보 필요",
                recommended_model="openai",
                estimated_tokens=800,
                needs_clarification=True,
                clarification_reasons=["구체적인 작업 내용 불분명"]
            )

            # 키워드 기반 판단 결과 반환
            return QuestionClassification(
                classification="debugging" if "오류" in question or "문제" in question else "simple",
                confidence=0.9,
                reasoning="구체적인 Excel 문제로 즉시 답변 가능",
                recommended_model="openai",
                estimated_tokens=1000,
                needs_clarification=False,
                clarification_reasons=[]
            )
                
        except Exception as e:
            return QuestionClassification(
                classification="complex",
                confidence=0.5,
                reasoning=f"분석 실패: {str(e)}",
                recommended_model="openai",
                estimated_tokens=1000,
                needs_clarification=True,
                clarification_reasons=["시스템 오류로 명확화 필요"]
            )
    
    async def generate_clarification_questions(
        self, 
        question: str, 
        clarification_type: str,
        context: str = ""
    ) -> List[ClarificationQuestion]:
        """Generate specific clarification questions based on type"""
        try:
            clarification_prompts = {
                "file_structure": f"""사용자의 질문: "{question}"
이전 대화: "{context}"

파일 구조에 대한 핵심 정보만 확인하는 질문을 생성하세요.

**중요**: 
- 중복 질문 금지
- 결과 형태나 목표 질문 금지
- 오직 파일 구조 정보만

확인할 정보:
- 작업할 시트 이름 (시트가 여러 개인 경우)
- 데이터 범위 (전체 범위인지 특정 범위인지)

**예시 질문:**
"어떤 시트에서 작업하시나요?" (시트가 여러 개인 경우만)
"전체 데이터 범위를 사용하시나요, 아니면 특정 범위만 사용하시나요?"

간단한 질문 1개만 생성하세요.""",
                
                "data_format": f"""사용자의 질문: "{question}"
이전 대화: "{context}"

데이터 형식에 대한 핵심 정보만 확인하는 질문을 생성하세요.

**중요**: 
- 중복 질문 금지
- 결과 형태나 목표 질문 금지
- 오직 데이터 형식 정보만

확인할 정보:
- 데이터 타입 (숫자/텍스트/날짜)
- 특별한 형식 규칙 (앞에 0 붙는지, 특수문자 포함 등)

**예시 질문:**
"데이터가 숫자인가요, 텍스트인가요?"
"코드에 특수문자나 공백이 포함되어 있나요?"

간단한 질문 1개만 생성하세요.""",
                
                "goal": f"""사용자의 질문: "{question}"
이전 대화: "{context}"

작업 목표에 대한 핵심 정보만 확인하는 질문을 생성하세요.

**중요**: 
- 중복 질문 금지
- 결과 형태나 최종 출력 질문 금지
- 오직 작업 조건만

확인할 정보:
- 구체적인 작업 조건
- 특별한 요구사항

**예시 질문:**
"어떤 조건으로 데이터를 필터링하시나요?"
"자동화가 필요한 작업인가요, 일회성 작업인가요?"

간단한 질문 1개만 생성하세요.""",
                
                "constraints": f"""사용자의 질문: "{question}"
이전 대화: "{context}"

작업 환경에 대한 핵심 정보만 확인하는 질문을 생성하세요.

**중요**: 
- 중복 질문 금지
- 결과 형태나 목표 질문 금지
- 오직 환경 제약사항만

확인할 정보:
- Excel 버전
- VBA 사용 가능 여부

**예시 질문:**
"사용 중인 Excel 버전이 어떻게 되시나요?"
"VBA 매크로 사용이 가능한 환경인가요?"

간단한 질문 1개만 생성하세요."""
            }
            
            prompt = clarification_prompts.get(clarification_type, clarification_prompts["goal"])
            
            # Use Gemini for generating clarification questions
            if ai_service.gemini_model:
                response = await ai_service._call_gemini(prompt, temperature=0.7)
            else:
                response = await ai_service._call_openai(prompt, model="gpt-4o-mini", temperature=0.7)
            
            # Parse the response to extract questions
            questions = self._parse_clarification_questions(response, clarification_type)
            return questions
            
        except Exception as e:
            # Fallback questions based on clarification type
            fallback_questions = {
                "file_structure": ClarificationQuestion(
                    question="어떤 시트에서 작업하시나요?",
                    context="파일 구조를 정확히 파악하기 위해 필요합니다.",
                    question_type=clarification_type,
                    is_required=True
                ),
                "data_format": ClarificationQuestion(
                    question="데이터가 숫자인가요, 텍스트인가요?",
                    context="데이터 형식을 정확히 파악하기 위해 필요합니다.",
                    question_type=clarification_type,
                    is_required=True
                ),
                "goal": ClarificationQuestion(
                    question="어떤 조건으로 작업하시나요?",
                    context="작업 목표를 정확히 파악하기 위해 필요합니다.",
                    question_type=clarification_type,
                    is_required=True
                ),
                "constraints": ClarificationQuestion(
                    question="사용 중인 Excel 버전이 어떻게 되시나요?",
                    context="환경 제약사항을 정확히 파악하기 위해 필요합니다.",
                    question_type=clarification_type,
                    is_required=True
                )
            }
            return [fallback_questions.get(clarification_type, fallback_questions["goal"])]
    
    def _parse_clarification_questions(self, response: str, question_type: str) -> List[ClarificationQuestion]:
        """Parse AI response to extract clarification questions"""
        questions = []
        
        # Simple parsing - split by numbered questions
        lines = response.split('\n')
        current_question = ""
        current_context = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line starts with number or bullet
            if line[0].isdigit() or line.startswith('-') or line.startswith('•'):
                # Save previous question if exists
                if current_question:
                    questions.append(ClarificationQuestion(
                        question=current_question,
                        context=current_context or f"{question_type} 관련 정보를 확인하기 위해 필요합니다.",
                        question_type=question_type,
                        is_required=True
                    ))
                
                # Start new question
                current_question = line.lstrip('1234567890.-• ').strip()
                current_context = ""
            elif current_question and line:
                # This might be context or options
                if not current_context:
                    current_context = line
                else:
                    current_question += " " + line
        
        # Add the last question
        if current_question:
            questions.append(ClarificationQuestion(
                question=current_question,
                context=current_context or f"{question_type} 관련 정보를 확인하기 위해 필요합니다.",
                question_type=question_type,
                is_required=True
            ))
        
        # If no questions were parsed, create a type-specific fallback
        if not questions:
            fallback_questions = {
                "file_structure": "어떤 시트에서 작업하시나요?",
                "data_format": "데이터가 숫자인가요, 텍스트인가요?",
                "goal": "어떤 조건으로 작업하시나요?",
                "constraints": "사용 중인 Excel 버전이 어떻게 되시나요?"
            }
            fallback_question = fallback_questions.get(question_type, "어떤 조건으로 작업하시나요?")
            questions.append(ClarificationQuestion(
                question=fallback_question,
                context=f"{question_type} 관련 정보를 정확히 파악하기 위해 필요합니다.",
                question_type=question_type,
                is_required=True
            ))
        
        return questions[:1]  # Limit to 1 question only
    
    async def process_clarification_response(
        self, 
        conversation_context: ConversationContext,
        user_answer: str
    ) -> ConversationContext:
        """Process user's response to clarification question"""
        try:
            # Update gathered information
            if conversation_context.pending_clarifications:
                current_question = conversation_context.pending_clarifications[0]
                conversation_context.gathered_info[current_question.question_type] = user_answer
            
            # Remove the answered question
            if conversation_context.pending_clarifications:
                conversation_context.pending_clarifications.pop(0)
            
            # Update clarification count
            conversation_context.clarification_count += 1
            
            # Check if we have enough information or reached max clarifications
            if (not conversation_context.pending_clarifications or 
                conversation_context.clarification_count >= conversation_context.max_clarifications):
                
                # Generate final understanding
                understanding = await self._generate_final_understanding(
                    conversation_context.original_question,
                    conversation_context.gathered_info
                )
                conversation_context.current_understanding = understanding
                conversation_context.state = ConversationState.PLANNING
            else:
                conversation_context.state = ConversationState.CLARIFYING
            
            return conversation_context
            
        except Exception as e:
            # On error, move to planning state
            conversation_context.state = ConversationState.PLANNING
            return conversation_context
    
    async def _generate_final_understanding(
        self, 
        original_question: str, 
        gathered_info: Dict[str, Any]
    ) -> str:
        """Generate final understanding based on gathered information"""
        try:
            info_summary = "\n".join([f"{k}: {v}" for k, v in gathered_info.items()])
            
            prompt = f"""원래 질문: "{original_question}"
수집된 정보:
{info_summary}

위 정보를 바탕으로 사용자의 요구사항을 명확하게 정리해주세요. 
다음 형식으로 답하세요:

[문제 정의]
- 사용자가 해결하고자 하는 문제

[요구사항]
- 구체적인 요구사항들

[제약사항]
- 확인된 제약사항들

[예상 결과]
- 사용자가 원하는 최종 결과"""

            # Use Gemini for understanding generation
            if ai_service.gemini_model:
                return await ai_service._call_gemini(prompt, temperature=0.5)
            else:
                return await ai_service._call_openai(prompt, model="gpt-4o-mini", temperature=0.5)
                
        except Exception as e:
            return f"원래 질문: {original_question}\n수집된 정보: {gathered_info}"
    
    def should_continue_clarification(self, conversation_context: ConversationContext) -> bool:
        """Check if clarification should continue"""
        return (conversation_context.state == ConversationState.CLARIFYING and
                conversation_context.clarification_count < conversation_context.max_clarifications and
                conversation_context.pending_clarifications)
    
    def create_conversation_context(self, original_question: str) -> ConversationContext:
        """Create new conversation context"""
        return ConversationContext(
            state=ConversationState.INITIAL,
            clarification_count=0,
            max_clarifications=self.max_clarifications,
            pending_clarifications=[],
            gathered_info={},
            original_question=original_question,
            current_understanding=""
        )

# Global conversation service instance
conversation_service = ConversationService()
