# 🧠 CARL — Constellation AI Reasoning Layer (Plano)

**Nome:** CARL (Constellation AI Reasoning Layer) — em homenagem a Carl Sagan.

> *"Somewhere, something incredible is waiting to be known."* — Carl Sagan

## Rationale

**Hoje:** "Send data → get AI Insight" — one-shot, passivo, o AI não consegue agir.

**Amanhã:** Chat interativo com um **engenheiro de constelações especialista** que tem acesso a ferramentas (tool calling) para criar simulações, analisar resultados e iterar — tudo em linguagem natural.

---

## Arquitetura

```
[Frontend: Chat UI] ←→ [Backend: CARL API] ←→ [LLM Provider]
                              ↓
                    [Tool Registry (APIs internas)]
                              ↓
         ┌──────────┬──────────┬──────────┬──────────┐
         │ Submeter  │ Ler      │ Batch    │ Obter    │
         │ Job      │ Resultados│ Sweep    │ Options  │
         └──────────┴──────────┴──────────┴──────────┘
```

### Fluxo

1. User diz: *"Design a VDES constellation for Panama Canal coverage, max 24 sats"*
2. AI recebe a mensagem + ferramentas disponíveis
3. AI decide: *call get_options() para ver comms disponíveis → call submit_job(heatmap, 24 sats, 53°, VDES)*
4. Backend executa o job → retorna job_id
5. AI decide: *call get_job_status() → vê que está completed → call get_results()*
6. AI analisa os resultados e responde ao user com recomendações
7. User diz: *"What if I use 48 sats at 87°?"*
8. AI: *call submit_job(heatmap, 48 sats, 87°, VDES) → compara com o anterior*

---

## O que é necessário

### 1. Backend — Tool Registry (NOVO)

Ficheiro: `web/backend/app/ai_copilot/`

```
ai_copilot/
├── __init__.py
├── router.py          ← POST /api/copilot/chat (SSE streaming)
├── tools.py           ← Tool definitions (JSON schema para o LLM)
└── executor.py        ← Executa o tool call (chama APIs internas)
```

#### Ferramentas disponíveis para o AI:

| Tool | Descrição | Endpoint |
|------|-----------|----------|
| `get_simulation_options` | Lista comms, weather, modos, presets disponíveis | `GET /api/options` |
| `submit_simulation` | Cria um job de simulação | `POST /api/jobs` |
| `submit_batch_sweep` | Cria um sweep paramétrico | `POST /api/jobs/batch` |
| `get_job_status` | Ver estado + ficheiros de um job | `GET /api/jobs/{id}` |
| `get_job_results` | Ler CSV/JSON de resultados | `GET /api/jobs/{id}/files/{file}` |
| `read_csv_data` | CSV como JSON (para análise) | `GET /api/jobs/{id}/csv/{file}` |
| `constellation_presets` | Listar presets conhecidos | `GET /api/options` (já incluído) |
| `analyze_coverage` | Análise estatística de heatmap | (usar get_job_results + processamento local) |

#### Formato do tool schema (OpenAI function calling):

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "submit_simulation",
            "description": "Run a constellation simulation job",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["heatmap", "heatmap-rf", "orbit", "track", "route", "latency"]},
                    "sats": {"type": "integer"},
                    "planes": {"type": "integer"},
                    "inclination": {"type": "number"},
                    "altitude": {"type": "number"},
                    "comms": {"type": "string"},
                    "weather": {"type": "string"},
                    ...
                },
                "required": ["mode", "sats", "planes", "inclination"]
            }
        }
    },
    ...
]
```

#### Endpoint de Chat:

```
POST /api/copilot/chat
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "messages": [
    {"role": "system", "content": "You are an expert satellite constellation engineer..."},
    {"role": "user", "content": "Design a VDES constellation for Panama Canal coverage"}
  ]
}

