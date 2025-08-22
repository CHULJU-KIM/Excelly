# app/api/chat.py
# Chat API endpoints

import time
from fastapi import APIRouter, Form, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from typing import Optional

from app.services.session_service import session_service
from app.services.ai_service import ai_service
from app.services.file_service import file_service
from app.services.file_generation_service import file_generation_service

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
        print(f"🔍 파일 업로드 요청 받음: session_id={session_id}, filename={file.filename}")
        
        # Read file content
        file_content = await file.read()
        print(f"📁 파일 크기: {len(file_content)} bytes")
        
        # Validate and analyze file
        file_service.validate_file(file_content, file.filename)
        print(f"✅ 파일 검증 완료: {file.filename}")
        
        analysis_result = file_service.analyze_excel_file(file_content, file.filename)
        print(f"📊 파일 분석 완료: 시트 수={len(analysis_result.sheets)}")
        
        # 세션 ID 정규화 및 생성
        if not session_id or session_id.strip().lower() in ["null", ""]:
            session_id = f"session_{int(time.time())}"
            print(f"🔄 세션 ID 정규화: {session_id}")
        
        # 세션이 없으면 생성
        existing = session_service.get_session(session_id)
        if not existing:
            session_service.create_session(session_id)
            print(f"✅ 새 세션 생성: {session_id}")
        
        # Store file content and filename in session for later use
        session_service.update_session(session_id, temp_file_content=file_content, filename=file.filename)
        print(f"💾 파일 내용 세션에 저장 완료: {session_id}")
        
        # 저장 확인
        updated_session = session_service.get_session(session_id)
        if updated_session and updated_session.temp_file_content:
            print(f"✅ 파일 내용 저장 확인: {len(updated_session.temp_file_content)} bytes")
        
        result = {"sheets": analysis_result.sheets, "session_id": session_id}
        print(f"🎯 응답 반환: {result}")
        return result
    except Exception as e:
        print(f"❌ 파일 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 분석 실패: {str(e)}")

