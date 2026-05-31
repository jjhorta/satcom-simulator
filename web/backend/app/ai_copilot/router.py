"""CARL router — streaming chat endpoint with tool calling."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..auth import get_current_user
from ..config import Settings, get_settings
from ..ai_config_store import feature_gate
from .config_store import load_carl_config, save_carl_config, get_tool_list
from .tools import TOOL_SCHEMAS
from .chat_store import list_chats, get_chat, create_chat, update_chat_name, delete_chat, add_messages
from .executor import execute_tool_call

router = APIRouter(prefix="/api/carl", tags=["carl"])

DEFAULT_SYSTEM_PROMPT = (
    "You are CARL (Constellation AI Reasoning Layer), an AI constellation engineer "
    "inspired by Carl Sagan. You make complex orbital mechanics accessible and exciting. "
    "You have direct access to the Constellation Simulator API. "
    "Create simulations, analyze results, and iterate on designs. "
    "Explain your reasoning in clear, vivid terms — use analogies, be precise, and inspire curiosity. "
    "Always use metric units (km, degrees, dB). Be technical but not dry."
)


# ── Config endpoints (for Admin page) ──────────────────────────────────────


@router.get("/config")
async def get_carl_config(
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Return CARL's full configuration (no secrets)."""
    return load_carl_config(settings.outputs_dir)


