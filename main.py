import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lấy key từ biến môi trường
genai.api_key = os.environ.get("GEMINI_API_KEY")

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
        # Gọi Gemini đúng cú pháp
        response = genai.ChatCompletion.create(
            model="gemini-1.5",
            messages=conversations[user],
            temperature=0.7
        )
        # Lấy reply
        reply = response.choices[0].message["content"]
        conversations[user].append({"role": "assistant", "content": reply})
    except Exception as e:
        reply = f"Lỗi gọi Gemini API: {e}"

    return {"reply": reply}
