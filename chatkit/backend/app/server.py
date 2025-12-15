"""ChatKit server that streams responses using exported Agent Builder workflow."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, AsyncIterator

import httpx
import vercel_blob
from agents import (
    Agent,
    CodeInterpreterTool,
    ModelSettings,
    Runner,
    WebSearchTool,
)
from chatkit.agents import AgentContext, simple_to_agent_input, stream_agent_response
from chatkit.server import ChatKitServer
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    ThreadItemAddedEvent,
    ThreadItemDoneEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
)

from .memory_store import MemoryStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

MAX_RECENT_ITEMS = 30


async def upload_container_file_to_blob(
    container_id: str, file_id: str, filename: str
) -> str | None:
    """Download file from OpenAI container and upload to Vercel Blob, return public URL."""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not set")
            return None

        # Download from OpenAI container
        url = f"https://api.openai.com/v1/containers/{container_id}/files/{file_id}/content"
        logger.info(f"Downloading from OpenAI: {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60.0,
            )
            response.raise_for_status()

        file_content = response.content
        logger.info(f"Downloaded {len(file_content)} bytes from OpenAI container")

        # Upload to Vercel Blob
        blob_path = f"chatkit-files/{uuid.uuid4().hex[:8]}_{filename}"
        logger.info(f"Uploading to Vercel Blob: {blob_path}")

        result = vercel_blob.put(blob_path, file_content)
        blob_url = result.get("url")

        logger.info(f"Uploaded to Vercel Blob: {blob_url}")
        return blob_url

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading from OpenAI: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error uploading to Vercel Blob: {e}")
        return None


# Tool definitions (from Agent Builder export)
web_search_preview = WebSearchTool(
    search_context_size="medium",
    user_location={"type": "approximate"},
)

code_interpreter = CodeInterpreterTool(
    tool_config={
        "type": "code_interpreter",
        "container": {
            "type": "auto",
            "file_ids": [],
        },
    }
)

# Agent definition (from Agent Builder export)
assistant_agent = Agent[AgentContext[dict[str, Any]]](
    name="My agent",
    instructions="""당신은 훌륭한 조언가에요.
그림 그려달라는 요청시에 image generation tool을 사용해 주세요.
계산이 필요한 경우 code interpreter tool을 사용해 주세요.""",
    model="gpt-5.2-chat-latest",
    tools=[
        web_search_preview,
        code_interpreter,
    ],
    model_settings=ModelSettings(
        temperature=1,
        max_tokens=2048,
    ),
)


class StarterChatServer(ChatKitServer[dict[str, Any]]):
    """Server implementation that keeps conversation state in memory."""

    def __init__(self) -> None:
        self.store: MemoryStore = MemoryStore()
        super().__init__(self.store)

    async def respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        logger.info(f"Processing request for thread: {thread.id}")

        items_page = await self.store.load_thread_items(
            thread.id,
            after=None,
            limit=MAX_RECENT_ITEMS,
            order="desc",
            context=context,
        )
        items = list(reversed(items_page.data))
        agent_input = await simple_to_agent_input(items)

        logger.info(f"Agent input items: {len(items)}")

        agent_context = AgentContext(
            thread=thread,
            store=self.store,
            request_context=context,
        )

        logger.info("Starting agent run with tools: web_search, code_interpreter")
        result = Runner.run_streamed(
            assistant_agent,
            agent_input,
            context=agent_context,
        )

        # Track container files from raw events
        container_files: list[dict[str, str]] = []

        async for event in stream_agent_response(agent_context, result):
            logger.debug(f"Stream event: {type(event).__name__}")
            yield event

        # After streaming, check raw_responses for container file citations
        try:
            logger.info(f"raw_responses count: {len(result.raw_responses)}")
            for i, response in enumerate(result.raw_responses):
                logger.info(f"Response {i}: {type(response).__name__}")
                logger.info(f"Response {i} content: {response}")
                output = getattr(response, "output", None)
                if not output:
                    continue
                for output_item in output:
                    content_list = getattr(output_item, "content", None)
                    if not content_list:
                        continue
                    for content in content_list:
                        annotations = getattr(content, "annotations", None)
                        if not annotations:
                            continue
                        for annotation in annotations:
                            ann_type = getattr(annotation, "type", None)
                            if ann_type == "container_file_citation":
                                container_id = getattr(annotation, "container_id", None)
                                file_id = getattr(annotation, "file_id", None)
                                filename = getattr(annotation, "filename", None)
                                if container_id and file_id and filename:
                                    container_files.append({
                                        "container_id": container_id,
                                        "file_id": file_id,
                                        "filename": filename,
                                    })
                                    logger.info(f"Found container file: {filename} ({container_id}/{file_id})")
        except Exception as e:
            logger.warning(f"Error extracting container files: {e}")

        # If container files were found, upload to Vercel Blob and emit download links
        if container_files:
            logger.info(f"Found {len(container_files)} container files, uploading to Vercel Blob")

            # Upload files to Vercel Blob and build markdown links
            links = []
            for file_info in container_files:
                filename = file_info['filename']
                blob_url = await upload_container_file_to_blob(
                    file_info['container_id'],
                    file_info['file_id'],
                    filename,
                )
                if blob_url:
                    links.append(f"📎 [{filename}]({blob_url})")
                    logger.info(f"Blob URL for {filename}: {blob_url}")
                else:
                    logger.warning(f"Failed to upload {filename} to Vercel Blob")

            # Only emit message if we have successful uploads
            if links:
                # Create download message
                download_text = "\n\n---\n**생성된 파일 다운로드:**\n" + "\n".join(links)

                # Generate a unique item ID
                download_item_id = f"dl_{uuid.uuid4().hex[:12]}"

                download_item = AssistantMessageItem(
                    id=download_item_id,
                    thread_id=thread.id,
                    created_at=datetime.now(),
                    content=[
                        AssistantMessageContent(
                            type="output_text",
                            text=download_text,
                            annotations=[],
                        )
                    ],
                )

                # Emit the download message
                yield ThreadItemAddedEvent(item=download_item)
                yield ThreadItemDoneEvent(item=download_item)

                logger.info(f"Emitted download links message: {download_item_id}")

        logger.info(f"Completed response for thread: {thread.id}")
