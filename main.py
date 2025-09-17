from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import json

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
    appt = {
        "user": data["user"],
        "clinic": data["clinic"],
        "date": data["date"],
        "time": data["time"],
    }
    appointments.append(appt)
    return {"message": "Đặt lịch thành công", "appointment": appt}
