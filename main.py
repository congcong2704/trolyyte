from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import shutil
import os

app = FastAPI()

# Cho phép CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIza..."))  # thay API key

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
        model = genai.GenerativeModel("gemini-1.5-pro")
        chat = model.start_chat(history=conversations[user])
        response = chat.send_message(msg)
        reply = response.text
        conversations[user].append({"role": "assistant", "content": reply})
    except Exception as e:
        reply = f"Lỗi gọi Gemini API: {e}"

    return {"reply": reply}


@app.post("/api/upload")
async def upload(user: str = Form(...), file: UploadFile = File(...)):
    try:
        # Lưu file tạm
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Xử lý bằng Gemini (nếu là ảnh thì gửi vào vision model)
        if file.content_type.startswith("image/"):
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([
                {"mime_type": file.content_type, "data": open(file_path, "rb").read()},
                "Hãy phân tích hình ảnh này liên quan đến y tế."
            ])
            reply = response.text
        else:
            reply = f"📎 Tệp {file.filename} đã được tải lên thành công."

        os.remove(file_path)
    except Exception as e:
        reply = f"Lỗi xử lý file: {e}"

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
