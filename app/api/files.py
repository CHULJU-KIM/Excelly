# app/api/files.py
# File handling API endpoints

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional

from app.services.file_service import file_service
from app.core.exceptions import ExcellyException, handle_excelly_exception

router = APIRouter(prefix="/api/files", tags=["files"])

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and validate file"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate file
        file_service.validate_file(file_content, file.filename)
        
        # Get file info
        file_info = {
            "filename": file.filename,
            "size": len(file_content),
            "content_type": file.content_type
        }
        
        return {
            "message": "파일이 성공적으로 업로드되었습니다.",
            "file_info": file_info
        }
        
    except ExcellyException as e:
        raise handle_excelly_exception(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류 발생: {str(e)}")

@router.post("/analyze")
async def analyze_file(file: UploadFile = File(...)):
    """Analyze file and return detailed information"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Analyze file
        analysis_result = file_service.analyze_excel_file(file_content, file.filename)
        
        return {
            "analysis": analysis_result.dict(),
            "message": "파일 분석이 완료되었습니다."
        }
        
    except ExcellyException as e:
        raise handle_excelly_exception(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 분석 중 오류 발생: {str(e)}")

@router.post("/extract-sheet")
async def extract_sheet_data(
    file: UploadFile = File(...),
    sheet_name: str = Form(...)
):
    """Extract data from specific sheet"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Extract sheet data
        sheet_data = file_service.extract_sheet_data(file_content, sheet_name, file.filename)
        
        return {
            "sheet_name": sheet_name,
            "data": sheet_data,
            "message": "시트 데이터 추출이 완료되었습니다."
        }
        
    except ExcellyException as e:
        raise handle_excelly_exception(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시트 데이터 추출 중 오류 발생: {str(e)}")

@router.post("/process-image")
async def process_image(image: UploadFile = File(...)):
    """Process uploaded image for analysis"""
    try:
        # Read image content
        image_content = await image.read()
        
        # Process image
        image_info = file_service.process_image(image_content)
        
        return {
            "image_info": image_info,
            "message": "이미지 처리가 완료되었습니다."
        }
        
    except ExcellyException as e:
        raise handle_excelly_exception(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 처리 중 오류 발생: {str(e)}")

@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "supported_formats": list(file_service.supported_formats.keys()),
        "max_file_size_mb": file_service.supported_formats.get("max_size", 10)
    }
