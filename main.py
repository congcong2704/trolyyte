from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
from google import genai  # Thư viện mới google-genai

app = FastAPI()

# CORS để frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Gemini API =====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("⚠️ Chưa cấu hình GEMINI_API_KEY trong environment variables!")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# --- Lưu trữ tạm thời ---
appointments = []
conversations = {}

# ===== API chat =====
@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user = data.get("username")
    msg = data.get("message")

    if not user or not msg:
        return {"reply": "Thiếu thông tin username hoặc message."}

    # Khởi tạo conversation nếu chưa có
    if user not in conversations:
        conversations[user] = [
            {"role": "system", "content": "Bạn là một trợ lí y tế hữu ích."}
        ]

    conversations[user].append({"role": "user", "content": msg})

    try:
        # Gửi message tới Gemini AI
        response = client.models.generate_message(
            model="gemini-2.5-chat",
            input_messages=conversations[user],
            temperature=0.7,
            max_output_tokens=1024
        )

        # Lấy nội dung trả về
        reply = response.output_text if hasattr(response, "output_text") else "Không nhận được phản hồi từ Gemini."

        # Lưu lại vào conversation
        conversations[user].append({"role": "assistant", "content": reply})

    except Exception as e:
        reply = f"Lỗi gọi Gemini API: {e}"

    return {"reply": reply}

# ===== API lấy lịch hẹn =====
@app.get("/api/appointments")
async def get_appts(user: str):
    user_appts = [a for a in appointments if a["user"] == user]
    return {"appointments": user_appts}

# ===== API đặt lịch =====
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

# --- Lưu ý Start Command trên Render ---
# uvicorn main:app --host 0.0.0.0 --port $PORT
