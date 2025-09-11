from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import google.generativeai as genai

app = FastAPI()

# CORS cho frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("❌ GEMINI_API_KEY chưa cấu hình!")
genai.configure(api_key=api_key)

model_text = genai.GenerativeModel("gemini-1.5-pro")
model_multimodal = genai.GenerativeModel("gemini-1.5-flash")

appointments = []
conversations = {}

@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user = data.get("username")
    msg = data.get("message")
    if user not in conversations:
        conversations[user] = []
    conversations[user].append({"role": "user", "content": msg})
    history = "\n".join([f"{m['role']}: {m['content']}" for m in conversations[user]])
    response = model_text.generate_content(history)
    reply = response.text
    conversations[user].append({"role": "assistant", "content": reply})
    return {"reply": reply}

@app.post("/api/upload")
async def upload(username: str = Form(...), file: UploadFile = File(...)):
    content = await file.read()
    # Tạo tài nguyên hình ảnh/file cho Gemini
    try:
        response = model_multimodal.generate_content([
            f"Người dùng {username} đã gửi file {file.filename}, hãy phân tích nội dung:",
            {"mime_type": file.content_type, "data": content}
        ])
        reply = response.text
    except Exception as e:
        reply = f"Lỗi xử lý file: {e}"
    return {"reply": reply}

@app.get("/api/appointments")
async def get_appts(user: str):
    return {"appointments": [a for a in appointments if a["user"] == user]}

@app.post("/api/book")
async def book(req: Request):
    data = await req.json()
    appt = {
        "user": data["user"], "clinic": data["clinic"],
        "date": data["date"], "time": data["time"],
    }
    appointments.append(appt)
    return {"message": "Đặt lịch thành công", "appointment": appt}
