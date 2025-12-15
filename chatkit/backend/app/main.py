"""FastAPI entrypoint for the ChatKit starter backend."""

from __future__ import annotations

import logging
import os
import uuid

import httpx
from chatkit.server import StreamingResult
from fastapi import Cookie, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .server import StarterChatServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ChatKit Starter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chatkit_server = StarterChatServer()


@app.post("/chatkit")
async def chatkit_endpoint(
    request: Request,
    user_id: str | None = Cookie(default=None),
) -> Response:
    """Proxy the ChatKit web component payload to the server implementation."""
    # Generate user_id if not present in cookie
    is_new_user = False
    if not user_id:
        user_id = str(uuid.uuid4())
        is_new_user = True
        logger.info(f"New user created: {user_id}")
    else:
        logger.info(f"Existing user: {user_id}")

    payload = await request.body()
    logger.debug(f"Payload size: {len(payload)} bytes")

    # Pass user_id in context for filtering
    context = {"request": request, "user_id": user_id}
    result = await chatkit_server.process(payload, context)
    logger.info(f"ChatKit response type: {type(result).__name__}")

    if isinstance(result, StreamingResult):
        response = StreamingResponse(result, media_type="text/event-stream")
    elif hasattr(result, "json"):
        response = Response(content=result.json, media_type="application/json")
    else:
        response = JSONResponse(result)

    # Set user_id cookie (1 year expiry)
    if is_new_user:
        response.set_cookie(
            key="user_id",
            value=user_id,
            max_age=365 * 24 * 60 * 60,
            httponly=True,
            samesite="lax",
        )

    return response


@app.get("/api/containers/{container_id}/files/{file_id}/content")
async def get_container_file_content(
    container_id: str, file_id: str, filename: str = "download"
) -> Response:
    """Download a file from an OpenAI container using direct HTTP API."""
    logger.info(f"Downloading file from container: {container_id}, file: {file_id}")

    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        # Direct HTTP request to OpenAI API
        url = f"https://api.openai.com/v1/containers/{container_id}/files/{file_id}/content"
        logger.info(f"Fetching from URL: {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60.0,
            )
            response.raise_for_status()

        content = response.content
        logger.info(f"File retrieved: {filename}, size: {len(content)} bytes")

        # Return file as downloadable response
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading file: {e.response.status_code} - {e.response.text}")
        return JSONResponse({"error": str(e)}, status_code=e.response.status_code)
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)
