from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import google.generativeai as genai

app = FastAPI()

# === CORS cho frontend GitHub Pages gọi ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://congcong2704.github.io"],  # bạn có thể đổi thành "https://yourusername.github.io"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Gemini API Key từ environment ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("⚠️ GEMINI_API_KEY chưa được cấu hình!")

genai.configure(api_key=GEMINI_API_KEY)

# === Lưu trữ tạm thời ===
appointments = []
conversations = {}

# === API chat ===
@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user = data.get("username")
    msg = data.get("message")

    if not user or not msg:
        return {"reply": "Thiếu thông tin username hoặc message."}

    if user not in conversations:
        conversations[user] = [
            {"role": "system", "content": "Bạn là trợ lí y tế hữu ích."}
        ]

    conversations[user].append({"role": "user", "content": msg})

    try:
        response = genai.models.generate_message(
            model="gemini-2.5-chat",
            input_messages=conversations[user],
            temperature=0.7,
            max_output_tokens=1024
        )
        reply = response.output_text if hasattr(response, "output_text") else "Không nhận được phản hồi từ Gemini."
        conversations[user].append({"role": "assistant", "content": reply})
    except Exception as e:
        reply = f"Lỗi gọi Gemini API: {e}"
        conversations[user].append({"role": "assistant", "content": reply})

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
