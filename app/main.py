"""
TechNova Support Bot — FastAPI server.

Replaces the fictional Neam runtime with a real Python/FastAPI implementation.
All endpoints mirror the original Neam agent HTTP channel spec.

Lambda entry point: app.main.handler  (via Mangum ASGI adapter)
"""
from __future__ import annotations

import time
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from mangum import Mangum
from pydantic import BaseModel

from .database import Database
from .knowledge import KnowledgeBase
from .sessions import SessionManager
from .llm import LLMClient
import os

app = FastAPI(
    title="TechNova Support Bot",
    version="1.0.0",
    description="Nova — AI-powered customer support for TechNova electronics.",
)

# Singletons — initialised once per Lambda container cold-start
_db = Database()
_kb = KnowledgeBase()
_sessions = SessionManager()
_llm = LLMClient()

_API_KEY = os.environ.get("NEAM_API_KEY", "dev-key-change-me")


# ── Schemas ───────────────────────────────────────────────────────────────────


class MessageRequest(BaseModel):
    message: str


# ── Auth ──────────────────────────────────────────────────────────────────────


def require_api_key(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header required: Bearer <api-key>",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if token != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return token


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    """Public health check — no auth required."""
    return {
        "status": "healthy",
        "service": "TechNova Support Bot (Nova)",
        "version": "1.0.0",
        "llm_backend": _llm.backend_name(),
        "knowledge_chunks": _kb.count(),
        "timestamp": int(time.time()),
    }


@app.get("/api/v1/claw")
def list_agents(_: str = Depends(require_api_key)):
    """List active Claw agents."""
    return {
        "agents": ["support_bot"],
        "active_sessions": _sessions.count(),
    }


@app.post("/api/v1/claw/support_bot/sessions/{session_key}/message")
def send_message(
    session_key: str,
    body: MessageRequest,
    _: str = Depends(require_api_key),
):
    """Send a message to Nova and receive a reply."""
    history = _sessions.load(session_key)
    context_chunks = _kb.search(body.message, top_k=4)
    context = "\n\n---\n\n".join(context_chunks)

    reply = _llm.chat(
        message=body.message,
        history=history,
        context=context,
        db=_db,
    )

    history.append({"role": "user", "content": body.message})
    history.append({"role": "assistant", "content": reply})
    _sessions.save(session_key, history)

    return {
        "response": reply,
        "session_key": session_key,
        "turn": len(history) // 2,
    }


@app.post("/api/v1/claw/support_bot/sessions/{session_key}/reset")
def reset_session(session_key: str, _: str = Depends(require_api_key)):
    """Reset (delete) a session's conversation history."""
    _sessions.delete(session_key)
    return {"message": f"Session '{session_key}' has been reset."}


@app.get("/api/v1/metrics")
def metrics(_: str = Depends(require_api_key)):
    """Runtime metrics."""
    return {
        "active_sessions": _sessions.count(),
        "knowledge_chunks": _kb.count(),
        "llm_backend": _llm.backend_name(),
        "uptime_ts": int(time.time()),
    }


# ── Lambda / ASGI handler ─────────────────────────────────────────────────────

handler = Mangum(app, lifespan="off")
