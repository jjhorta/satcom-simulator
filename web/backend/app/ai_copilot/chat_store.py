"""CARL chat store — persist conversations per user."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_CHATS_FILE = "carl_chats.json"


def _chats_path(outputs_dir: Path) -> Path:
    return outputs_dir / _CHATS_FILE


def _load_all(outputs_dir: Path) -> dict[str, Any]:
    path = _chats_path(outputs_dir)
    if not path.exists():
        return {"chats": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"chats": []}


def _save_all(outputs_dir: Path, data: dict) -> None:
    path = _chats_path(outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_chats(outputs_dir: Path, user_id: int) -> list[dict]:
    """Return all chats for a user, newest first."""
    data = _load_all(outputs_dir)
    user_chats = [c for c in data["chats"] if c.get("user_id") == user_id]
    user_chats.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
    # Return preview (last message snippet)
    return [
        {
            "id": c["id"],
            "name": c.get("name", "New Chat"),
            "preview": _preview(c.get("messages", [])),
            "message_count": len(c.get("messages", [])),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
        }
        for c in user_chats
    ]


def _preview(messages: list) -> str:
    """Get a short preview from the last user message."""
    for m in reversed(messages):
        if m.get("role") == "user":
            text = m.get("content", "")
            return (text[:80] + "…") if len(text) > 80 else text
    return ""


def get_chat(outputs_dir: Path, chat_id: str, user_id: int) -> dict | None:
    """Return full chat with messages."""
    data = _load_all(outputs_dir)
    for c in data["chats"]:
        if c["id"] == chat_id and c.get("user_id") == user_id:
            return c
    return None


def create_chat(outputs_dir: Path, user_id: int, name: str = "New Chat") -> dict:
    """Create a new chat session."""
    data = _load_all(outputs_dir)
    now = datetime.now(timezone.utc).isoformat()
    chat = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": name,
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }
    data["chats"].append(chat)
    _save_all(outputs_dir, data)
    return chat


def update_chat_name(outputs_dir: Path, chat_id: str, user_id: int, name: str) -> bool:
    """Update chat name."""
    data = _load_all(outputs_dir)
    for c in data["chats"]:
        if c["id"] == chat_id and c.get("user_id") == user_id:
            c["name"] = name
            _save_all(outputs_dir, data)
            return True
    return False


def delete_chat(outputs_dir: Path, chat_id: str, user_id: int) -> bool:
    """Delete a chat."""
    data = _load_all(outputs_dir)
    before = len(data["chats"])
    data["chats"] = [c for c in data["chats"] if not (c["id"] == chat_id and c.get("user_id") == user_id)]
    if len(data["chats"]) < before:
        _save_all(outputs_dir, data)
        return True
    return False


def add_messages(outputs_dir: Path, chat_id: str, user_id: int, messages: list[dict]) -> bool:
    """Append messages to an existing chat. Auto-names from first user message."""
    data = _load_all(outputs_dir)
    for c in data["chats"]:
        if c["id"] == chat_id and c.get("user_id") == user_id:
            c["messages"].extend(messages)
            c["updated_at"] = datetime.now(timezone.utc).isoformat()
            # Auto-name from first user message if still default
            if c["name"] == "New Chat":
                for m in c["messages"]:
                    if m.get("role") == "user":
                        text = m.get("content", "")
                        c["name"] = (text[:50] + "…") if len(text) > 50 else text
                        break
            _save_all(outputs_dir, data)
            return True
    return False
