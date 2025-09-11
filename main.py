from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import google.generativeai as genai
import shutil
from pathlib import Path

app = FastAPI()

# Cho phép frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Cấu hình Gemini ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("❌ GEMINI_API_KEY chưa được cấu hình trong biến môi trường!")

genai.configure(api_key=api_key)

# Models
model_pro = genai.GenerativeModel("gemini-1.5-pro")
model_flash = genai.GenerativeModel("gemini-1.5-flash")

appointments = []
conversations = {}

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user = data.get("username")
    msg = data.get("message")

    if not user:
        return {"reply": "❌ Thiếu username."}

    if user not in conversations:
        conversations[user] = [
            {"role": "system", "content": "Bạn là một trợ lí y tế hữu ích."}
        ]

    conversations[user].append({"role": "user", "content": msg})

    # Gom lịch sử hội thoại thành text
    history_text = ""
    for m in conversations[user]:
        role = "Người dùng" if m["role"] == "user" else "Trợ lý"
        history_text += f"{role}: {m['content']}\n"

    try:
        # Gọi gemini-1.5-pro trước
        response = model_pro.generate_content(history_text)
        reply = response.text
    except Exception as e:
        if "429" in str(e):  # hết quota → fallback sang flash
            try:
                response = model_flash.generate_content(history_text)
                reply = response.text
            except Exception as e2:
                reply = f"Lỗi gọi Gemini Flash API: {e2}"
        else:
            reply = f"Lỗi gọi Gemini Pro API: {e}"

    conversations[user].append({"role": "assistant", "content": reply})
    return {"reply": reply}


@app.post("/api/upload")
async def upload_file(user: str = Form(...), file: UploadFile = File(...)):
    """
    API nhận file/ảnh từ frontend.
    """
    if not user:
        return {"reply": "❌ Thiếu username."}

    # Lưu file vào thư mục uploads
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Tạo prompt cho Gemini
    try:
        response = model_pro.generate_content(
            [f"Người dùng {user} đã gửi một file: {file.filename}. Hãy phân tích nội dung hoặc đưa ra phản hồi phù hợp."]
        )
        reply = response.text
    except Exception as e:
        reply = f"Đã nhận file {file.filename}, nhưng lỗi khi gọi Gemini: {e}"

    # Lưu hội thoại
    if user not in conversations:
        conversations[user] = [
            {"role": "system", "content": "Bạn là một trợ lí y tế hữu ích."}
        ]
    conversations[user].append({"role": "user", "content": f"Gửi file {file.filename}"})
    conversations[user].append({"role": "assistant", "content": reply})

    return {"reply": reply}


@app.get("/api/appointments")
async def get_appts(user: str):
    user_appts = [a for a in appointments if a["user"] == user]
    return {"appointments": user_appts}


@app.post("/api/book")
async def book(req: Request):
    data = await req.json()
    appt = {
        "user": data["user"],
        "clinic": data["clinic"],
        "date": data["date"],
        "time": data["time"],
    }
    appointments.append(appt)
    return {"message": "Đặt lịch thành công", "appointment": appt}
