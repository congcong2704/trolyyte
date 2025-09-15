from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os, json, requests
from dotenv import load_dotenv
import google.generativeai as genai
import tempfile
from pathlib import Path
import PyPDF2
import docx

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

appointments=[]
conversations={}
GOOGLE_SHEET_URL = "https://script.google.com/macros/s/AKfycbzWE79uuLGZMV9PiyruPfj4tGzJH5ttiZKg-EYztZgADslNojf9Bh5N4uHhtTljksDB/exec"

@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user = data.get("username")
    msg = data.get("message")

    if user not in conversations:
        conversations[user] = [{"role":"system","parts":"Bạn là trợ lí y tế hữu ích."}]
    conversations[user].append({"role":"user","parts":msg})

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        chat = model.start_chat(history=conversations[user])
        response = chat.send_message(msg)
        reply=response.text
        conversations[user].append({"role":"model","parts":reply})
    except Exception as e:
        print("Gemini error:",e)
        reply="Hệ thống gặp sự cố, thử lại sau."
    return {"reply":reply}

@app.post("/api/voice")
async def voice_chat(username: str = Form(...), file: UploadFile = File(...)):
    try:
        tmp_path = Path(tempfile.gettempdir()) / file.filename
        with open(tmp_path,'wb') as f: f.write(await file.read())
        text = genai.audio.transcribe(model="whisper-1", file=str(tmp_path))['text']

        if username not in conversations:
            conversations[username] = [{"role":"system","parts":"Bạn là trợ lí y tế hữu ích."}]
        conversations[username].append({"role":"user","parts":text})
        model = genai.GenerativeModel("gemini-1.5-flash")
        chat = model.start_chat(history=conversations[username])
        response = chat.send_message(text)
        reply=response.text
        conversations[username].append({"role":"model","parts":reply})
        return {"reply":reply}
    except Exception as e:
        print(e)
        return {"reply":"Lỗi khi xử lý giọng nói."}

@app.post("/api/message-with-file")
async def message_with_file(username: str = Form(...), message: str = Form(''), file: UploadFile = File(...)):
    parts = [message] if message else []
    try:
        ext = file.filename.split('.')[-1].lower()
        tmp_path = Path(tempfile.gettempdir()) / file.filename
        with open(tmp_path,'wb') as f: f.write(await file.read())

        if ext in ['pdf','txt']:
            text=''
            if ext=='pdf':
                reader = PyPDF2.PdfReader(str(tmp_path))
                for page in reader.pages: text+=page.extract_text()+'\n'
            else:
                text=tmp_path.read_text(encoding='utf-8')
            parts.append(text)
        elif ext in ['doc','docx']:
            doc = docx.Document(str(tmp_path))
            text='\n'.join([p.text for p in doc.paragraphs])
            parts.append(text)
        elif ext in ['jpg','jpeg','png']:
            parts.append(genai.types.Part.from_uri(str(tmp_path),mime_type=f'image/{ext}'))
    except Exception as e:
        print(e)
        parts.append(f"[Không đọc được file: {file.filename}]")

    if username not in conversations:
        conversations[username] = [{"role":"system","parts":"Bạn là trợ lí y tế hữu ích."}]
    conversations[username].append({"role":"user","parts":parts})

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        chat = model.start_chat(history=conversations[username])
        response = chat.send_message(parts)
        reply=response.text
        conversations[username].append({"role":"model","parts":reply})
        return {"reply":reply}
    except Exception as e:
        print(e)
        return {"reply":"Lỗi khi xử lý file."}

@app.get("/api/appointments")
async def get_appts(user: str):
    user_appts=[a for a in appointments if a['user']==user]
    return {'appointments':user_appts}

@app.post("/api/book")
async def book(req: Request):
    data = await req.json()
    appt = {"user":data['user'],"clinic":data['clinic'],"date":data['date'],"time":data['time']}
    appointments.append(appt)

    # Gửi lên Google Sheets
    try:
        requests.post(GOOGLE_SHEET_URL, json=appt, timeout=5)
    except Exception as e:
        print("Lỗi gửi Google Sheets:",e)

    return {'message':'Đặt lịch thành công','appointment':appt}