@router.get("/download/{file_id}")
async def download_file(file_id: str):
    """Download generated file by file ID"""
    try:
        file_path = file_generation_service.get_file_path(file_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        return FileResponse(
            path=file_path,
            filename=f"analysis_result_{file_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 다운로드 실패: {str(e)}")

@router.post("/generate-file")
async def generate_file(session_id: str = Form(...), ai_response: str = Form("")):
    """Generate Excel file from AI response"""
    try:
        print(f"📁 파일 생성 요청: session_id={session_id}, ai_response 길이={len(ai_response)}")
        
        # 세션에서 원본 파일 데이터 가져오기
        session = session_service.get_session(session_id)
        if not session or not session.temp_file_content:
            raise HTTPException(status_code=404, detail="원본 파일 데이터를 찾을 수 없습니다.")
        
        # AI 응답이 비어있으면 기본 메시지 사용
        if not ai_response or ai_response.strip() == "":
            ai_response = "파일 생성 요청으로 인한 분석 결과 파일입니다."
            print(f"⚠️ AI 응답이 비어있어 기본 메시지 사용")
        
        # 선택된 시트 정보 가져오기
        selected_sheet = getattr(session, 'selected_sheet', None)
        print(f"📊 선택된 시트: {selected_sheet}")
        
        # 파일 생성 서비스 호출
        result = file_generation_service.generate_analysis_file(
            session_id=session_id,
            ai_response=ai_response,
            original_file_content=session.temp_file_content,
            selected_sheet=selected_sheet,
            original_filename=session.filename
        )
        
        print(f"✅ 파일 생성 성공: {result}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 파일 생성 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"파일 생성 실패: {str(e)}")

@router.post("/ask")
async def handle_ask_request(
    question: str = Form(""),
    session_id: str = Form(""),
    selected_sheet: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    answer_style: Optional[str] = Form(None)
):
    """Handle chat request with AI processing"""
    try:
        print(f"🔍 질문 요청 받음: session_id={session_id}, question='{question}', selected_sheet='{selected_sheet}'")
        
        # 세션 ID 정규화 및 생성
        if not session_id or session_id.strip().lower() in ["null", ""]:
            session_id = session_service.create_session()
            print(f"✅ 새 세션 생성: {session_id}")
        else:
            # 기존 세션 확인
            existing_session = session_service.get_session(session_id)
            if not existing_session:
                session_id = session_service.create_session()
                print(f"✅ 기존 세션 없음, 새 세션 생성: {session_id}")
            else:
                print(f"✅ 기존 세션 로드: {session_id}")
        
        # 세션 가져오기
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 파일명 처리 통합
        actual_filename = session.filename or "uploaded_file.xlsx"
        
        # 시트 선택 처리 - 세션에 선택된 시트 정보 저장
        if selected_sheet and selected_sheet != "None":
            print(f"🎯 시트 선택됨: {selected_sheet}")
            
            # 선택된 시트 정보를 세션에 저장
            session_service.update_session(session_id, temp_file_content=session.temp_file_content, selected_sheet=selected_sheet)
            print(f"💾 시트 선택 정보 세션에 저장: {selected_sheet}")
            
            # 질문이 비어있으면 시트 구조 정보만 반환 (AI 분석 없음)
            if not question or question.strip() == "":
                print(f"📝 시트 선택만 감지 - 구조 정보만 반환")
                
                # 파일 요약 생성 (간단한 구조 정보만)
                print(f"🔍 get_file_summary 호출 전: actual_filename={actual_filename}")
                file_summary = file_service.get_file_summary(session.temp_file_content, actual_filename, selected_sheet)
                print(f"📊 파일 요약 생성 완료: {len(file_summary)} 문자")
                
                # 시트 구조 정보만 반환 (AI 분석 없음)
                response_data = {
                    "answer": f"✅ **시트 '{selected_sheet}' 선택 완료**\n\n{file_summary}\n\n💡 **다음 단계**: 이제 이 시트에 대해 원하는 분석을 질문해주세요!",
                    "session_id": session_id,
                    "model_used": "시트 선택",
                    "response_type": "sheet_selection",
                    "next_action": "wait_for_question",
                    "conversation_state": None,
                    "model_info": {
                        "model_name": "sheet_selection",
                        "model_type": "시트 선택",
                        "processing_time": 0.1,
                        "classification": "structure_only"
                    }
                }
                
                print(f"✅ 시트 선택 응답 완료: 구조 정보만 반환")
                return response_data
                
            # 질문이 있는 경우는 선택한 시트의 실제 데이터를 제공
            print(f"📊 선택한 시트 '{selected_sheet}'의 실제 데이터 추출")
            sheet_data = file_service.extract_sheet_data(session.temp_file_content, selected_sheet, actual_filename)
            file_summary = f"📊 **선택된 시트**: '{selected_sheet}'\n\n{sheet_data}"
            print(f"📊 시트 데이터 추출 완료: {len(file_summary)} 문자")
        else:
            # 시트가 선택되지 않은 경우, 세션에서 이전에 선택된 시트 정보 확인
            session_selected_sheet = getattr(session, 'selected_sheet', None)
            if session_selected_sheet and session.temp_file_content:
                print(f"📁 세션에서 이전 선택된 시트 사용: {session_selected_sheet}")
                sheet_data = file_service.extract_sheet_data(session.temp_file_content, session_selected_sheet, actual_filename)
                file_summary = f"📊 **선택된 시트**: '{session_selected_sheet}'\n\n{sheet_data}"
                print(f"📊 세션 시트 데이터 추출 완료: {len(file_summary)} 문자")
            else:
                file_summary = ""
                if session.temp_file_content:
                    print(f"📁 파일은 있지만 시트 미선택")
                    print(f"🔍 selected_sheet 값: '{selected_sheet}'")
                    print(f"🔍 session.selected_sheet 값: '{getattr(session, 'selected_sheet', None)}'")
        
        # 이미지 처리
        image_data = None
        if image:
            image_data = await image.read()
            print(f"🖼️ 이미지 업로드됨: {len(image_data)} bytes")
        
        # AI 서비스로 요청 처리 (질문이 있는 경우만)
        ai_response = await ai_service.process_chat_request(
            question=question,
            context="",
            file_summary=file_summary,
            image_data=image_data,
            answer_style=answer_style
        )
        
        # 응답을 데이터베이스에 저장
        session_service.add_message(
            session_id=session_id,
            role="user",
            content=question
        )
        
        session_service.add_message(
            session_id=session_id,
            role="assistant",
            content=ai_response.answer,
            model_used=ai_response.model_used,
            processing_time=ai_response.processing_time,
            metadata={
                "model_used": ai_response.model_used,
                "processing_time": ai_response.processing_time,
                "response_type": ai_response.response_type
            }
        )
        
        # 응답 반환
        response_data = {
            "answer": ai_response.answer,
            "session_id": session_id,
            "model_used": ai_response.model_used,
            "response_type": ai_response.response_type,
            "next_action": ai_response.next_action,
            "conversation_state": ai_response.conversation_state.value if ai_response.conversation_state else None,
            "model_info": ai_response.model_info
        }
        
        print(f"✅ 응답 완료: 모델={ai_response.model_used}, 타입={ai_response.response_type}")
        return response_data
        
    except Exception as e:
        print(f"❌ ask 요청 처리 실패: {e}")
        import traceback
        print(f"❌ 상세 오류: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"요청 처리 실패: {str(e)}")

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