→ SSE stream: chunks de texto + tool calls + resultados
```

**System prompt** do CARL (versão tool-calling):

```
You are CARL (Constellation AI Reasoning Layer), an expert satellite constellation engineer named after Carl Sagan. You have a passion for explaining complex orbital mechanics in simple, beautiful terms — just like Carl Sagan explained the cosmos. You have direct access to the 
Constellation Simulator API. You can create simulations, analyze results, 
and iterate on designs in real-time.

CAPABILITIES:
- Design Walker constellations based on mission requirements
- Run coverage heatmaps, RF link budgets, orbit visualizations
- Interpret results: coverage gaps, revisit times, SNR margins
- Compare configurations side-by-side
- Recommend geometry improvements (inclination, altitude, phasing)

RULES:
1. Always explain your reasoning before running simulations
2. Run simulations one at a time unless the user asks for a sweep
3. Analyze results quantitatively — give specific numbers
4. Suggest improvements and offer to test them
5. Use metric units (km, degrees, dB)
6. When the user uploads a file, use read_csv_data to analyze it
```

### 2. Frontend — Chat Interface (NOVO)

`web/frontend/src/components/CopilotChat.tsx`
`web/frontend/src/pages/CopilotPage.tsx`

#### Layout:

```
┌──────────────────────────────────────────────┐
│  🤖 CARL — Constellation Analyst       │
│                                              │
│  ┌──────────────────────────────────────────┐│
│  │ User: Design a VDES constellation for    ││
│  │       Panama Canal, max 24 sats          ││
│  ├──────────────────────────────────────────┤│
│  │ AI: Let me start with a Walker 24/4/1    ││
│  │     at 53° inclination, 600km...         ││
│  │     [Running simulation...]              ││
│  │                                          ││
│  │     Results: mean coverage 42.3%         ││
│  │     ⚠️ Coverage gap at Equator (0-10°N)  ││
│  │     💡 Suggested: try 24/6/1 at 35°      ││
│  │     [Would you like me to test this?]    ││
│  ├──────────────────────────────────────────┤│
│  │ User: Yes, test it                       ││
│  ├──────────────────────────────────────────┤│
│  │ AI: [Running 24/6/1 at 35°...]          ││
│  │     New results: mean coverage 51.8%     ││
│  │     ✅ Improvement of 9.5%               ││
│  └──────────────────────────────────────────┘│
│                                              │
│  [📎 Upload CSV/GeoJSON]  [💬 Type message ] │
│                                [Send ➤]      │
└──────────────────────────────────────────────┘
```

#### Estado:

```typescript
interface Message {
  role: 'user' | 'assistant' | 'tool'
  content: string
  tool_calls?: ToolCall[]
  timestamp: string
}

interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  result?: unknown
  status: 'pending' | 'running' | 'completed' | 'error'
}
```

#### Características:

- Streaming de resposta (SSE) — mostra texto em tempo real
- Indicadores visuais de tool calls (ex: "🔧 Running simulation...")
- Upload de CSV/GeoJSON (analisar ficheiros existentes)
- Chat persistente por sessão (opcional: guardar histórico)
- Botão "Copy config" ou "Save as report" nos resultados

### 3. Injeção no Dashboard (MODIFICAR)

Adicionar acesso ao Copilot no DashboardPage:

```
[🤖 CARL] no header — ao lado de "Batch Sweep"
→ Abre CopilotPage (/copilot)
→ Ou abre como painel lateral no dashboard
```

### 4. Upload de Ficheiros (NOVO)

```
POST /api/copilot/upload
Content-Type: multipart/form-data
File: .csv ou .geojson

