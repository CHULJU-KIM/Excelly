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
            '.xlsm': 'excel',  # Excel 매크로 포함 파일
            '.xlsb': 'excel',  # Excel 바이너리 파일
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
            
            if file_ext in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
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
        """Analyze Excel workbook (.xlsx, .xls, .xlsm, .xlsb)"""
        try:
            # 엔진 선택 (.xls는 xlrd, .xlsx/.xlsm/.xlsb는 openpyxl)
            engine = 'xlrd' if filename.lower().endswith('.xls') else 'openpyxl'
            
            xls = pd.ExcelFile(io.BytesIO(file_content), engine=engine)
            sheets = []
            
            for sheet_name in xls.sheet_names:
                try:
                    df = pd.read_excel(xls, sheet_name=sheet_name, nrows=5, engine=engine)
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
        """Extract actual sheet data for AI analysis"""
        try:
            print(f"🔍 extract_sheet_data 호출: sheet_name={sheet_name}, filename={filename}")
            
            # 엔진 선택 (.xls는 xlrd, .xlsx/.xlsm/.xlsb는 openpyxl)
            engine = 'xlrd' if filename.lower().endswith('.xls') else 'openpyxl'
            
            if sheet_name == "all_sheets":
                # 모든 시트 데이터 추출
                xls = pd.ExcelFile(io.BytesIO(file_content), engine=engine)
                all_data = ""
                
                for sheet in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet, engine=engine)
                    all_data += f"📊 **시트: {sheet}** ({len(df)}행 × {len(df.columns)}열)\n"
                    all_data += f"📝 **열명**: {list(df.columns)}\n"
                    all_data += f"📋 **데이터**:\n{df.to_string(index=False)}\n\n"
                
                return all_data
            else:
                # 특정 시트 데이터 추출
                xls = pd.ExcelFile(io.BytesIO(file_content), engine=engine)
                df = pd.read_excel(xls, sheet_name=sheet_name, engine=engine)
                
                print(f"📈 시트 데이터 추출: {len(df)}행 × {len(df.columns)}열")
                
                # 실제 데이터를 문자열로 변환 (강화된 버전)
                data_str = f"📊 **시트: {sheet_name}** ({len(df)}행 × {len(df.columns)}열)\n"
                data_str += f"📝 **열명**: {list(df.columns)}\n"
                data_str += f"📋 **실제 데이터 (원본 그대로)**:\n"
                data_str += f"⚠️ **중요**: 아래 데이터는 실제 원본 데이터입니다. 가상의 이름이나 값을 사용하지 마세요.\n"
                data_str += f"{df.to_string(index=False)}\n"
                
                # 숫자형 열의 기본 통계 추가
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    data_str += f"\n📊 **숫자형 열 통계**:\n"
                    for col in numeric_cols:
                        data_str += f"- {col}: 평균={df[col].mean():.2f}, 최대={df[col].max()}, 최소={df[col].min()}\n"
                
                print(f"✅ 시트 데이터 추출 완료: {len(data_str)} 문자")
                return data_str
                
        except Exception as e:
            print(f"❌ extract_sheet_data 실패: {e}")
            return f"❌ **데이터 추출 오류**: {str(e)}\n"
    
    def process_image(self, image_content: bytes) -> Dict[str, Any]:
        """Process uploaded image for Flash model analysis"""
        try:
            print(f"🖼️ 이미지 처리 시작: {len(image_content)} bytes")
            
            # Validate image
            image = Image.open(io.BytesIO(image_content))
            print(f"🖼️ 이미지 정보: {image.format}, {image.mode}, {image.size}")
            
            # Flash 모델에 최적화된 이미지 처리
            # 이미지 크기 최적화 (Flash 모델 성능 향상)
            if image.width > 1920 or image.height > 1080:
                image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                print(f"🖼️ 이미지 크기 최적화: {image.width}x{image.height}")
            
            # Get optimized image info for Flash model
            image_info = {
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'width': image.width,
                'height': image.height,
                'optimized_for_flash': True
            }
            
            # Convert to base64 for AI analysis (Flash 모델용)
            import base64
            image_base64 = base64.b64encode(image_content).decode('utf-8')
            
            result = {
                'image_info': image_info,
                'base64_data': image_base64,
                'mime_type': f"image/{image.format.lower() if image.format else 'jpeg'}",
                'flash_optimized': True
            }
            
            print(f"✅ 이미지 처리 완료: Flash 모델 최적화됨")
            return result
            
        except Exception as e:
            print(f"❌ 이미지 처리 실패: {e}")
            raise FileProcessingException(f"이미지 처리 실패: {str(e)}")
    
    def get_file_summary(self, file_content: bytes, filename: str, sheet_name: Optional[str] = None) -> str:
        """Generate optimized file summary for AI context"""
        try:
            print(f"🔍 get_file_summary 호출: filename={filename}, sheet_name={sheet_name}")
            print(f"🔍 파일 확장자 확인: {filename.lower().endswith('.xls')}")
            
            analysis_result = self.analyze_excel_file(file_content, filename)
            print(f"📊 파일 분석 완료: {len(analysis_result.sheets)}개 시트")
            
            summary = f"📊 **파일 분석**: {filename} ({len(file_content) // 1024}KB)\n"
            summary += f"📋 **시트**: {len(analysis_result.sheets)}개 - {', '.join(analysis_result.sheets)}\n\n"
            
            if sheet_name and sheet_name != "all_sheets":
                # 특정 시트 선택된 경우
                print(f"🎯 특정 시트 처리: {sheet_name}")
                summary += f"🎯 **선택된 시트**: '{sheet_name}'\n"
                try:
                    # 엔진 선택 및 파일 읽기 (.xls는 xlrd, .xlsx/.xlsm/.xlsb는 openpyxl)
                    engine = 'xlrd' if filename.lower().endswith('.xls') else 'openpyxl'
                    xls = pd.ExcelFile(io.BytesIO(file_content), engine=engine)
                    print(f"📖 Excel 파일 열기 성공")
                    
                    df = pd.read_excel(xls, sheet_name=sheet_name, engine=engine)
                    print(f"📈 시트 읽기 성공: {len(df)}행 × {len(df.columns)}열")
                    
                    summary += f"📈 **구조**: {len(df)}행 × {len(df.columns)}열\n"
                    summary += f"📝 **열명**: {list(df.columns)}\n"
                    
                    # 데이터 미리보기 (간소화 - 시트 선택 시에는 구조만)
                    summary += f"👀 **구조 정보**:\n"
                    summary += f"- 행 수: {len(df)}행\n"
                    summary += f"- 열 수: {len(df.columns)}열\n"
                    summary += f"- 열명: {list(df.columns)}\n"
                    
                    # 숫자형 열 확인
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    if numeric_cols:
                        summary += f"- 숫자형 열: {numeric_cols}\n"
                    
                    # 간단한 미리보기 (1행만)
                    summary += f"- 샘플 데이터 (1행):\n"
                    summary += df.head(1).to_string(index=False) + "\n"
                    
                    print(f"✅ 시트 요약 생성 완료")
                    
                except Exception as e:
                    print(f"❌ 시트 읽기 실패: {e}")
                    summary += f"⚠️ **오류**: {str(e)}\n"
            
            elif sheet_name == "all_sheets":
                # 모든 시트 요청된 경우
                print(f"📋 모든 시트 처리")
                summary += f"📋 **전체 시트 데이터**\n"
                try:
                    sheet_data = self.extract_sheet_data(file_content, "all_sheets", filename)
                    summary += sheet_data
                    print(f"✅ 모든 시트 요약 생성 완료")
                except Exception as e:
                    print(f"❌ 모든 시트 처리 실패: {e}")
                    summary += f"⚠️ **오류**: {str(e)}\n"
            
            else:
                # 시트가 선택되지 않은 경우
                print(f"💡 시트 미선택 상태")
                summary += f"💡 **시트를 선택해주세요**\n"
                summary += f"위 시트 목록에서 분석할 시트를 선택하시면 자세한 분석을 제공합니다.\n"
            
            print(f"📄 최종 요약 길이: {len(summary)} 문자")
            return summary
            
        except Exception as e:
            print(f"❌ get_file_summary 전체 실패: {e}")
            return f"❌ **파일 분석 오류**: {str(e)}\n"

# Global file service instance
file_service = FileService()
