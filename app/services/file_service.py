# app/services/file_service.py
# File processing service

import io
import os
from typing import List, Optional, Dict, Any
import pandas as pd
from PIL import Image

from app.models.excel import FileAnalysisResult, ExcelFile, ExcelSheet
from app.core.config import settings
from app.core.exceptions import FileProcessingException, ValidationException

class FileService:
    """Service for processing uploaded files"""
    
    def __init__(self):
        self.supported_formats = {
            '.xlsx': 'excel',
            '.xls': 'excel', 
            '.csv': 'csv',
            '.png': 'image',
            '.jpg': 'image',
            '.jpeg': 'image'
        }
    
    def validate_file(self, file_content: bytes, filename: str) -> bool:
        """Validate uploaded file"""
        # Check file size
        if len(file_content) > settings.MAX_FILE_SIZE:
            raise ValidationException(
                f"파일 크기가 너무 큽니다. 최대 {settings.MAX_FILE_SIZE // (1024*1024)}MB까지 허용됩니다."
            )
        
        # Check file extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in self.supported_formats:
            raise ValidationException(
                f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(self.supported_formats.keys())}"
            )
        
        return True
    
    def analyze_excel_file(self, file_content: bytes, filename: str) -> FileAnalysisResult:
        """Analyze Excel file and extract sheet information"""
        try:
            self.validate_file(file_content, filename)
            
            # Determine file type
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext in ['.xlsx', '.xls']:
                return self._analyze_excel_workbook(file_content, filename)
            elif file_ext == '.csv':
                return self._analyze_csv_file(file_content, filename)
            else:
                raise FileProcessingException(f"지원하지 않는 파일 형식: {file_ext}")
                
        except Exception as e:
            if isinstance(e, (ValidationException, FileProcessingException)):
                raise
            raise FileProcessingException(f"파일 분석 중 오류 발생: {str(e)}")
    
    def _analyze_excel_workbook(self, file_content: bytes, filename: str) -> FileAnalysisResult:
        """Analyze Excel workbook (.xlsx, .xls)"""
        try:
            xls = pd.ExcelFile(io.BytesIO(file_content), engine='openpyxl')
            sheets = []
            
            for sheet_name in xls.sheet_names:
                try:
                    df = pd.read_excel(xls, sheet_name=sheet_name, nrows=5)
                    sheet = ExcelSheet(
                        name=sheet_name,
                        row_count=len(df),
                        column_count=len(df.columns),
                        preview_data=df.head().values.tolist()
                    )
                    sheets.append(sheet)
                except Exception as e:
                    # Skip problematic sheets
                    continue
            
            file_info = ExcelFile(
                filename=filename,
                file_size=len(file_content),
                sheets=sheets,
                file_type='excel'
            )
            
            return FileAnalysisResult(
                sheets=xls.sheet_names,
                file_info=file_info
            )
            
        except Exception as e:
            raise FileProcessingException(f"Excel 파일 분석 실패: {str(e)}")
    
    def _analyze_csv_file(self, file_content: bytes, filename: str) -> FileAnalysisResult:
        """Analyze CSV file"""
        try:
            # Try to detect encoding
            content_str = file_content.decode('utf-8', errors='ignore')
            df = pd.read_csv(io.StringIO(content_str), nrows=5)
            
            sheet = ExcelSheet(
                name='Sheet1',
                row_count=len(df),
                column_count=len(df.columns),
                preview_data=df.head().values.tolist()
            )
            
            file_info = ExcelFile(
                filename=filename,
                file_size=len(file_content),
                sheets=[sheet],
                file_type='csv'
            )
            
            return FileAnalysisResult(
                sheets=['Sheet1'],
                file_info=file_info
            )
            
        except Exception as e:
            raise FileProcessingException(f"CSV 파일 분석 실패: {str(e)}")
    
    def extract_sheet_data(self, file_content: bytes, sheet_name: str, filename: str) -> str:
        """Extract data from specific sheet for AI analysis"""
        try:
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext in ['.xlsx', '.xls']:
                return self._extract_excel_sheet_data(file_content, sheet_name)
            elif file_ext == '.csv':
                return self._extract_csv_data(file_content)
            else:
                raise FileProcessingException(f"지원하지 않는 파일 형식: {file_ext}")
                
        except Exception as e:
            raise FileProcessingException(f"시트 데이터 추출 실패: {str(e)}")
    
    def _extract_excel_sheet_data(self, file_content: bytes, sheet_name: str) -> str:
        """Extract data from Excel sheet"""
        try:
            xls = pd.ExcelFile(io.BytesIO(file_content), engine='openpyxl')
            
            if sheet_name == 'all_sheets':
                # Extract data from all sheets
                all_data = []
                for sheet in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet)
                    all_data.append(f"--- Sheet: '{sheet}' (Top 5 rows) ---\n{df.head().to_string()}\n\n")
                return "".join(all_data)
            else:
                # Extract data from specific sheet
                df = pd.read_excel(xls, sheet_name=sheet_name)
                return f"--- Sheet: '{sheet_name}' (Top 5 rows) ---\n{df.head().to_string()}\n\n"
                
        except Exception as e:
            raise FileProcessingException(f"Excel 시트 데이터 추출 실패: {str(e)}")
    
    def _extract_csv_data(self, file_content: bytes) -> str:
        """Extract data from CSV file"""
        try:
            content_str = file_content.decode('utf-8', errors='ignore')
            df = pd.read_csv(io.StringIO(content_str))
            return f"--- CSV Data (Top 5 rows) ---\n{df.head().to_string()}\n\n"
        except Exception as e:
            raise FileProcessingException(f"CSV 데이터 추출 실패: {str(e)}")
    
    def process_image(self, image_content: bytes) -> Dict[str, Any]:
        """Process uploaded image for analysis"""
        try:
            # Validate image
            image = Image.open(io.BytesIO(image_content))
            
            # Get image info
            image_info = {
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'width': image.width,
                'height': image.height
            }
            
            # Convert to base64 for AI analysis
            import base64
            image_base64 = base64.b64encode(image_content).decode('utf-8')
            
            return {
                'image_info': image_info,
                'base64_data': image_base64,
                'mime_type': f"image/{image.format.lower()}"
            }
            
        except Exception as e:
            raise FileProcessingException(f"이미지 처리 실패: {str(e)}")
    
    def get_file_summary(self, file_content: bytes, filename: str, sheet_name: Optional[str] = None) -> str:
        """Generate file summary for AI context"""
        try:
            analysis_result = self.analyze_excel_file(file_content, filename)
            
            summary = f"[Attached File Analysis 📊]\n"
            summary += f"File: {filename}\n"
            summary += f"Size: {len(file_content) // 1024} KB\n"
            summary += f"Sheets: {', '.join(analysis_result.sheets)}\n\n"
            
            if sheet_name:
                sheet_data = self.extract_sheet_data(file_content, sheet_name, filename)
                summary += sheet_data
            
            return summary
            
        except Exception as e:
            return f"[System Note: Error occurred while analyzing the Excel file: {str(e)}]\n"

# Global file service instance
file_service = FileService()
