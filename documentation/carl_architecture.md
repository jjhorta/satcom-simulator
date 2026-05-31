# 🤖 CARL — Constellation AI Reasoning Layer

## Architecture & Chat System

---

## 1. What is CARL?

CARL (Constellation AI Reasoning Layer) is an AI copilot that lives inside the Constellation Simulator. Users describe mission requirements in plain language, and CARL:

1. Interprets the request
2. Calls internal APIs to **submit simulations** (heatmap, latency, batch sweeps, ...)
3. **Checks results** by fetching job status
4. **Reads CSV data** from completed jobs
5. **Explains** findings in natural language

It is named after **Carl Sagan** — the AI persona is inspired by his ability to make complex science accessible and exciting.

---

## 2. Architecture Overview

```
┌─ Browser ──────────────────────────────────────────────┐
│                                                        │
│  CopilotPage.tsx                                       │
│    └─ CopilotChat.tsx  ← UI component                  │
│         ├─ Sidebar (chats list)                        │
│         ├─ Messages area (chat history display)        │
│         ├─ Input box                                   │
│         ├─ HelpModal / ResourcesModal                  │
│         └─ SSE stream reader (fetch + ReadableStream)  │
│                                                        │
│  Auth: JWT token from useAuthStore                     │
└──────────────────────┬──────────────────────────────────┘
                       │ POST /api/carl/chat  (SSE)
                       │ Headers: Authorization: Bearer <jwt>
                       │ Body: { chat_id, messages }
                       ▼
┌─ Backend (FastAPI) ─────────────────────────────────────┐
│                                                         │
│  router.py  (POST /api/carl/chat)                       │
│    ├─ 1. Extract JWT user → get_current_user()          │
│    ├─ 2. Load or create chat from chat_store.py         │
│    ├─ 3. Build message list:                             │
│    │      existing_messages + new_user_message           │
│    ├─ 4. Load CARL persona from config_store.py         │
│    ├─ 5. Load enabled tools from get_tool_list()        │
│    ├─ 6. Send to LLM (OpenAI-compatible API)            │
│    │      with function-calling tool schemas             │
│    ├─ 7. Stream response back via SSE                   │
│    └─ 8. Persist assistant response to chat_store       │
│                                                         │
│  executor.py  (tool execution)                          │
│    ├─ submit_simulation  → POST /api/jobs               │
│    ├─ submit_batch_sweep → POST /api/jobs/batch         │
│    ├─ get_job_status    → GET  /api/jobs/{id}           │
│    ├─ read_csv_data     → GET  /api/jobs/{id}/csv/...   │
│    ├─ get_simulation_options → GET /api/options          │
│    └─ upload_file       → POST /api/jobs/upload         │
│                                                         │
│  chat_store.py  (persistence layer)                     │
│    └─ JSON file: outputs_dir/carl_chats.json            │
│                                                         │
│  config_store.py  (CARL settings)                       │
│    └─ JSON file: outputs_dir/ai_carl_config.json        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. How the Chat Loop Works (Step by Step)

### Step 1 — User sends a message

The frontend calls:

```
POST /api/carl/chat
Authorization: Bearer <jwt>
{
  "chat_id": "uuid",         // optional — creates new if absent
  "messages": [
    { "role": "user", "content": "Design a VDES constellation..." }
  ]
}
```

### Step 2 — Backend loads context

The router:

1. Looks up `chat_id` in `carl_chats.json`
2. Loads **all previous messages** from that chat
3. **Appends** the new user message
4. Prepends the **system prompt** (CARL persona + domain restrictions)

Result: a message array like:

```python
[
  {"role": "system", "content": "You are CARL..."},
  {"role": "user",   "content": "Design a VDES constellation..."},  # old
  {"role": "assistant", "content": "I suggest 24 sats..."},           # old
  {"role": "user",   "content": "Now try 48 sats"},                  # new
]
```

### Step 3 — LLM processes with tool schemas

The entire context is sent to an LLM (e.g. GPT-4o, Claude) along with the **tool definitions** for the 6 enabled functions:

- `submit_simulation`
- `submit_batch_sweep`
- `get_job_status`
- `read_csv_data`
- `get_simulation_options`
- `upload_file`

The LLM can respond with:
- **Text** — explanation, analysis, suggestions
- **Tool calls** — the LLM decides to call one or more functions

### Step 4 — Tool execution loop

When the LLM calls a tool:

```
LLM → {"function_call": {"name": "submit_simulation", "arguments": {...}}}
```

The backend:

1. Calls `executor.submit_simulation(...)` → makes HTTP request to internal API
2. Collects the result
3. Sends it back to the LLM as a "tool response"
4. LLM continues (may call more tools or produce final text)

This loop runs up to `max_tools_per_turn` (default: 5) to prevent infinite loops.

### Step 5 — Streaming response

The final text is streamed back via **Server-Sent Events (SSE)**:

```
{"type": "delta",     "content": "I've submitted..."}
{"type": "tool_calls_start", "tool_calls": [...]}
{"type": "tool_result",      "tool_call_id": "...", "status": "done"}
{"type": "delta",     "content": "The results show..."}
{"type": "done",      "chat_id": "..."}
```

### Step 6 — Persistence

After the turn completes, both the user message and the assistant response are **persisted** to `carl_chats.json`.

---

## 4. Why Must the Full History Be Re-Sent Every Time?

**LLMs are stateless.** Each API call to the LLM is independent — the model has no memory of previous calls.

Think of it like a messenger pigeon:

```
Turn 1: You send a letter  → pigeon flies to LLM → LLM replies and flies back
Turn 2: You send a NEW letter → pigeon flies again → LLM has NO IDEA what you said before
```

The LLM only sees what is in the **current request**. If we only sent the latest message:

```
Turn 5 request:
  "check it"
