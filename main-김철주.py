# --- 1. 필요한 도구들 가져오기 ---
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
# from dotenv import load_dotenv  # 배포 환경에서는 이 줄을 주석 처리하는 것이 좋습니다.
import os
import shutil
import pandas as pd
from openai import OpenAI
import google.generativeai as genai
from PIL import Image
import io
import uuid

# --- 2. 초기 설정 ---
# load_dotenv()  # 배포 환경에서는 이 줄을 주석 처리하는 것이 좋습니다.
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# ★★★★★★★★★★★★★★★★★★★ 디버깅 코드 시작 ★★★★★★★★★★★★★★★★★★★
# Render 서버가 환경 변수를 제대로 읽었는지 확인하기 위해 값을 변수에 저장합니다.
gemini_api_key_from_env = os.getenv("GEMINI_API_KEY")
openai_api_key_from_env = os.getenv("OPENAI_API_KEY")

# 서버 로그에 상태를 출력합니다. 이 로그를 Render에서 확인해야 합니다.
print("--- STARTING SERVER & CHECKING ENVIRONMENT VARIABLES ---")
if gemini_api_key_from_env:
    # 키 전체를 로그에 노출하지 않도록 앞 5자리만 출력합니다.
    print(f"[SUCCESS] Gemini API Key loaded. Starts with: {gemini_api_key_from_env[:5]}")
else:
    print("[ERROR] FAILED to load Gemini API Key. Value is None.")

if openai_api_key_from_env:
    print(f"[SUCCESS] OpenAI API Key loaded. Starts with: {openai_api_key_from_env[:5]}")
else:
    print("[ERROR] FAILED to load OpenAI API Key. Value is None.")
print("---------------------------------------------------------")
# ★★★★★★★★★★★★★★★★★★★ 디버깅 코드 끝 ★★★★★★★★★★★★★★★★★★★★

# OpenAI: 정밀한 코드/수식/논리 담당
# 이제 os.getenv() 대신 위에서 확인한 변수를 사용합니다.
openai_client = OpenAI(api_key=openai_api_key_from_env)
OPENAI_MODEL = "gpt-4-turbo"

# Google Gemini: 역할에 따라 다른 모델 사용
# 이제 os.getenv() 대신 위에서 확인한 변수를 사용합니다.
genai.configure(api_key=gemini_api_key_from_env)
gemini_pro_model = genai.GenerativeModel('gemini-1.5-pro-latest') 
gemini_flash_model = genai.GenerativeModel('gemini-1.5-flash-latest')

templates = Jinja2Templates(directory="templates")
chat_sessions = {}

# --- 3. AI 페르소나 및 프롬프트 정의 ---
# (코드 길이상 생략) 실제 파일에는 PERSONA_PROMPT와 DEBUGGING_PERSONA_PROMPT 내용이 있어야 합니다.
PERSONA_PROMPT = """..."""
DEBUGGING_PERSONA_PROMPT = """..."""

# --- 4. 웹페이지 보여주기 ---
@app.get("/", response_class=HTMLResponse)
async def serve_home_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- 5. AI에게 질문/피드백하는 핵심 기능 ---
@app.post("/ask")
async def handle_ask_request(
    question: str = Form(""),
    file: UploadFile = File(None),
    image: UploadFile = File(None),
    session_id: str = Form(None),
    is_feedback: bool = Form(False)
):
    # (이하 로직은 기존과 동일하므로 생략하지 않고 그대로 유지합니다)
    # 5.1. 세션 관리
    if not session_id or session_id not in chat_sessions:
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = []

    # 5.2. 입력 데이터 분석 및 텍스트화
    final_input_text = f"사용자 질문/피드백: {question}\n\n"
    
    if file and file.filename:
        pass 

    if image and image.filename:
        try:
            image_content = await image.read()
            img = Image.open(io.BytesIO(image_content))
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()
            
            response = gemini_flash_model.generate_content(
                ["이 이미지에 있는 모든 텍스트와 상황을 설명해줘.", {"mime_type": "image/png", "data": img_bytes}]
            )
            image_description = response.text
            final_input_text += f"[사용자 첨부 이미지 분석 결과 📸]\n{image_description}\n------------------\n"
        except Exception as e:
            print(f"이미지 텍스트 변환 오류: {e}")
            final_input_text += "[사용자 첨부 이미지 분석 중 오류 발생]\n"
    
    ai_answer = ""
    try:
        if is_feedback:
            previous_answer = next((msg['content'] for msg in reversed(chat_sessions.get(session_id, [])) if msg['role'] == 'assistant'), "이전 답변을 찾을 수 없습니다.")
            debugging_prompt = f"{DEBUGGING_PERSONA_PROMPT}\n\n--- 이전 해결책 ---\n{previous_answer}\n\n--- 사용자 피드백 ---\n{final_input_text}"
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL, messages=[{"role": "user", "content": debugging_prompt}]
            )
            ai_answer = response.choices[0].message.content
        else:
            is_code_request = any(k in question.lower() for k in ["vba", "매크로", "스크립트", "코드"])
            is_complex_request = any(k in question.lower() for k in ["복잡한", "배열 수식", "수식 조합", "분석"])
            is_file_attached = file is not None

            if is_file_attached and (is_code_request or is_complex_request):
                context_prompt = f"다음은 사용자의 질문과 업로드한 파일의 정보입니다. 이를 바탕으로, 코드를 작성하거나 복잡한 분석을 하기 위해 필요한 핵심 정보(시트, 컬럼, 데이터 특징 등)만 간결하게 요약해주세요.\n\n{final_input_text}"
                context_response = gemini_pro_model.generate_content(context_prompt)
                extracted_context = context_response.text
                final_prompt_for_openai = f"{PERSONA_PROMPT}\n\n--- AI 요약 정보 ---\n{extracted_context}\n\n--- 원본 질문 ---\n{question}\n\n위 정보를 바탕으로 최고의 답변을 생성해줘."
                response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL, messages=[{"role": "user", "content": final_prompt_for_openai}]
                )
                ai_answer = response.choices[0].message.content + "\n\n---\n*💡 Gemini Pro의 분석과 GPT-4의 정밀함으로 답변을 만들었어요!*"
            elif is_code_request or is_complex_request:
                final_prompt = f"{PERSONA_PROMPT}\n\n{final_input_text}"
                response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL, messages=[{"role": "user", "content": final_prompt}]
                )
                ai_answer = response.choices[0].message.content
            else:
                final_prompt = f"{PERSONA_PROMPT}\n\n{final_input_text}"
                response = gemini_pro_model.generate_content(final_prompt)
                ai_answer = response.text

        chat_sessions.setdefault(session_id, []).append({"role": "assistant", "content": ai_answer})
        return {"answer": ai_answer, "session_id": session_id}

    except Exception as e:
        # 에러 로그를 더 자세하게 출력합니다.
        print(f"!!! API 호출 중 심각한 오류 발생: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail="으악! AI 전문가와 연결이 잠시 끊겼어요. 😭")