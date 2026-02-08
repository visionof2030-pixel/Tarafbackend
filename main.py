# main.py
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timedelta
import os
import itertools
import google.generativeai as genai

from database import init_db, get_connection
from create_key import create_key
from security import activation_required

# ---------- Init DB ----------
init_db()

# ---------- App ----------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Admin Auth ----------
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

def admin_auth(x_admin_token: str = Header(...)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ---------- Models ----------
class Req(BaseModel):
    prompt: str

class GenerateKeyReq(BaseModel):
    plan: str

# ---------- Plans ----------
PLANS = {
    "5min_1":   {"minutes": 5,    "usage": 1},
    "15min_2":  {"minutes": 15,   "usage": 2},
    "30min_3":  {"minutes": 30,   "usage": 3},
    "1day_6":   {"days": 1,       "usage": 6},
    "3day_15":  {"days": 3,       "usage": 15},
    "7day_25":  {"days": 7,       "usage": 25},
    "1m_45":    {"days": 30,      "usage": 45},
    "2m_65":    {"days": 60,      "usage": 65},
    "3m_120":   {"days": 90,      "usage": 120},
    "5m_200":   {"days": 150,     "usage": 200},
}

# ---------- Gemini Keys ----------
api_keys = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
    os.getenv("GEMINI_API_KEY_6"),
    os.getenv("GEMINI_API_KEY_7"),
]
api_keys = [k for k in api_keys if k]
key_cycle = itertools.cycle(api_keys) if api_keys else None

def get_api_key():
    if not key_cycle:
        raise HTTPException(status_code=500, detail="No Gemini API key configured")
    return next(key_cycle)

# ---------- Routes ----------
@app.get("/")
def root():
    return {"status": "running"}

@app.get("/health")
def health(_: int = Depends(activation_required)):
    return {"status": "ok"}

# ---------- Main Feature (usage counted ONLY here) ----------
@app.post("/ask")
def ask(
    req: Req,
    code_id: int = Depends(activation_required)
):
    # ⬅️ الخصم هنا فقط
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE activation_codes
        SET usage_count = usage_count + 1,
            last_used_at = ?
        WHERE id = ?
        """,
        (datetime.utcnow().isoformat(), code_id)
    )
    conn.commit()
    conn.close()

    genai.configure(api_key=get_api_key())
    model = genai.GenerativeModel("models/gemini-2.5-flash-lite")
    response = model.generate_content(req.prompt)

    return {"answer": response.text}

# ---------- Admin APIs (محميّة بالتوكن) ----------
@app.post("/admin/generate", dependencies=[Depends(admin_auth)])
def admin_generate(req: GenerateKeyReq):
    if req.plan not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    plan = PLANS[req.plan]
    now = datetime.utcnow()
    expires_at = now

    if "minutes" in plan:
        expires_at += timedelta(minutes=plan["minutes"])
    if "days" in plan:
        expires_at += timedelta(days=plan["days"])

    return {
        "code": create_key(
            expires_at.isoformat(),
            plan["usage"]
        ),
        "expires_at": expires_at.isoformat(),
        "usage_limit": plan["usage"]
    }

@app.get("/admin/codes", dependencies=[Depends(admin_auth)])
def admin_codes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id,
            code,
            is_active,
            expires_at,
            usage_limit,
            usage_count
        FROM activation_codes
    """)
    rows = cur.fetchall()
    conn.close()

    now = datetime.utcnow()
    result = []

    for r in rows:
        expired = False
        if r[3] and datetime.fromisoformat(r[3]) < now:
            expired = True
        if r[4] is not None and r[5] >= r[4]:
            expired = True

        result.append({
            "id": r[0],
            "code": r[1],
            "active": bool(r[2]),
            "expires_at": r[3],
            "usage_limit": r[4],
            "usage_count": r[5],
            "expired": expired
        })

    return result

@app.put("/admin/code/{code_id}/toggle", dependencies=[Depends(admin_auth)])
def admin_toggle(code_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE activation_codes
        SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END
        WHERE id = ?
        """,
        (code_id,)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/admin/code/{code_id}", dependencies=[Depends(admin_auth)])
def admin_delete(code_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM activation_codes WHERE id=?", (code_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

# ---------- Admin Panel HTML (بدون حماية هيدر) ----------
@app.get("/admin/panel", response_class=HTMLResponse)
def admin_panel():
    return Path("admin.html").read_text(encoding="utf-8")