from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import google.generativeai as genai

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lấy key từ biến môi trường
GEN_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEN_API_KEY:
    raise ValueError("Bạn chưa thiết lập biến môi trường GEMINI_API_KEY trên Render!")

genai.configure(api_key=GEN_API_KEY)

# Lưu trữ tạm thời
appointments = []
conversations = {}

# --- API chat ---
@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user = data.get("username")
    msg = data.get("message")

    if not user or not msg:
        return {"reply": "Thiếu thông tin username hoặc message."}

    if user not in conversations:
        conversations[user] = [
            {"author": "system", "content": "Bạn là một trợ lí y tế hữu ích."}
        ]

    conversations[user].append({"author": "user", "content": msg})

    try:
        response = genai.chat.create(
            model="models/chat-bison-001",
            messages=conversations[user],
            temperature=0.7,
            max_output_tokens=1024
        )

        # Lấy nội dung trả về an toàn
        if response and hasattr(response, "last") and response.last:
            reply = response.last.get("content", [{}])[0].get("text", "...")
        else:
            reply = "Không nhận được phản hồi từ Gemini."

        conversations[user].append({"author": "assistant", "content": reply})

    except Exception as e:
        reply = f"Lỗi gọi Gemini API: {e}"

    return {"reply": reply}

# --- API lấy lịch hẹn ---
@app.get("/api/appointments")
async def get_appts(user: str):
    user_appts = [a for a in appointments if a["user"] == user]
    return {"appointments": user_appts}

# --- API đặt lịch ---
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

# --- Start Command trên Render ---
# Trên Render, bạn sẽ điền: uvicorn main:app --host 0.0.0.0 --port $PORT
