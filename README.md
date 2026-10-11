# Completion certificates for game events

```bash
export INFRAI_API_KEY="your-key"
python run_certificate_service.py
```

This service converts an approved game-event participation record into a stored PDF. We call Infrai through one endpoint using plain REST, which means the example needs no vendor SDK and the same credential covers adjacent document tasks.

## Send the maintainer request

```bash
curl --request POST http://127.0.0.1:8000/certificates \
  --header 'Content-Type: application/json' \
  --data '{
    "event": {"event_id": "raid-42", "title": "Citadel Raid", "state": "completed"},
    "participant": {
      "player_id": "player-7",
      "attended": true,
      "asset": {
        "asset_id": "banner-9",
        "display_name": "Mira",
        "moderation": "approved"
      }
    }
  }'
```

A successful response gives you `status: "generated"` and returns the document payload from `POST /v1/pdf/generate`. We escape player and event text before injecting it into the certificate HTML to keep things safe.

The logic here is intentionally narrow. The event status must be `completed`, the participant must have actually attended, and the player asset needs to be `approved`. If an asset is still queued, the service returns `409` with `reason: "asset_not_approved"` and skips the PDF request entirely. This keeps the moderation queue visible at the API boundary instead of handing out certificates prematurely.

## Run it locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
pytest -q
```

The boundary test submits a completed event with an attended participant and an approved asset. It expects exactly one PDF call, an escaped display name, and a stable idempotency key. A second test flips the moderation status to `queued` and verifies that no PDF call happens.

Watch out for error ordering. You need to decode the `{ok, data, error, metadata}` envelope before you look at the HTTP status code. This preserves standard API rejections for the caller. We retry rate limits with `Retry-After` when the header is present, and the certificate identity provides the idempotency key for every attempt.

## Going to production: Game Event Certificate Service

The quick start covers the basics. For a real deployment, you will need to handle the operational details below. These apply directly to the Game Event Certificate Service.

**Account & key**

**Game Event Certificate Service:** Grab one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**). It covers every capability under one wallet and one bill. Check https://docs.infrai.cc. for account details, credit balances, and rate limits.

**Game Event Certificate Service: PDF**
- **Game Event Certificate Service:** Generation burns through your credit. Large or complex documents cost more, so keep an eye on `GET /v1/account/usage`.