from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import google.generativeai as genai

app = FastAPI()

# CORS để cho frontend gọi API
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

# Bộ nhớ tạm
appointments = []
conversations = {}

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/api/message")
async def message(req: Request):
    """Nhận tin nhắn từ frontend, gọi Gemini để trả lời"""
    data = await req.json()
    user = data.get("username")
    msg = data.get("message")

    if not user or not msg:
        return {"reply": "⚠️ Thiếu thông tin username hoặc message."}

    if user not in conversations:
        conversations[user] = [
            {"role": "system", "content": "Bạn là một trợ lí y tế hữu ích."}
        ]

    conversations[user].append({"role": "user", "content": msg})

    history_text = ""
    for m in conversations[user]:
        role = "Người dùng" if m["role"] == "user" else "Trợ lý"
        history_text += f"{role}: {m['content']}\n"

    try:
        response = model_pro.generate_content(history_text)
        reply = response.text
    except Exception as e:
        if "429" in str(e):  # hết quota → fallback
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
    """Nhận file từ người dùng và lưu vào thư mục uploads/"""
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        reply = f"📎 File '{file.filename}' đã được tải lên thành công."

        # Nếu là ảnh → gợi ý phân tích
        if file.content_type.startswith("image/"):
            reply += " Đây là ảnh, bạn có muốn tôi phân tích nội dung ảnh không?"

        # Nếu là text → tóm tắt nội dung
        elif file.content_type.startswith("text/"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(500)
            ai_resp = model_flash.generate_content(
                f"Đây là nội dung file:\n{content}\n\nHãy tóm tắt ngắn gọn cho bệnh nhân."
            )
            reply += "\n📝 Tóm tắt: " + ai_resp.text

        return {"reply": reply}
    except Exception as e:
        return {"reply": f"❌ Lỗi upload file: {e}"}


@app.get("/api/appointments")
async def get_appts(user: str):
    """Trả về danh sách lịch hẹn của 1 user"""
    user_appts = [a for a in appointments if a["user"] == user]
    return {"appointments": user_appts}


@app.post("/api/book")
async def book(req: Request):
    """Đặt lịch hẹn mới"""
    data = await req.json()
    appt = {
        "user": data["user"],
        "clinic": data["clinic"],
        "date": data["date"],
        "time": data["time"],
    }
    appointments.append(appt)
    return {"message": "Đặt lịch thành công", "appointment": appt}
