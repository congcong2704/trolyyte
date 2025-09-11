from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import os, tempfile
import google.generativeai as genai

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

api_key=os.getenv("GEMINI_API_KEY")
if not api_key: raise RuntimeError("❌ GEMINI_API_KEY chưa được cấu hình!")
genai.configure(api_key=api_key)

model_pro=genai.GenerativeModel("gemini-1.5-pro")
model_flash=genai.GenerativeModel("gemini-1.5-flash")

appointments=[]; conversations={}

@app.post("/api/message")
async def message(username: str=Form(...), message: str=Form(""), files: list[UploadFile]=[]):
    if username not in conversations:
        conversations[username]=[{"role":"system","content":"Bạn là trợ lí y tế hữu ích"}]
    if message: conversations[username].append({"role":"user","content":message})

    parts=[]
    if message: parts.append(message)
    for f in files:
        tmp=tempfile.NamedTemporaryFile(delete=False); tmp.write(await f.read()); tmp.close()
        uploaded=genai.upload_file(tmp.name); parts.append(uploaded)

    history_text="\n".join([("Người dùng" if m["role"]=="user" else "Trợ lý")+": "+m["content"] for m in conversations[username]])
    try:
        response=model_pro.generate_content([history_text]+parts); reply=response.text
    except Exception:
        response=model_flash.generate_content([history_text]+parts); reply=response.text
    conversations[username].append({"role":"assistant","content":reply})
    return {"reply":reply}

@app.post("/api/upload")
async def upload(username: str=Form(...), file: UploadFile=None):
    tmp=tempfile.NamedTemporaryFile(delete=False); tmp.write(await file.read()); tmp.close()
    uploaded=genai.upload_file(tmp.name)
    response=model_pro.generate_content([uploaded,"Hãy phiên âm hoặc tóm tắt nội dung giọng nói này."])
    return {"reply":response.text}

@app.get("/api/appointments")
async def get_appts(user:str):
    return {"appointments":[a for a in appointments if a["user"]==user]}

@app.post("/api/book")
async def book(req:Request):
    data=await req.json()
    appt={"user":data["user"],"clinic":data["clinic"],"date":data["date"],"time":data["time"]}
    appointments.append(appt)
    return {"message":"Đặt lịch thành công","appointment":appt}
