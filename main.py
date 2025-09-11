from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import google.generativeai as genai

app = FastAPI()

# ====== CORS để frontend gọi API ======
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== Cấu hình Gemini ======
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("❌ GEMINI_API_KEY chưa được cấu hình trong biến môi trường!")

genai.configure(api_key=api_key)

model_pro = genai.GenerativeModel("gemini-1.5-pro")
model_flash = genai.GenerativeModel("gemini-1.5-flash")

appointments = []
conversations = {}

# ====== API chat ======
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

    # Gom lịch sử hội thoại thành text
    history_text = ""
    for m in conversations[user]:
        role = "Người dùng" if m["role"] == "user" else "Trợ lý"
        history_text += f"{role}: {m['content']}\n"

    try:
        response = model_pro.generate_content(history_text)
        reply = response.text
    except Exception as e:
        if "429" in str(e):  # quota exceeded
            try:
                response = model_flash.generate_content(history_text)
                reply = response.text
            except Exception as e2:
                reply = f"Lỗi gọi Gemini Flash API: {e2}"
        else:
            reply = f"Lỗi gọi Gemini Pro API: {e}"

    conversations[user].append({"role": "assistant", "content": reply})
    return {"reply": reply}

# ====== API lấy lịch hẹn ======
@app.get("/api/appointments")
async def get_appts(user: str):
    user_appts = [a for a in appointments if a["user"] == user]
    return {"appointments": user_appts}

# ====== API đặt lịch ======
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

# ====== API upload ảnh/tệp ======
@app.post("/api/upload")
async def upload(user: str = Form(...), file: UploadFile = File(...)):
    """
    Nhận file (ảnh/pdf/txt...) từ frontend, gửi lên Gemini để phân tích.
    """
    try:
        contents = await file.read()
        path = f"/tmp/{file.filename}"
        with open(path, "wb") as f:
            f.write(contents)

        # Gọi Gemini với file (chỉ demo, bạn có thể mở rộng thêm)
        response = model_pro.generate_content(
            [f"Người dùng {user} gửi tệp {file.filename}, hãy mô tả nội dung:", path]
        )
        reply = response.text
    except Exception as e:
        reply = f"Lỗi khi xử lý file: {e}"

    return {"reply": reply}
