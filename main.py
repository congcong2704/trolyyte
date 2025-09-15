from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

# Load biến môi trường từ file .env
load_dotenv()

app = FastAPI()

# Cho phép frontend (index.html) gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lấy API key từ biến môi trường
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

appointments = []
conversations = {}

@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user = data.get("username")
    msg = data.get("message")

    if user not in conversations:
        conversations[user] = [
            {"role": "user", "parts": "Bạn là một trợ lí y tế hữu ích."}
        ]

    conversations[user].append({"role": "user", "parts": msg})

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        chat = model.start_chat(history=conversations[user])
        response = chat.send_message(msg)

        reply = response.text
        conversations[user].append({"role": "model", "parts": reply})
    except Exception as e:
        reply = f"Lỗi gọi Gemini API: {e}"

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
