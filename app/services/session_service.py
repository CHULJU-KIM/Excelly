# app/services/session_service.py
# Session management service with database support

import time
import uuid
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc

from app.models.chat import ChatSession, Message
from app.models.database import DBSession as DBSessionModel, DBMessage
from app.core.config import settings
from app.core.exceptions import SessionException
from app.core.database import SessionLocal

class SessionService:
    """Service for managing chat sessions with database persistence"""
    
    def __init__(self):
        self._last_cleanup = time.time()
    
    def _get_db(self) -> DBSession:
        """Get database session"""
        return SessionLocal()
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new chat session"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        db = self._get_db()
        try:
            # Check if session already exists
            existing_session = db.query(DBSessionModel).filter(
                DBSessionModel.session_id == session_id
            ).first()
            
            if existing_session:
                raise SessionException(f"Session {session_id} already exists")
            
            # Create new session
            db_session = DBSessionModel(
                session_id=session_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            
            return session_id
            
        except Exception as e:
            db.rollback()
            raise SessionException(f"Failed to create session: {str(e)}")
        finally:
            db.close()
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID"""
        db = self._get_db()
        try:
            db_session = db.query(DBSessionModel).filter(
                DBSessionModel.session_id == session_id
            ).first()
            
            if not db_session:
                return None
            
            # Convert to ChatSession model
            messages = []
            for db_message in db_session.messages:
                message = Message(
                    role=db_message.role,
                    content=db_message.content,
                    timestamp=db_message.timestamp
                )
                messages.append(message)
            
            # Parse metadata
            metadata = {}
            if db_session.metadata_json:
                try:
                    metadata = json.loads(db_session.metadata_json)
                except json.JSONDecodeError:
                    metadata = {}
            
            return ChatSession(
                session_id=db_session.session_id,
                messages=messages,
                plan=db_session.plan,
                temp_file_content=db_session.temp_file_content,
                filename=db_session.filename,
                selected_sheet=db_session.selected_sheet,
                timestamp=db_session.created_at.timestamp(),
                metadata=metadata
            )
            
        finally:
            db.close()
    
    def update_session(self, session_id: str, **kwargs) -> bool:
        """Update session data"""
        db = self._get_db()
        try:
            db_session = db.query(DBSessionModel).filter(
                DBSessionModel.session_id == session_id
            ).first()
            
            if not db_session:
                return False
            
            # Update fields
            for key, value in kwargs.items():
                # Special handling for metadata - store as JSON string regardless of model attribute
                if key == "metadata" and isinstance(value, dict):
                    db_session.metadata_json = json.dumps(value)
                    continue
                # Special handling for temp_file_content - ensure it's preserved
                if key == "temp_file_content" and value is not None:
                    print(f"💾 세션 {session_id}에 파일 내용 저장: {len(value)} bytes")
                    db_session.temp_file_content = value
                    continue
                if hasattr(db_session, key):
                    setattr(db_session, key, value)
            
            db_session.updated_at = datetime.utcnow()
            db.commit()
            print(f"✅ 세션 {session_id} 업데이트 완료")
            return True
            
        except Exception as e:
            db.rollback()
            print(f"❌ 세션 업데이트 실패: {e}")
            return False
        finally:
            db.close()
    
    def add_message(self, session_id: str, role: str, content: str, 
                   model_used: Optional[str] = None, 
                   processing_time: Optional[float] = None,
                   message_type: str = "normal",
                   metadata: Optional[Dict] = None) -> bool:
        """Add a message to a session"""
        db = self._get_db()
        try:
            # Check if session exists
            db_session = db.query(DBSessionModel).filter(
                DBSessionModel.session_id == session_id
            ).first()
            
            if not db_session:
                return False
            
            # Create message
            db_message = DBMessage(
                session_id=session_id,
                role=role,
                content=content,
                timestamp=datetime.utcnow(),
                model_used=model_used,
                processing_time=processing_time,
                message_type=message_type,
                metadata_json=json.dumps(metadata) if metadata else None
            )
            
            db.add(db_message)
            db_session.updated_at = datetime.utcnow()
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()
    
    def update_conversation_context(self, session_id: str, conversation_context: Any) -> bool:
        """Update conversation context for a session (stored under metadata_json).
        Stores minimal pending question info to allow continuity."""
        try:
            # Convert conversation context to dict for storage
            context_dict = {
                "state": conversation_context.state.value if hasattr(conversation_context.state, 'value') else str(conversation_context.state),
                "clarification_count": conversation_context.clarification_count,
                "max_clarifications": conversation_context.max_clarifications,
                "gathered_info": conversation_context.gathered_info,
                "original_question": conversation_context.original_question,
                "current_understanding": conversation_context.current_understanding
            }
            # Persist first pending clarification (lightweight)
            try:
                if getattr(conversation_context, 'pending_clarifications', None):
                    first = conversation_context.pending_clarifications[0]
                    context_dict["pending_question"] = {
                        "question": getattr(first, 'question', None),
                        "context": getattr(first, 'context', None),
                        "question_type": getattr(first, 'question_type', None),
                        "is_required": getattr(first, 'is_required', True)
                    }
            except Exception:
                pass

            # Merge with existing metadata to avoid overwriting other keys
            existing = {}
            session = self.get_session(session_id)
            if session and isinstance(session.metadata, dict):
                existing = dict(session.metadata)
            existing["conversation_context"] = context_dict

            return self.update_session(session_id, metadata=existing)
        except Exception:
            return False
    
    def get_conversation_context(self, session_id: str) -> Optional[Any]:
        """Get conversation context for a session"""
        try:
            session = self.get_session(session_id)
            if session and session.metadata.get("conversation_context"):
                from app.models.chat import ConversationContext, ConversationState
                from app.models.chat import ClarificationQuestion
                context_data = session.metadata["conversation_context"]
                ctx = ConversationContext(
                    state=ConversationState(context_data["state"]),
                    clarification_count=context_data["clarification_count"],
                    max_clarifications=context_data["max_clarifications"],
                    pending_clarifications=[],
                    gathered_info=context_data["gathered_info"],
                    original_question=context_data["original_question"],
                    current_understanding=context_data["current_understanding"]
                )
                # Reconstruct one pending question if present
                try:
                    pq = context_data.get("pending_question")
                    if pq and pq.get("question"):
                        ctx.pending_clarifications = [ClarificationQuestion(
                            question=pq.get("question"),
                            context=pq.get("context") or "추가 정보를 확인하기 위해 필요합니다.",
                            question_type=pq.get("question_type") or "goal",
                            is_required=pq.get("is_required", True)
                        )]
                except Exception:
                    pass
                return ctx
            return None
        except Exception as e:
            return None
    
    def get_messages(self, session_id: str) -> List[Message]:
        """Get all messages from a session"""
        db = self._get_db()
        try:
            db_messages = db.query(DBMessage).filter(
                DBMessage.session_id == session_id
            ).order_by(DBMessage.timestamp).all()
            
            messages = []
            for db_message in db_messages:
                msg_metadata = {}
                if db_message.metadata_json:
                    try:
                        msg_metadata = json.loads(db_message.metadata_json)
                    except json.JSONDecodeError:
                        msg_metadata = {}
                message = Message(
                    role=db_message.role,
                    content=db_message.content,
                    timestamp=db_message.timestamp,
                    message_type=db_message.message_type or "normal",
                    metadata=msg_metadata
                )
                messages.append(message)
            
            return messages
            
        finally:
            db.close()
    
    def get_all_sessions(self) -> List[Dict]:
        """Get list of all sessions with basic info"""
        db = self._get_db()
        try:
            db_sessions = db.query(DBSessionModel).order_by(
                desc(DBSessionModel.updated_at)
            ).all()
            
            sessions = []
            for db_session in db_sessions:
                # Get first message
                first_message = "새 대화"
                first_db_message = db.query(DBMessage).filter(
                    DBMessage.session_id == db_session.session_id
                ).order_by(DBMessage.timestamp).first()
                
                if first_db_message:
                    first_message = first_db_message.content
                    if first_message.startswith("질문: "):
                        first_message = first_message[4:].strip()
                
                # Get message count
                message_count = db.query(DBMessage).filter(
                    DBMessage.session_id == db_session.session_id
                ).count()
                
                sessions.append({
                    "session_id": db_session.session_id,
                    "first_message": first_message,
                    "timestamp": db_session.updated_at.timestamp(),
                    "message_count": message_count
                })
            
            return sessions
            
        finally:
            db.close()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        db = self._get_db()
        try:
            db_session = db.query(DBSessionModel).filter(
                DBSessionModel.session_id == session_id
            ).first()
            
            if not db_session:
                return False
            
            db.delete(db_session)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()
    
    def clear_session_messages(self, session_id: str) -> bool:
        """Clear all messages from a session but keep the session"""
        db = self._get_db()
        try:
            db_session = db.query(DBSessionModel).filter(
                DBSessionModel.session_id == session_id
            ).first()
            
            if not db_session:
                return False
            
            # Delete all messages for this session
            db.query(DBMessage).filter(
                DBMessage.session_id == session_id
            ).delete()
            
            # Clear conversation context and plan
            db_session.plan = None
            db_session.metadata_json = None
            db_session.updated_at = datetime.utcnow()
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()
    
    def clear_all_sessions(self) -> bool:
        """Clear all sessions and their messages from the database"""
        db = self._get_db()
        try:
            # Delete all messages first
            db.query(DBMessage).delete()
            
            # Delete all sessions
            db.query(DBSessionModel).delete()
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()
    
    def cleanup_sessions(self) -> int:
        """Clean up expired sessions"""
        db = self._get_db()
        try:
            cutoff_time = datetime.utcnow() - timedelta(seconds=settings.SESSION_TIMEOUT)
            
            expired_sessions = db.query(DBSessionModel).filter(
                DBSessionModel.updated_at < cutoff_time
            ).all()
            
            count = len(expired_sessions)
            for session in expired_sessions:
                db.delete(session)
            
            db.commit()
            return count
            
        except Exception as e:
            db.rollback()
            return 0
        finally:
            db.close()
    
    def _cleanup_old_sessions(self):
        """Internal method to cleanup old sessions periodically"""
        current_time = time.time()
        if current_time - self._last_cleanup > 300:  # Cleanup every 5 minutes
            self.cleanup_sessions()
            self._last_cleanup = current_time
    
    def get_session_stats(self) -> Dict:
        """Get session statistics"""
        db = self._get_db()
        try:
            total_sessions = db.query(DBSessionModel).count()
            total_messages = db.query(DBMessage).count()
            
            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "active_sessions": total_sessions,
                "last_cleanup": self._last_cleanup
            }
        finally:
            db.close()

# Global session service instance
session_service = SessionService()
