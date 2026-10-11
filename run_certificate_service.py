import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "certificate_service.certificate_api:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "8000")),
        app_dir="src",
    )

