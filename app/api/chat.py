# app/api/chat.py
# Chat API endpoints

import time
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional

from app.services.session_service import session_service
from app.services.ai_service import ai_service
from app.services.file_service import file_service
from app.services.conversation_service import conversation_service
from app.core.exceptions import ExcellyException, handle_excelly_exception
from app.models.chat import AIResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.get("/sessions")
async def get_sessions():
    """Get all chat sessions"""
    try:
        sessions = session_service.get_all_sessions()
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history for a specific session"""
    try:
        # Check if session exists first
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        messages = session_service.get_messages(session_id)
        
        # Get conversation context
        conversation_context = session_service.get_conversation_context(session_id)
        
        # Convert to dict format for JSON response
        message_list = []
        for msg in messages:
            message_data = {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
            }
            
            # Add metadata if available
            if hasattr(msg, 'metadata') and msg.metadata:
                message_data["metadata"] = msg.metadata
            
            message_list.append(message_data)
        
        return {
            "messages": message_list,
            "conversation_context": conversation_context.dict() if conversation_context else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-sheets")
async def analyze_sheets(session_id: str = Form(...), file: UploadFile = File(...)):
    """Analyze uploaded Excel file and return sheet information"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate and analyze file
        file_service.validate_file(file_content, file.filename)
        analysis_result = file_service.analyze_excel_file(file_content, file.filename)
        
        # Store file content in session for later use
        session_service.update_session(session_id, temp_file_content=file_content)
        
        return {"sheets": analysis_result.sheets}
        
    except ExcellyException as e:
        raise handle_excelly_exception(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 분석 중 오류 발생: {str(e)}")

@router.post("/ask")
async def handle_ask_request(
    session_id: str = Form(...),
    question: str = Form(""),
    selected_sheet: Optional[str] = Form(None),
    is_feedback: bool = Form(False),
    image: Optional[UploadFile] = File(None)
):
    """Main chat endpoint for handling user questions with conversation management"""
    try:
        # Ensure session exists and create if it doesn't
        session = session_service.get_session(session_id)
        if not session:
            try:
                session_service.create_session(session_id)
                print(f"✅ Created new session: {session_id}")
            except Exception as e:
                print(f"❌ Failed to create session {session_id}: {e}")
                # If session creation fails, try to use existing session or create with different ID
                session_id = f"session_{int(time.time())}_{hash(question) % 10000}"
                session_service.create_session(session_id)
                print(f"✅ Created fallback session: {session_id}")
        
        # Add user message to session
        session_service.add_message(session_id, "user", question)
        
        # Get session data
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # Get conversation context
        conversation_context = session_service.get_conversation_context(session_id)
        
        # Process image if provided
        image_data = None
        if image:
            image_content = await image.read()
            image_data = image_content
        
        # Build conversation context
        context = "\n".join([
            f"[{msg.role}] {msg.content}" 
            for msg in session.messages[:-1]  # Exclude current message
        ])
        
        # Handle file analysis if sheet is selected
        file_summary = ""
        if selected_sheet and session.temp_file_content:
            try:
                file_summary = file_service.get_file_summary(
                    session.temp_file_content, 
                    "uploaded_file.xlsx", 
                    selected_sheet
                )
                # Clear temp file content after use
                session_service.update_session(session_id, temp_file_content=None)
            except Exception as e:
                file_summary = f"[파일 분석 오류: {str(e)}]"
        
        # Process with enhanced AI service including conversation management
        ai_response = await ai_service.process_chat_request(
            question=question,
            context=context,
            file_summary=file_summary,
            is_feedback=is_feedback,
            image_data=image_data,
            conversation_context=conversation_context
        )
        ai_answer = ai_response.answer
        response_type = ai_response.response_type
        next_action = ai_response.next_action
        conversation_state = ai_response.conversation_state
        
        # Update conversation context if provided
        if conversation_state and conversation_context:
            conversation_context.state = conversation_state
            session_service.update_conversation_context(session_id, conversation_context)
        
        # Add AI response to session with enhanced metadata
        session_service.add_message(
            session_id, 
            "assistant", 
            ai_answer,
            model_used=ai_response.model_used if hasattr(ai_response, 'model_used') else None,
            processing_time=ai_response.processing_time if hasattr(ai_response, 'processing_time') else None,
            message_type=response_type,
            metadata={
                "response_type": response_type,
                "next_action": next_action,
                "conversation_state": conversation_state.value if conversation_state else None
            }
        )
        
        return {
            "answer": ai_answer,
            "session_id": session_id,
            "response_type": response_type,
            "next_action": next_action,
            "conversation_state": conversation_state.value if conversation_state else None
        }
        
    except ExcellyException as e:
        raise handle_excelly_exception(e)
    except Exception as e:
        # Clear plan on error
        if session_id:
            session_service.update_session(session_id, plan=None)
        raise HTTPException(status_code=500, detail=f"AI 전문가와 연결 중 오류가 발생했습니다: {str(e)}")

@router.delete("/sessions/all")
async def clear_all_sessions():
    """Clear all sessions and their messages"""
    try:
        success = session_service.clear_all_sessions()
        if not success:
            raise HTTPException(status_code=500, detail="대화 기록 삭제에 실패했습니다.")
        return {"message": "모든 대화 기록이 지워졌습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session"""
    try:
        success = session_service.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        return {"message": "세션이 삭제되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}/messages")
async def clear_session_messages(session_id: str):
    """Clear all messages from a session but keep the session"""
    try:
        success = session_service.clear_session_messages(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        return {"message": "대화 기록이 지워졌습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_service_status():
    """Get service status information"""
    try:
        ai_status = ai_service.get_service_status()
        session_stats = session_service.get_session_stats()
        
        return {
            "ai_service": ai_status,
            "session_service": session_stats,
            "status": "healthy"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
