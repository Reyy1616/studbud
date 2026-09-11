from __future__ import annotations

import hmac
import json
import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Cookie, FastAPI, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

_SESSION_COOKIE = "studbud_admin"

from .config import load_config
from .embeddings import Embedder
from .ingest import SUPPORTED_SUFFIXES, Ingestor
from .llm import ChatClient, Message
from .query import build_user_message, initial_messages, retrieve
from .stores.factory import make_store

log = logging.getLogger (__name__)

_STATIC_DIR = Path(__file__).parent / "static"

class ChatTurn(BaseModel):
    role: str
    content: str
    
    
class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = []
    k: int | None = None


class LoginRequest(BaseModel):
    token: str
    

def create_app()-> FastAPI:
    cfg = load_config()
    cfg.ensure_dirs()
    
    store = make_store(cfg)
    embedder = Embedder.from_config(cfg)
    chat = ChatClient.from_config(cfg)
    ingestor = Ingestor(cfg, store, embedder)
    lock = threading.Lock()
    
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            store.close()
            
    
    app = FastAPI(title="studbud", lifespan=lifespan)
    app.state.cfg = cfg
    app.state.store = store
    app.state.embedder = embedder
    app.state.chat = chat
    app.state.ingestor = ingestor
    app.state.lock = lock
    
    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(
            _STATIC_DIR / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

    @app.get("/about")
    def about() -> FileResponse:
        return FileResponse(
            _STATIC_DIR / "about.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

    def _is_admin(cookie_value: str | None) -> bool:
        """Return True only when ingestion is unlocked for this request.

        A blank ADMIN_TOKEN means ingestion is locked for everyone. Comparison
        is constant-time to avoid leaking the secret via timing.
        """
        secret = cfg.admin_token
        if not secret or not cookie_value:
            return False
        return hmac.compare_digest(cookie_value, secret)

    @app.get("/api/session")
    def session(studbud_admin: str | None = Cookie(default=None)) -> dict[str, bool]:
        return {"authenticated": _is_admin(studbud_admin)}

    @app.post("/api/login")
    def login(req: LoginRequest, response: Response) -> dict[str, bool]:
        secret = cfg.admin_token
        if not secret:
            raise HTTPException(
                status_code=503,
                detail="ingestion is disabled: no ADMIN_TOKEN configured",
            )
        if not hmac.compare_digest(req.token.strip(), secret):
            raise HTTPException(status_code=401, detail="invalid credentials")
        response.set_cookie(
            key=_SESSION_COOKIE,
            value=secret,
            httponly=True,
            samesite="strict",
            max_age=60 * 60 * 8,
        )
        return {"authenticated": True}

    @app.post("/api/logout")
    def logout(response: Response) -> dict[str, bool]:
        response.delete_cookie(_SESSION_COOKIE)
        return {"authenticated": False}
    
    @app.post("/api/chat")
    def chat_endpoint(req: ChatRequest) -> StreamingResponse:
        question = req.message.strip()
        if not question:
            raise HTTPException(status_code=400, detail="empty message")
        top_k = req.k if req.k is not None else cfg.top_k
        
        def event_stream():
            try:
                with lock:
                    ctx = retrieve(store, embedder, question, top_k)
                    
                raw_history: list[Message] = [
                    {"role": t.role,"content": t.content}for t in req.history
                ]
                message: list[Message] = initial_messages(cfg.system_prompt)
                message.extend(raw_history)
                message.append(
                    {"role":"user", "content": build_user_message(question, ctx)}
                )
                
                for piece in chat.stream(message):
                    yield _sse("token", {"text":piece})
                    
                yield _sse("sources", {"hits": _hits_payload(ctx.hits)})
                yield _sse("done",{})
                
                
            except Exception as exc:
                log.exception("chat endpoint failed")
                yield _sse("error", {"message": str(exc)})
                
        return StreamingResponse(event_stream(), media_type="text/event-stream")
    
    @app.post("/api/upload")
    def upload(
        file: UploadFile,
        studbud_admin: str | None = Cookie(default=None),
    ) -> dict[str, Any]:
        if not _is_admin(studbud_admin):
            raise HTTPException(
                status_code=403,
                detail="ingestion is restricted to lecturers and developers",
            )

        name= Path(file.filename or "").name
        if not name:
            raise HTTPException(status_code=400, detail="missing filename")
        
        
        suffix = Path(name).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"unsupported document type: {suffix or 'no extension'}",
            )
            
        target = cfg.documents_dir / name
        if target.exists():
            raise HTTPException(
                status_code=400,
                detail=f"{name} already exists in documents",
            )
            
        data = file.file.read()
        target.write_bytes(data)
        
        with lock:
            try:
                ingestor.ingest_file(target)
            except Exception as exc:
                log.exception("ingest failed for %s", target)
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            
        return {"filename": name, "bytes": len(data)}
            
    
    return app


def _sse(event:str, payload: dict[str,Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"

def _hits_payload(hits: list) -> list[dict[str,Any]]:
    return[
        {
            "filename": Path(h.source_path).name,
            "chunk_index": h.chunk_index,
            "score":round(float(h.score), 3),
        }
        for h in hits
    ]

app = create_app()