@router.put("/config")
async def update_carl_config(
    payload: dict[str, Any],
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Update CARL configuration fields."""
    allowed = {"name", "persona", "tools", "temperature", "max_tools_per_turn"}
    patch = {k: v for k, v in payload.items() if k in allowed and v is not None}
    return save_carl_config(settings.outputs_dir, patch)


# ── Chat CRUD endpoints ──────────────────────────────────────────────────


@router.get("/chats")
async def carl_list_chats(
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """List all chats for the current user."""
    return list_chats(settings.outputs_dir, user.get("id", 0))


@router.post("/chats")
async def carl_create_chat(
    body: dict,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
) -> dict:
    """Create a new chat session."""
    name = body.get("name", "New Chat")
    return create_chat(settings.outputs_dir, user.get("id", 0), name)


@router.get("/chats/{chat_id}")
async def carl_get_chat(
    chat_id: str,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
) -> dict:
    """Get a single chat with all messages."""
    chat = get_chat(settings.outputs_dir, chat_id, user.get("id", 0))
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.put("/chats/{chat_id}")
async def carl_update_chat(
    chat_id: str,
    body: dict,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
) -> dict:
    """Update chat name."""
    name = body.get("name", "")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if not update_chat_name(settings.outputs_dir, chat_id, user.get("id", 0), name):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "ok"}


@router.delete("/chats/{chat_id}")
async def carl_delete_chat(
    chat_id: str,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
) -> dict:
    """Delete a chat session."""
    if not delete_chat(settings.outputs_dir, chat_id, user.get("id", 0)):
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "deleted"}


# ── Chat endpoint ──────────────────────────────────────────────────────────


@router.post("/chat")
async def carl_chat(
    request: Request,
    settings: Settings = Depends(get_settings),
    user: dict = Depends(get_current_user),
):
    """
    Streaming chat with CARL — supports tool calling.

    Request body:
    {
        "chat_id": "uuid",  // optional — if provided, messages are persisted
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "Design a VDES constellation..."}
        ]
    }

    Response: SSE stream with text deltas and tool_call status updates.
    """
    cfg = feature_gate(settings.outputs_dir)
    if cfg is None:
        raise HTTPException(
            status_code=400,
            detail="AI API key not configured. Set it in Settings → AI.",
        )

    body = await request.json()
    new_messages: list[dict] = body.get("messages", [])
    chat_id: str | None = body.get("chat_id")
    chat_name: str | None = body.get("name")

    user_id = user.get("id", 0)

    # Load or create chat
    if chat_id:
        existing_chat = get_chat(settings.outputs_dir, chat_id, user_id)
        if not existing_chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        # Build full message history: existing + new user message
        messages = list(existing_chat.get("messages", []))
        # Persist new user messages
        new_user_msgs = [m for m in new_messages if m.get("role") == "user"]
        if new_user_msgs:
            add_messages(settings.outputs_dir, chat_id, user_id, new_user_msgs)
        messages.extend(new_messages)
    else:
        # No chat_id — create one automatically
        chat = create_chat(settings.outputs_dir, user_id, chat_name or "New Chat")
        chat_id = chat["id"]
        messages = list(new_messages)
        if messages:
            add_messages(settings.outputs_dir, chat_id, user_id, messages)

    # Load CARL persona
    carl_cfg = load_carl_config(settings.outputs_dir)
    system_content = carl_cfg.get("persona", DEFAULT_SYSTEM_PROMPT)
    temperature = carl_cfg.get("temperature", 0.5)
    max_tools = carl_cfg.get("max_tools_per_turn", 5)
    enabled_tools = get_tool_list(carl_cfg)

    # Build active tool schemas
    active_tools = [t for t in TOOL_SCHEMAS if t["function"]["name"] in enabled_tools]

    # Prepend system message if not provided
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": system_content})

    token = request.headers.get("authorization", "").replace("Bearer ", "")
    base_url = f"{settings.app_url}" if settings.app_url else "http://localhost:8000"
    if "localhost" in base_url:
        base_url = "http://localhost:8000"

    async def generate():
        turn_count = 0
        while turn_count < max_tools + 1:
            turn_count += 1
            endpoint = cfg["base_url"].rstrip("/") + "/chat/completions"

            llm_payload: dict[str, Any] = {
                "model": cfg["model"],
                "stream": True,
                "temperature": temperature,
                "messages": messages,
            }
            if active_tools and turn_count <= max_tools:
                llm_payload["tools"] = active_tools
                llm_payload["tool_choice"] = "auto"

            collected_text = ""
            tool_calls: dict[int, dict] = {}

            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    async with client.stream(
                        "POST",
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {cfg['api_key']}",
                            "Content-Type": "application/json",
                        },
                        json=llm_payload,
                    ) as resp:
                        if resp.status_code != 200:
                            body_err = await resp.aread()
                            err = body_err.decode("utf-8", errors="replace")[:300]
                            yield json.dumps({"type": "error", "content": f"LLM API {resp.status_code}: {err}"}) + "\n"
                            return

                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [{}])
                                delta = choices[0].get("delta", {})

                                # Text content
                                if delta.get("content"):
                                    collected_text += delta["content"]
                                    yield json.dumps({
                                        "type": "delta",
                                        "content": delta["content"],
                                        "turn": turn_count,
                                    }) + "\n"

                                # Tool calls
                                if delta.get("tool_calls"):
                                    for tc in delta["tool_calls"]:
                                        idx = tc.get("index", 0)
                                        if idx not in tool_calls:
                                            tool_calls[idx] = {
                                                "id": tc.get("id", f"call_{idx}"),
                                                "name": tc["function"]["name"],
                                                "arguments": "",
                                            }
                                        if tc["function"].get("arguments"):
                                            tool_calls[idx]["arguments"] += tc["function"]["arguments"]

                            except json.JSONDecodeError:
                                pass

            except httpx.TimeoutException:
                yield json.dumps({"type": "error", "content": "CARL: Request timed out after 120s. Try a simpler question."}) + "\n"
                return
            except Exception as exc:
                yield json.dumps({"type": "error", "content": f"CARL error: {str(exc)[:200]}"}) + "\n"
                return

            # Process tool calls if any
            if tool_calls:
                yield json.dumps({
                    "type": "tool_calls_start",
                    "tool_calls": [
                        {"id": tc["id"], "name": tc["name"]} for tc in tool_calls.values()
                    ],
                }) + "\n"

                # Execute each tool
                tool_results = []
                for tc in tool_calls.values():
                    result = await execute_tool_call(tc, base_url, token, settings.outputs_dir)
                    tool_results.append(result)
                    yield json.dumps({
                        "type": "tool_result",
                        "tool_call_id": tc["id"],
                        "name": tc["name"],
                        "status": "error" if result.get("content", "").startswith("Error") else "done",
                    }) + "\n"

                # Add assistant message with tool calls
                assistant_msg: dict[str, Any] = {"role": "assistant", "content": collected_text or None}
                if tool_calls:
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]},
                        }
                        for tc in tool_calls.values()
                    ]
                messages.append(assistant_msg)

                # Add tool results
                for tr in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "content": tr["content"],
                    })

                # Continue loop to let LLM process tool results
                continue
            else:
                # No tool calls — finalize
                if collected_text:
                    messages.append({"role": "assistant", "content": collected_text})
                    # Persist assistant response
                    if chat_id:
                        add_messages(settings.outputs_dir, chat_id, user_id, [{"role": "assistant", "content": collected_text}])
                yield json.dumps({"type": "done", "chat_id": chat_id, "turn": turn_count}) + "\n"
                return

        # Max turns reached
        yield json.dumps({"type": "done", "chat_id": chat_id, "turn": turn_count, "note": "Max turns reached"}) + "\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
