# app/models/excel.py
# Excel-related data models

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ExcelSheet(BaseModel):
    """Excel sheet information"""
    name: str = Field(..., description="Sheet name")
    row_count: int = Field(..., description="Number of rows")
    column_count: int = Field(..., description="Number of columns")
    preview_data: Optional[List[List[str]]] = Field(None, description="Preview of sheet data")

class ExcelFile(BaseModel):
    """Excel file information"""
    filename: str = Field(..., description="File name")
    file_size: int = Field(..., description="File size in bytes")
    sheets: List[ExcelSheet] = Field(default_factory=list, description="List of sheets")
    file_type: str = Field(..., description="File type (xlsx, xls, csv)")
    
class FileAnalysisResult(BaseModel):
    """Result of file analysis"""
    sheets: List[str] = Field(..., description="List of sheet names")
    file_info: Optional[ExcelFile] = Field(None, description="Detailed file information")
    analysis_summary: Optional[str] = Field(None, description="Analysis summary")

class SheetSelection(BaseModel):
    """Sheet selection request"""
    session_id: str = Field(..., description="Session identifier")
    selected_sheet: str = Field(..., description="Selected sheet name or 'all_sheets'")

class VBARequest(BaseModel):
    """VBA code generation request"""
    task_description: str = Field(..., description="Task description")
    target_sheet: Optional[str] = Field(None, description="Target sheet name")
    target_range: Optional[str] = Field(None, description="Target range (e.g., A1:B10)")
    requirements: Optional[List[str]] = Field(default_factory=list, description="Specific requirements")

class FormulaRequest(BaseModel):
    """Excel formula request"""
    task_description: str = Field(..., description="Task description")
    target_cell: Optional[str] = Field(None, description="Target cell")
    data_range: Optional[str] = Field(None, description="Data range")
    formula_type: Optional[str] = Field(None, description="Type of formula needed")
