from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import json
import datetime
import re
import unicodedata   # << thêm thư viện này

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

# -----------------------------
# Hàm bỏ dấu tiếng Việt
# -----------------------------
def remove_accents(text: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

@app.post("/api/message")
async def message(req: Request):
    data = await req.json()
    user = data.get("username")
    msg = data.get("message")

    # Chuẩn hóa input (bỏ dấu + lowercase)
    normalized_msg = remove_accents(msg).lower()

    if user not in conversations:
        conversations[user] = [
            {"role": "system", "content": "Bạn là một trợ lí y tế hữu ích."}
        ]

    # Lưu cả bản gốc và bản không dấu để tiện xử lý
    conversations[user].append({"role": "user", "content": normalized_msg})

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
