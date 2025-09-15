from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os, shutil
import google.generativeai as genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

# --- Gemini ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("❌ Chưa cấu hình GEMINI_API_KEY")
genai.configure(api_key=api_key)

model_pro = genai.GenerativeModel("gemini-1.5-pro")
model_flash = genai.GenerativeModel("gemini-1.5-flash")

appointments = []
conversations = {}
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Chat thường ---
@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user, msg = data.get("username"), data.get("message")
    if not user or not msg:
        return {"reply": "⚠️ Thiếu username hoặc message."}

    if user not in conversations:
        conversations[user] = [{"role":"system","content":"Bạn là một trợ lí y tế hữu ích."}]
    conversations[user].append({"role":"user","content":msg})

    history_text = "\n".join(
        [("Người dùng" if m["role"]=="user" else "Trợ lý")+": "+m["content"] for m in conversations[user]]
    )
    try:
        response = model_pro.generate_content(history_text)
        reply = response.text
    except Exception as e:
        try:
            response = model_flash.generate_content(history_text)
            reply = response.text
        except Exception as e2:
            reply = f"❌ Lỗi Gemini: {e2}"
    conversations[user].append({"role":"assistant","content":reply})
    return {"reply": reply}

# --- Chat kèm file ---
@app.post("/api/message_with_file")
async def message_with_file(user: str = Form(...), message: str = Form(""), file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path,"wb") as f: shutil.copyfileobj(file.file, f)

    summary = ""
    if file.content_type.startswith("text/"):
        with open(file_path,"r",encoding="utf-8",errors="ignore") as f:
            content = f.read(500)
        resp = model_flash.generate_content(f"Hãy tóm tắt ngắn gọn:\n{content}")
        summary = "\n📝 Tóm tắt file: " + resp.text
    elif file.content_type.startswith("image/"):
        summary = "\n📷 Đây là ảnh. Bạn có muốn tôi phân tích thêm không?"

    # gom câu hỏi + file
    full_msg = f"{message}\n(Đính kèm: {file.filename})"
    if user not in conversations:
        conversations[user] = [{"role":"system","content":"Bạn là một trợ lí y tế hữu ích."}]
    conversations[user].append({"role":"user","content":full_msg})

    history_text = "\n".join(
        [("Người dùng" if m["role"]=="user" else "Trợ lý")+": "+m["content"] for m in conversations[user]]
    )
    try:
        response = model_pro.generate_content(history_text)
        reply = response.text
    except:
        response = model_flash.generate_content(history_text)
        reply = response.text
    conversations[user].append({"role":"assistant","content":reply})
    return {"reply": reply + summary}

# --- Appointment ---
@app.get("/api/appointments")
async def get_appts(user: str):
    return {"appointments": [a for a in appointments if a["user"] == user]}

@app.post("/api/book")
async def book(req: Request):
    data = await req.json()
    appt = {
        "user":