```

The LLM would respond: *"Check what? I have no context!"*

### The fix: re-send the entire conversation

```
Turn 5 request:
  "Design a VDES constellation for Panama Canal"     ← turn 1
  "I suggest 24 sats, 3 planes, 53°, 650km"            ← turn 2 (assistant)
  "starlink ku"                                         ← turn 3
  "Submitted job f759..."                               ← turn 4 (assistant)
  "check it"                                            ← turn 5 (new)
```

Now the LLM knows:
- What was requested (Panama Canal VDES)
- What was suggested (24 sats, 53°)
- That the user switched to Starlink Ku
- That a job was submitted (f759...)
- And that the user wants to check its status

### Token limit consideration

LLMs have a **context window** (token limit). Sending the full history consumes tokens:

| Model | Max tokens | ~10 turns | ~50 turns |
|-------|:----------:|:---------:|:---------:|
| GPT-4o | 128k | ~8k | ~40k |
| Claude Sonnet | 200k | ~8k | ~40k |
| DeepSeek V4 | 1M | ~8k | ~40k |

For most practical conversations, **50+ turns fit comfortably** in modern models. If the conversation grows too long, older messages are trimmed (oldest first) to stay within limits.

---

## 5. Multi-Tenancy & Security

Chats are **isolated per user**:

```
carl_chats.json
├── chats:
│   ├── { id: "abc", user_id: 1, messages: [...] }  ← admin
│   └── { id: "def", user_id: 2, messages: [...] }  ← other user
```

- Every endpoint filters by `user_id` from the JWT token
- User 1 can never see User 2's chats
- Authentication is enforced via `get_current_user()` dependency

---

## 6. Key Files

| File | Purpose |
|------|---------|
| `web/backend/app/ai_copilot/router.py` | FastAPI router: `/api/carl/*` endpoints |
| `web/backend/app/ai_copilot/tools.py` | Tool schemas in OpenAI function-calling format |
| `web/backend/app/ai_copilot/executor.py` | Executes tool calls by calling internal APIs |
| `web/backend/app/ai_copilot/chat_store.py` | Persists chat sessions to JSON |
| `web/backend/app/ai_copilot/config_store.py` | Loads/saves CARL persona + tool config |
| `web/frontend/src/components/CopilotChat.tsx` | Main chat UI component |
| `web/frontend/src/components/CopilotPage.tsx` | Page wrapper with header |
| `web/frontend/src/components/ResourcesModal.tsx` | Shows job resources from chat |
| `web/frontend/src/components/HelpModal.tsx` | Help examples modal |

---

## 7. Configuration (via Settings → AI → CARL)

| Setting | Default | Description |
|---------|---------|-------------|
| Name | `CARL` | Assistant name |
| Persona | Carl Sagan-inspired | System prompt (domain restrictions included) |
| Tools | All 6 enabled | Toggle which tools CARL can use |
| Temperature | 0.5 | Creativity (0.0 = strict, 1.0 = creative) |
| Max tools/turn | 5 | Max tool calls before generating response |
