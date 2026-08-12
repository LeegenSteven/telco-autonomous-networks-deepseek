"""Project-local Chinese web UI backed by the ADK API server."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app


AGENTS_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = AGENTS_DIR / "frontend"


app = get_fast_api_app(
    agents_dir=str(AGENTS_DIR),
    web=False,
    use_local_storage=True,
    logo_text="电信智能运维平台",
)


@app.middleware("http")
async def disable_browser_cache(request, call_next):
    """Prevent stale session lists and frontend assets in the local UI."""

    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="chinese_frontend",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="启动中文电信智能运维页面")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