→ Backend guarda no output_dir, retorna file_id
→ AI pode usar read_csv_data(file_id) para analisar
```

---

## Integração com o Sistema Atual

### Sistema de Prompts — o CARL substitui o "AI Insight"

O `ai_config_store.py` já existe com system prompt configurável. O Copilot reutiliza:
- A mesma chave API
- O mesmo model config
- Mas com UM system prompt especializado para tool calling

### Tools → APIs existentes

O executor chama os mesmos endpoints que o frontend usa:
- `POST /api/jobs` — já existe
- `GET /api/jobs/{id}` — já existe
- `GET /api/jobs/{id}/csv/{filename}` — já existe
- `POST /api/jobs/batch` — já existe
- `GET /api/options` — já existe

**Não é preciso criar novas APIs** — só um adaptador que chama estas internamente.

---

## Ficheiros a Criar/Modificar

| # | Ficheiro | Ação | Descrição |
|---|----------|------|-----------|
| 1 | `web/backend/app/ai_copilot/__init__.py` | Criar | Package init |
| 2 | `web/backend/app/ai_copilot/tools.py` | Criar | Tool definitions (JSON schema) |
| 3 | `web/backend/app/ai_copilot/executor.py` | Criar | Executa tool calls contra APIs internas |
| 4 | `web/backend/app/ai_copilot/router.py` | Criar | `POST /api/copilot/chat` com SSE |
| 5 | `web/backend/app/main.py` | Modificar | Registar router do copilot |
| 6 | `web/frontend/src/pages/CopilotPage.tsx` | Criar | Chat interface |
| 7 | `web/frontend/src/components/CopilotChat.tsx` | Criar | Componente de chat reutilizável |
| 8 | `web/backend/app/ai_copilot/config_store.py` | Criar | Guarda/carrega `ai_carl_config.json` |
| 9 | `web/frontend/src/api/client.ts` | Modificar | `copilotChat()`, `copilotUpload()`, getCarlConfig(), updateCarlConfig() |
| 10 | `web/frontend/src/pages/AdminPage.tsx` | Modificar | Separador "🧠 CARL" com edição de persona + tools |
| 9 | `web/frontend/src/App.tsx` | Modificar | Rota `/copilot` |
| 10 | `web/frontend/src/pages/DashboardPage.tsx` | Modificar | Link "🤖 CARL" no header |

---

## Ordem de Implementação

| # | Tarefa | Estimativa |
|---|--------|:----------:|
| 1 | `tools.py` — definir tool schemas para OpenAI/Claude function calling | 20 min |
| 2 | `executor.py` — chamar APIs internas (httpx.AsyncClient local) | 30 min |
| 3 | `router.py` — SSE streaming com suporte a tool calls | 45 min |
| 4 | Registar router no `main.py` | 5 min |
| 5 | `CopilotChat.tsx` — componente de chat com indicadores visuais | 45 min |
| 6 | `CopilotPage.tsx` — página completa com upload | 20 min |
| 7 | `client.ts` — API calls + `App.tsx` + `DashboardPage.tsx` | 15 min |
| 8 | Testes end-to-end | 30 min |
| | **Total** | **~3.5 horas** |

---

## Considerações de Design

### Tool Calling com OpenAI

O backend faz uma chamada inicial ao LLM com `tools=tool_schemas`. O LLM pode responder com:
1. Texto normal (análise, recomendação)
2. `tool_calls` (quer executar uma ferramenta)

Se o LLM pedir tool calls, o backend:
1. Executa a tool (chama API interna)
2. Envia o resultado de volta ao LLM como mensagem `tool`
3. LLM gera resposta final com base no resultado

### Segurança

- O CARL só pode agir como o user que fez login (JWT)
- Tool calls usam o token do user para autorização
- Rate limiting aplicado (igual aos outros endpoints)
- Upload de ficheiros: validar tipo (.csv, .geojson), tamanho (< 10MB)

### Modelos

- **gpt-4o** ou **claude-sonnet-4** recomendados (bom com tool calling)
- Fallback para modelos mais simples sem tool calling (apenas análise textual)
- Configurável via Settings → AI (reutiliza `ai_config_store.py`)

### UX

- Indicador visual quando o AI está a executar um tool call (spinner + descrição)
- Resultados de simulação mostrados inline no chat (mini-tabelas, métricas)
- Opção de "View in Dashboard" para abrir o job completo
- Upload drag-and-drop para CSV/GeoJSON
