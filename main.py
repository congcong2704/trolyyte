from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import shutil
import google.generativeai as genai

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
    Nhận file từ frontend: nếu ảnh thì Gemini mô tả, nếu văn bản/PDF thì Gemini đọc nội dung.
    """
    if not user:
        return {"reply": "❌ Thiếu username."}

    # Lưu file
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    reply = ""
    try:
        if file.content_type.startswith("image/"):
            # Ảnh → Gemini Vision mô tả
            with open(file_path, "rb") as img:
                response = model_pro.generate_content(
                    ["Hãy mô tả nội dung của bức ảnh này.", img]
                )
            reply = response.text
        elif file.content_type in ["text/plain", "application/pdf"]:
            # Văn bản/PDF → Gemini đọc file
            with open(file_path, "r", errors="ignore") as f:
                text = f.read()[:4000]  # tránh quá dài
            response = model_pro.generate_content(
                [f"Người dùng {user} đã gửi văn bản sau, hãy tóm tắt và giải thích:", text]
            )
            reply = response.text
        else:
            # File khác → chỉ xác nhận
            reply = f"📂 Bạn đã gửi tệp: {file.filename}"
    except Exception as e:
        reply = f"❌ Lỗi khi xử lý file {file.filename}: {e}"

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
