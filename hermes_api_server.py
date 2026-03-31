"""Minimal FastAPI wrapper for Hermes Agent.

Endpoints:
- GET  /healthz
- GET  /status
- POST /send
"""

from __future__ import annotations

import os
import threading
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from gateway.status import is_gateway_running
from run_agent import AIAgent


class SendRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message to Hermes")
    session_id: str | None = Field(default=None, description="Optional session identifier")
    model: str | None = Field(default=None, description="Optional model override for this request")


class SendResponse(BaseModel):
    ok: bool
    response: str
    model: str
    session_id: str | None = None


app = FastAPI(title="Hermes API", version="0.1.0")
_agent_lock = threading.Lock()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def status() -> dict[str, Any]:
    gateway_running = False
    gateway_error = None
    try:
        gateway_running = bool(is_gateway_running())
    except Exception as e:
        gateway_error = str(e)

    return {
        "status": "ok",
        "gateway_running": gateway_running,
        "gateway_error": gateway_error,
    }


@app.post("/send", response_model=SendResponse)
def send(req: SendRequest) -> SendResponse:
    chosen_model = req.model or os.getenv("HERMES_API_MODEL") or ""
    kwargs: dict[str, Any] = {}
    if chosen_model:
        kwargs["model"] = chosen_model
    if req.session_id:
        kwargs["session_id"] = req.session_id

    try:
        with _agent_lock:
            agent = AIAgent(**kwargs)
            result = agent.chat(req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"send failed: {e}") from e

    return SendResponse(
        ok=True,
        response=result,
        model=chosen_model or "(config default)",
        session_id=req.session_id,
    )


def main() -> None:
    import uvicorn

    host = os.getenv("HERMES_API_HOST", "127.0.0.1")
    port = int(os.getenv("HERMES_API_PORT", "8080"))
    uvicorn.run("hermes_api_server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
