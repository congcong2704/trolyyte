from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import google.generativeai as genai

app = FastAPI()

# === CORS cho frontend GitHub Pages gọi ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://congcong2704.github.io"],  # domain frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Gemini API Key từ environment ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("⚠️ GEMINI_API_KEY chưa được cấu hình!")

genai.configure(api_key=GEMINI_API_KEY)

# === Tạo model ===
model = genai.GenerativeModel("gemini-1.5-flash")

# === Lưu trữ tạm hội thoại và lịch hẹn ===
conversations = {}
appointments = []

# === API chat ===
@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user = data.get("username")
    msg = data.get("message")

    if not user or not msg:
        return {"reply": "Thiếu thông tin username hoặc message."}

    # Nếu user chưa có hội thoại thì tạo mới
    if user not in conversations:
        conversations[user] = model.start_chat(
            history=[{"role": "system", "parts": "Bạn là trợ lí y tế hữu ích."}]
        )

    try:
        chat = conversations[user]
        response = chat.send_message(msg)   # <--- đúng cách gọi
        reply = response.text
    except Exception as e:
        reply = f"Lỗi gọi Gemini API: {e}"

    return {"reply": reply}

# === API lấy lịch hẹn ===
@app.get("/api/appointments")
async def get_appts(user: str):
    user_appts = [a for a in appointments if a["user"] == user]
    return {"appointments": user_appts}

# === API đặt lịch ===
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
