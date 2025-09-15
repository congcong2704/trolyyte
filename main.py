from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
import google.generativeai as genai
from pathlib import Path
import shutil

app = FastAPI()

# Cho phép frontend (index.html) gọi API
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

# Bộ nhớ tạm (có thể thay bằng DB sau)
appointments = []
conversations = {}

# Tạo thư mục lưu file upload
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ---------------- CHAT CHÍNH ----------------
@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user = data.get("username", "guest")
    msg = data.get("message")

    if not msg:
        return {"reply": "⚠️ Thiếu nội dung tin nhắn."}

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


# ---------------- LỊCH HẸN ----------------
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


# ---------------- MENU MỞ RỘNG ----------------
@app.post("/api/file")
async def file_action(file: UploadFile = File(...)):
    """Upload file thật (ảnh, pdf, docx, txt, ...)"""
    file_path = UPLOAD_DIR / file.filename

    # Lưu file vào thư mục uploads/
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size_kb = round(file_path.stat().st_size / 1024, 2)

    return {
        "reply": f"📎 Đã upload file **{file.filename}** ({size_kb} KB).",
        "filename": file.filename,
        "size_kb": size_kb,
        "path": str(file_path),
    }


@app.post("/api/study")
async def study_action(req: Request):
    return {"reply": "📖 Đây là chế độ *Học tập*. Bạn muốn học về chủ đề nào?"}


@app.post("/api/image")
async def image_action(req: Request):
    return {"reply": "🎨 Tính năng *Tạo hình ảnh* sẽ được bổ sung sau."}


@app.post("/api/think")
async def think_action(req: Request):
    return {"reply": "💡 Tôi sẽ *suy nghĩ chi tiết hơn* để đưa ra câu trả lời tốt hơn."}


@app.post("/api/research")
async def research_action(req: Request):
    return {"reply": "🔍 Tính năng *Nghiên cứu sâu* đang được phát triển."}
