# main.py
# Entry point for Excelly AI Assistant

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 자동 재시작 비활성화
        log_level="info"
    )
