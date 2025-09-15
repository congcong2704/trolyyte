from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import google.generativeai as genai
from pathlib import Path
from PIL import Image
import uuid
import shutil

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Cấu hình Gemini ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("❌ GEMINI_API_KEY chưa được cấu hình trong biến môi trường!")

genai.configure(api_key=api_key)

# Models
model_pro = genai.GenerativeModel("gemini-1.5-pro")
model_flash = genai.GenerativeModel("gemini-1.5-flash")

appointments = []
conversations = {}

# Upload folder
UPLOAD_DIR = Path('./uploads')
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
        # Gọi gemini-1.5-pro trước
        response = model_pro.generate_content(history_text)
        # Mô hình có thể trả nhiều trường - dùng response.text nếu có
        reply = getattr(response, "text", None) or str(response)
    except Exception as e:
        if "429" in str(e):
            try:
                response = model_flash.generate_content(history_text)
                reply = getattr(response, "text", None) or str(response)
            except Exception as e2:
                reply = f"Lỗi gọi Gemini Flash API: {e2}"
        else:
            reply = f"Lỗi gọi Gemini Pro API: {e}"

    conversations[user].append({"role": "assistant", "content": reply})
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


# ===== Image upload & (placeholder) image understanding =====
@app.post("/api/image")
async def upload_image(user: str = Form(...), image: UploadFile = File(...)):
    """
    Lưu ảnh và trả về mô tả cơ bản.
    NOTE:
      - Đây là implementation "an toàn" (server lưu file + lấy metadata).
      - Để phân tích nội dung ảnh (object detection, captioning...) bạn cần gọi dịch vụ Vision (Gemini Vision, Google Vision, AWS Rekognition, custom model...). Mình để chỗ đánh dấu để bạn cắm vào.
    """
    # generate filename
    ext = Path(image.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / filename

    with dest.open("wb") as f:
        shutil.copyfileobj(image.file, f)

    # get basic metadata
    try:
        with Image.open(dest) as im:
            fmt = im.format
            w, h = im.size
    except Exception as e:
        fmt = None
        w = h = None

    # build a basic description using available metadata
    description = f"Đã nhận ảnh từ {user}. Tên file: {filename}."
    if fmt and w and h:
        description += f" Định dạng: {fmt}. Kích thước: {w}x{h}."

    # ---- PLACEHOLDER: gọi service Vision / Gemini Vision ở đây ----
    # Ví dụ: nếu bạn có API cho Gemini Vision, bạn có thể upload file hoặc base64
    # và gọi API vision để nhận caption/labels. Do API vision khác nhau, mình để chỗ này để bạn tích hợp.
    #
    # Nếu muốn mình tích hợp sẵn với 1 dịch vụ cụ thể (ví dụ OpenAI Vision, Google Vision, AssemblyAI, v.v.),
    # gửi cho mình key và tài liệu API (hoặc nói tên service) — mình sẽ giúp chỉnh tiếp.
    # ----------------------------------------------------------------

    return JSONResponse({"description": description, "filename": filename, "path": str(dest)})


# ===== Transcribe endpoint (server-side) - placeholder =====
@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """
    Endpoint này là placeholder nếu bạn muốn dùng server-side STT
    (ví dụ: Whisper, Google Speech-to-Text, AssemblyAI, ...)

    Hiện tại mình chưa cắm dịch vụ STT ở server (vì mỗi người có provider khác).
    Nếu bạn muốn, mình sẽ tích hợp Whisper / AssemblyAI / GCP STT — chỉ cần cho biết provider & API key.
    """
    return JSONResponse({"error": "Server-side transcription chưa được cấu hình. Vui lòng tích hợp dịch vụ STT và update endpoint /api/transcribe."}, status_code=501)
