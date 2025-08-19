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
            content_str = None
            try:
                import charset_normalizer as cn
                detection = cn.from_bytes(file_content).best()
                if detection and detection.encoding:
                    content_str = file_content.decode(detection.encoding, errors='ignore')
                else:
                    content_str = file_content.decode('utf-8', errors='ignore')
            except Exception:
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
                    all_data.append(f"📋 시트: '{sheet}' (상위 5행)\n")
                    all_data.append(f"행 수: {len(df)}, 열 수: {len(df.columns)}\n")
                    all_data.append(f"열 이름: {list(df.columns)}\n")
                    all_data.append(f"{df.head().to_string()}\n\n")
                return "".join(all_data)
            else:
                # Extract data from specific sheet
                df = pd.read_excel(xls, sheet_name=sheet_name)
                result = f"📋 시트: '{sheet_name}' (상위 5행)\n"
                result += f"행 수: {len(df)}, 열 수: {len(df.columns)}\n"
                result += f"열 이름: {list(df.columns)}\n"
                result += f"{df.head().to_string()}\n\n"
                
                # 추가 정보: 빈 셀, 데이터 타입 등
                empty_cells = df.isnull().sum().sum()
                total_cells = df.size
                result += f"📊 데이터 통계:\n"
                result += f"- 총 셀 수: {total_cells}\n"
                result += f"- 빈 셀 수: {empty_cells}\n"
                result += f"- 데이터 채움률: {((total_cells - empty_cells) / total_cells * 100):.1f}%\n"
                
                return result
                
        except Exception as e:
            raise FileProcessingException(f"Excel 시트 데이터 추출 실패: {str(e)}")
    
    def _extract_csv_data(self, file_content: bytes) -> str:
        """Extract data from CSV file"""
        try:
            content_str = None
            try:
                import charset_normalizer as cn
                detection = cn.from_bytes(file_content).best()
                if detection and detection.encoding:
                    content_str = file_content.decode(detection.encoding, errors='ignore')
                else:
                    content_str = file_content.decode('utf-8', errors='ignore')
            except Exception:
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
        """Generate optimized file summary for AI context"""
        try:
            analysis_result = self.analyze_excel_file(file_content, filename)
            
            summary = f"📊 **파일 분석**: {filename} ({len(file_content) // 1024}KB)\n"
            summary += f"📋 **시트**: {len(analysis_result.sheets)}개 - {', '.join(analysis_result.sheets)}\n\n"
            
            if sheet_name and sheet_name != "all_sheets":
                # 특정 시트 선택된 경우
                summary += f"🎯 **선택된 시트**: '{sheet_name}'\n"
                try:
                    xls = pd.ExcelFile(io.BytesIO(file_content), engine='openpyxl')
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    
                    summary += f"📈 **구조**: {len(df)}행 × {len(df.columns)}열\n"
                    summary += f"📝 **열명**: {list(df.columns)}\n"
                    
                    # 데이터 미리보기 (간소화)
                    summary += f"👀 **미리보기** (상위 3행):\n"
                    summary += df.head(3).to_string(index=False) + "\n"
                    
                except Exception as e:
                    summary += f"⚠️ **오류**: {str(e)}\n"
            
            elif sheet_name == "all_sheets":
                # 모든 시트 요청된 경우
                summary += f"📋 **전체 시트 데이터**\n"
                try:
                    sheet_data = self.extract_sheet_data(file_content, "all_sheets", filename)
                    summary += sheet_data
                except Exception as e:
                    summary += f"⚠️ **오류**: {str(e)}\n"
            
            else:
                # 시트가 선택되지 않은 경우
                summary += f"💡 **시트를 선택해주세요**\n"
                summary += f"위 시트 목록에서 분석할 시트를 선택하시면 자세한 분석을 제공합니다.\n"
            
            return summary
            
        except Exception as e:
            return f"❌ **파일 분석 오류**: {str(e)}\n"

# Global file service instance
file_service = FileService()
