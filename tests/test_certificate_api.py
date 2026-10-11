import json

import httpx
from fastapi.testclient import TestClient

from certificate_service.certificate_api import create_app
from certificate_service.infrai_pdf import InfraiPdfClient


class RecordingPdfClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def generate(self, html: str, idempotency_key: str) -> dict[str, str]:
        self.calls.append((html, idempotency_key))
        return {"url": "https://documents.example/certificate.pdf"}


def request_body(moderation: str = "approved") -> dict[str, object]:
    return {
        "event": {"event_id": "raid-42", "title": "Citadel Raid", "state": "completed"},
        "participant": {
            "player_id": "player-7",
            "attended": True,
            "asset": {
                "asset_id": "banner-9",
                "display_name": "Mira & Co",
                "moderation": moderation,
            },
        },
    }


def test_approved_participant_gets_one_certificate_request() -> None:
    pdf = RecordingPdfClient()
    response = TestClient(create_app(pdf)).post("/certificates", json=request_body())

    assert response.status_code == 200
    assert response.json()["status"] == "generated"
    assert len(pdf.calls) == 1
    assert "Mira &amp; Co" in pdf.calls[0][0]
    assert pdf.calls[0][1].startswith("certificate-")


def test_queued_asset_stays_out_of_certificate_generation() -> None:
    pdf = RecordingPdfClient()
    response = TestClient(create_app(pdf)).post(
        "/certificates", json=request_body(moderation="queued")
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "status": "not_eligible",
        "reason": "asset_not_approved",
    }
    assert pdf.calls == []


def test_pdf_request_includes_idempotency_key_in_json() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "data": {"url": "https://example.com/pdf"}})

    client = InfraiPdfClient("test-key", transport=httpx.MockTransport(respond))
    try:
        client.generate("<h1>Certificate</h1>", "certificate-stable")
    finally:
        client.close()

    assert json.loads(requests[0].content)["idempotency_key"] == "certificate-stable"
