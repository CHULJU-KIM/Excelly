# app/core/exceptions.py
# Custom exceptions for Excelly AI Assistant

from fastapi import HTTPException
from typing import Optional

class ExcellyException(Exception):
    """Base exception for Excelly AI Assistant"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class AIServiceException(ExcellyException):
    """Exception raised when AI service fails"""
    def __init__(self, message: str = "AI 서비스 오류가 발생했습니다.", status_code: int = 503):
        super().__init__(message, status_code)

class FileProcessingException(ExcellyException):
    """Exception raised when file processing fails"""
    def __init__(self, message: str = "파일 처리 중 오류가 발생했습니다.", status_code: int = 400):
        super().__init__(message, status_code)

class SessionException(ExcellyException):
    """Exception raised when session management fails"""
    def __init__(self, message: str = "세션 관리 오류가 발생했습니다.", status_code: int = 400):
        super().__init__(message, status_code)

class ValidationException(ExcellyException):
    """Exception raised when input validation fails"""
    def __init__(self, message: str = "입력 데이터 검증에 실패했습니다.", status_code: int = 400):
        super().__init__(message, status_code)

def handle_excelly_exception(exc: ExcellyException) -> HTTPException:
    """Convert ExcellyException to FastAPI HTTPException"""
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message
    )
