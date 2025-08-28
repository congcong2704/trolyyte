from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import json
import datetime
import re

app = FastAPI()

# Cho phép frontend (index.html) gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key="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")

appointments = []
conversations = {}

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

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=conversations[user],
            max_completion_tokens=2048
        )
        reply = response.choices[0].message.content
        conversations[user].append({"role": "assistant", "content": reply})
    except Exception as e:
        reply = f"Lỗi gọi Groq API: {e}"

    return {"reply": reply}


@app.get("/api/appointments")
async def get_appts(user: str):
    user_appts = [a for a in appointments if a["user"] == user]
    return {"appointments": user_appts}


@app.post("/api/book")
async def book(req: Request):
    data = await req.json()
    user = data.get("user")
    clinic = data.get("clinic")
    date_str = data.get("date")
    time_str = data.get("time")

    # validate date (YYYY-MM-DD và phải là ngày hợp lệ)
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Ngày không hợp lệ. Dùng định dạng YYYY-MM-DD và ngày thực tế."
        )

    # validate time HH:MM (00:00 - 23:59)
    if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", time_str or ""):
        raise HTTPException(
            status_code=400,
            detail="Giờ không hợp lệ. Dùng định dạng HH:MM (00:00-23:59)."
        )

    appt = {
        "user": user,
        "clinic": clinic,
        "date": str(date_obj),  # lưu lại theo chuẩn YYYY-MM-DD
        "time": time_str,
    }
    appointments.append(appt)

    return {"message": "Đặt lịch thành công", "appointment": appt}
