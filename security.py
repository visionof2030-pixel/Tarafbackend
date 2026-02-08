# security.py
from fastapi import Header, HTTPException
from database import get_connection
from datetime import datetime

def activation_required(
    x_activation_code: str = Header(...)
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, is_active, expires_at, usage_limit, usage_count
        FROM activation_codes
        WHERE code=?
    """, (x_activation_code,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid code")

    code_id, active, expires, limit, used = row

    if not active:
        conn.close()
        raise HTTPException(status_code=401, detail="Code disabled")

    if expires and datetime.fromisoformat(expires) < datetime.utcnow():
        conn.close()
        raise HTTPException(status_code=401, detail="Code expired")

    if limit is not None and used >= limit:
        conn.close()
        raise HTTPException(status_code=401, detail="Usage limit reached")

    conn.close()
    return code_id