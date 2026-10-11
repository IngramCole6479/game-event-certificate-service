from __future__ import annotations

import hashlib
import html
import os
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_pdf import InfraiError, InfraiPdfClient


class EventState(str, Enum):
    LIVE = "live"
    COMPLETED = "completed"


class ModerationState(str, Enum):
    QUEUED = "queued"
    APPROVED = "approved"
    REJECTED = "rejected"


class PlayerAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1, max_length=80)
    moderation: ModerationState


class LiveEvent(BaseModel):
    event_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=120)
    state: EventState


class Participant(BaseModel):
    player_id: str = Field(min_length=1)
    attended: bool
    asset: PlayerAsset


class CertificateRequest(BaseModel):
    event: LiveEvent
    participant: Participant


class CertificateResult(BaseModel):
    status: str
    document: dict[str, Any]


def eligibility_reason(request: CertificateRequest) -> str | None:
    if request.event.state != EventState.COMPLETED:
        return "event_not_completed"
    if not request.participant.attended:
        return "participant_not_attended"
    if request.participant.asset.moderation != ModerationState.APPROVED:
        return "asset_not_approved"
    return None


def certificate_html(request: CertificateRequest) -> str:
    event_title = html.escape(request.event.title)
    player_name = html.escape(request.participant.asset.display_name)
    return (
        "<!doctype html><html><body style='font-family:sans-serif;text-align:center;padding:72px'>"
        "<h1>Completion certificate</h1>"
        f"<p>This certifies that <strong>{player_name}</strong> completed</p>"
        f"<h2>{event_title}</h2>"
        f"<small>Event {html.escape(request.event.event_id)}</small>"
        "</body></html>"
    )


def create_app(client: InfraiPdfClient | None = None) -> FastAPI:
    app = FastAPI(title="Game completion certificates")

    @app.post("/certificates", response_model=CertificateResult)
    def issue_certificate(request: CertificateRequest) -> CertificateResult:
        reason = eligibility_reason(request)
        if reason:
            raise HTTPException(status_code=409, detail={"status": "not_eligible", "reason": reason})

        pdf_client = client
        if pdf_client is None:
            api_key = os.environ.get("INFRAI_API_KEY")
            if not api_key:
                raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")
            pdf_client = InfraiPdfClient(api_key)

        identity = f"{request.event.event_id}:{request.participant.player_id}:{request.participant.asset.asset_id}"
        idempotency_key = "certificate-" + hashlib.sha256(identity.encode()).hexdigest()
        try:
            document = pdf_client.generate(certificate_html(request), idempotency_key)
        except InfraiError as exc:
            status = exc.status_code if 400 <= exc.status_code < 500 else 502
            raise HTTPException(status_code=status, detail={"code": exc.code, "error": exc.detail}) from exc
        return CertificateResult(status="generated", document=document)

    return app


app = create_app()

