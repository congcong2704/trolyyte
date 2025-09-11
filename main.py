from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai

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
genai.configure(api_key="AIzaSyA5wns2Z6xcze03KLL232AJ49gPj_YY5ts")
model = genai.GenerativeModel("gemini-1.5-pro")

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
        # Chuyển đổi lịch sử sang dạng text để gửi cho Gemini
        history_text = ""
        for m in conversations[user]:
            role = "Người dùng" if m["role"] == "user" else "Trợ lý"
            history_text += f"{role}: {m['content']}\n"

        response = model.generate_content(history_text)
        reply = response.text

        conversations[user].append({"role": "assistant", "content": reply})
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
