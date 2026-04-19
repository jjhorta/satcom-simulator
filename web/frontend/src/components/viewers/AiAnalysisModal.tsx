import { useState, useRef, useEffect } from 'react'
import { X, Sparkles, Copy, Check, AlertTriangle } from 'lucide-react'
import { useAiStore } from '../../store/aiStore'
import { fileUrl, fetchAiAnalysis, saveAiAnalysis } from '../../api/client'
import { useAuthStore } from '../../store/authStore'
import type { JobFile } from '../../types'

// ── Simple markdown renderer (bold, headings, code, lists) ───────────────────
function Markdown({ text }: { text: string }) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []

  lines.forEach((line, i) => {
    if (/^#{1}\s/.test(line)) {
      elements.push(<h2 key={i} className="text-base font-bold text-white mt-4 mb-1">{line.replace(/^#\s/, '')}</h2>)
    } else if (/^#{2}\s/.test(line)) {
      elements.push(<h3 key={i} className="text-sm font-semibold text-indigo-300 mt-3 mb-1">{line.replace(/^##\s/, '')}</h3>)
    } else if (/^#{3}\s/.test(line)) {
      elements.push(<h4 key={i} className="text-xs font-semibold text-gray-300 mt-2 mb-0.5">{line.replace(/^###\s/, '')}</h4>)
    } else if (/^[-*]\s/.test(line)) {
      elements.push(
        <li key={i} className="ml-4 text-sm text-gray-300 list-disc">
          <InlineMarkdown text={line.replace(/^[-*]\s/, '')} />
        </li>
      )
    } else if (/^\d+\.\s/.test(line)) {
      elements.push(
        <li key={i} className="ml-4 text-sm text-gray-300 list-decimal">
          <InlineMarkdown text={line.replace(/^\d+\.\s/, '')} />
        </li>
      )
    } else if (line.startsWith('```')) {
      // skip code fence markers
    } else if (line.trim() === '') {
      elements.push(<div key={i} className="h-2" />)
    } else {
      elements.push(
        <p key={i} className="text-sm text-gray-300 leading-relaxed">
          <InlineMarkdown text={line} />
        </p>
      )
    }
  })

  return <div className="space-y-0.5">{elements}</div>
}

function InlineMarkdown({ text }: { text: string }) {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/)
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i} className="text-white font-semibold">{part.slice(2, -2)}</strong>
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return <code key={i} className="bg-gray-800 text-indigo-300 px-1 rounded text-xs font-mono">{part.slice(1, -1)}</code>
        }
        return <span key={i}>{part}</span>
      })}
    </>
  )
}

// ── Copy button ───────────────────────────────────────────────────────────────
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
      className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

// ── Main modal ────────────────────────────────────────────────────────────────
export default function AiAnalysisModal({
  jobId,
  jobMode,
  files,
  onClose,
}: {
  jobId:    string
  jobMode:  string
  files:    JobFile[]
  onClose:  () => void
}) {
  const ai    = useAiStore()
  const token = useAuthStore((s) => s.token)

  const [status,   setStatus]   = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [response, setResponse] = useState('')
  const [errMsg,   setErrMsg]   = useState('')
  const [cached,   setCached]   = useState(false)
  const bottomRef    = useRef<HTMLDivElement>(null)
  const accumRef     = useRef('')     // accumulates streaming text before saving

  // Load cached result from backend on mount
  useEffect(() => {
    fetchAiAnalysis(jobId).then((saved) => {
      if (saved) {
        setResponse(saved)
        setStatus('done')
        setCached(true)
      }
    })
  }, [jobId])

  // Auto-scroll as streaming text arrives
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [response])

  function clearAndRerun() {
    setCached(false)
    runAnalysis()
  }

  async function runAnalysis() {
    setStatus('loading')
    setResponse('')
    setErrMsg('')
    setCached(false)
    accumRef.current = ''

    // ── 1. Collect log/txt content from output files ─────────────────────────
    const textFiles = files.filter((f) => ['txt', 'log'].includes(f.type))
    const csvFiles  = files.filter((f) => f.type === 'csv')
    const chunks: string[] = [`# Simulation: ${jobMode} | Job ${jobId}\n`]

    for (const f of textFiles) {
      try {
        const url = fileUrl(jobId, f.name)
        const resp = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (resp.ok) {
          const txt = await resp.text()
          chunks.push(`\n## File: ${f.name}\n\`\`\`\n${txt.slice(0, 8000)}\n\`\`\``)
        }
      } catch { /* skip unreadable files */ }
    }

    // ── 1b. Include CSV data (summarised for heatmaps, full for routes) ──────
    for (const f of csvFiles) {
      try {
        const url = fileUrl(jobId, f.name)
        const resp = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (!resp.ok) continue
        const raw  = await resp.text()
        const lines = raw.trim().split('\n')
        const header = lines[0]
        const rows   = lines.slice(1)

        if (f.name.startsWith('route_')) {
          // Route CSV is small — send it fully as a markdown table
          const cols = header.split(',')
          const mdRows = rows.map((r) =>
            '| ' + r.split(',').map((c) => c.trim()).join(' | ') + ' |'
          ).join('\n')
          const mdHeader = '| ' + cols.join(' | ') + ' |'
          const mdSep    = '| ' + cols.map(() => '---').join(' | ') + ' |'
          chunks.push(`\n## Data: ${f.name} (Route waypoints)\n${mdHeader}\n${mdSep}\n${mdRows}`)

        } else if (f.name.startsWith('heatmap_')) {
          // Heatmap CSV can be 2700+ rows — summarise statistically
          const colNames = header.split(',')
          const latIdx   = colNames.indexOf('latitude')
          const pctIdx   = colNames.findIndex((c) => c.includes('availability_pct') || c.includes('pct'))

          if (latIdx < 0 || pctIdx < 0) {
            chunks.push(`\n## Data: ${f.name}\n(Could not parse columns: ${header})`)
            continue
          }

          const data = rows.map((r) => {
            const parts = r.split(',')
            return { lat: parseFloat(parts[latIdx]), pct: parseFloat(parts[pctIdx]) }
          }).filter((d) => !isNaN(d.lat) && !isNaN(d.pct))

          const pcts     = data.map((d) => d.pct)
          const mean     = pcts.reduce((a, b) => a + b, 0) / pcts.length
          const min      = Math.min(...pcts)
          const max      = Math.max(...pcts)
          const below50  = pcts.filter((p) => p < 50).length
          const below10  = pcts.filter((p) => p < 10).length
          const above90  = pcts.filter((p) => p >= 90).length

          // Latitude band summary (30° bands)
          const bands = [
            { label: 'Arctic   (60–90°N)', min: 60,  max: 90  },
            { label: 'N.Temp.  (30–60°N)', min: 30,  max: 60  },
            { label: 'Tropics  (30°S–30°N)', min: -30, max: 30 },
            { label: 'S.Temp.  (30–60°S)', min: -60, max: -30 },
            { label: 'Antarct. (60–90°S)', min: -90, max: -60 },
          ]
          const bandLines = bands.map((b) => {
            const pts = data.filter((d) => d.lat >= b.min && d.lat < b.max)
            if (!pts.length) return `  ${b.label}: no data`
            const avg = pts.reduce((a, d) => a + d.pct, 0) / pts.length
            const mn  = Math.min(...pts.map((d) => d.pct))
            const mx  = Math.max(...pts.map((d) => d.pct))
            return `  ${b.label}: avg=${avg.toFixed(1)}%  min=${mn.toFixed(1)}%  max=${mx.toFixed(1)}%`
          }).join('\n')

          chunks.push(
            `\n## Data: ${f.name} (Heatmap statistics, ${data.length} grid points)\n` +
            `Global: mean=${mean.toFixed(1)}%  min=${min.toFixed(1)}%  max=${max.toFixed(1)}%\n` +
            `Points < 10% coverage: ${below10} (${(below10/data.length*100).toFixed(1)}%)\n` +
            `Points < 50% coverage: ${below50} (${(below50/data.length*100).toFixed(1)}%)\n` +
            `Points ≥ 90% coverage: ${above90} (${(above90/data.length*100).toFixed(1)}%)\n` +
            `\nBy latitude band:\n${bandLines}`
          )
        } else {
          // Generic CSV: send first 50 rows
          const preview = [header, ...rows.slice(0, 50)].join('\n')
          chunks.push(`\n## Data: ${f.name}\n\`\`\`csv\n${preview}\n\`\`\``)
        }
      } catch { /* skip */ }
    }

    if (chunks.length === 1) {
      setErrMsg('No output files found for this simulation.')
      setStatus('error')
      return
    }

    const userContent = chunks.join('\n')

    // ── 2. Call LLM (OpenAI-compatible) ─────────────────────────────────────
    try {
      const endpoint = ai.baseUrl.replace(/\/$/, '') + '/chat/completions'
      const body = {
        model: ai.model,
        stream: true,
        messages: [
          { role: 'system',  content: ai.systemPrompt },
          { role: 'user',    content: userContent },
        ],
      }

      const llmResp = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': `Bearer ${ai.token}`,
        },
        body: JSON.stringify(body),
      })

      if (!llmResp.ok) {
        const errBody = await llmResp.text().catch(() => '')
        throw new Error(`LLM API error ${llmResp.status}: ${errBody.slice(0, 300)}`)
      }

      // ── 3. Stream response ─────────────────────────────────────────────────
      const reader  = llmResp.body?.getReader()
      const decoder = new TextDecoder()
      let   buffer  = ''

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') break
          try {
            const chunk = JSON.parse(data)
            const delta = chunk.choices?.[0]?.delta?.content ?? ''
            if (delta) {
              accumRef.current += delta
              setResponse((r) => r + delta)
            }
          } catch { /* malformed chunk */ }
        }
      }

      setStatus('done')
      // Persist the completed analysis on the backend (cross-device)
      saveAiAnalysis(jobId, accumRef.current).catch(() => { /* non-critical */ })
    } catch (e) {
      setErrMsg((e as Error).message ?? 'Unknown error calling LLM.')
      setStatus('error')
    }
  }

  const isLoading = status === 'loading'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <div>
              <h2 className="text-base font-semibold text-white">AI Assist</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {ai.model} · {ai.baseUrl.replace(/https?:\/\//, '').split('/')[0]}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Context note */}
          <div className="text-xs text-gray-500 bg-gray-800/40 border border-gray-700/40 rounded-lg p-3 space-y-1">
            <p>The following files will be sent to the LLM:</p>
            {['txt', 'log'].some((t) => files.some((f) => f.type === t)) && (
              <p><span className="text-gray-400 font-medium">Logs/text: </span>
                <span className="text-gray-300">
                  {files.filter((f) => ['txt','log'].includes(f.type)).map((f) => f.name).join(', ')}
                </span>
              </p>
            )}
            {files.some((f) => f.type === 'csv') && (
              <p><span className="text-gray-400 font-medium">CSV data: </span>
                <span className="text-gray-300">
                  {files.filter((f) => f.type === 'csv').map((f) =>
                    f.name.startsWith('heatmap_') ? `${f.name} (summarised)` :
                    f.name.startsWith('route_')   ? `${f.name} (full table)` : f.name
                  ).join(', ')}
                </span>
              </p>
            )}
            {!files.some((f) => ['txt','log','csv'].includes(f.type)) && (
              <span className="text-yellow-400">No suitable files found.</span>
            )}
          </div>

          {/* Start button */}
          {status === 'idle' && (
            <button
              onClick={runAnalysis}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl
                         bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors"
            >
              <Sparkles className="w-4 h-4" />
              Analyse simulation
            </button>
          )}

          {/* Loading */}
          {isLoading && !response && (
            <div className="flex items-center gap-2 text-sm text-gray-500 animate-pulse">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              Sending to {ai.model}…
            </div>
          )}

          {/* Streaming / done response */}
          {response && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">
                  {isLoading
                    ? <span className="animate-pulse">Receiving response…</span>
                    : 'Analysis complete'}
                </span>
                <div className="flex items-center gap-3">
                  {cached && (
                    <span className="text-xs text-emerald-500/70 border border-emerald-700/40 rounded px-1.5 py-0.5">
                      saved
                    </span>
                  )}
                  {status === 'done' && <CopyButton text={response} />}
                </div>
              </div>
              <div className="bg-gray-950 border border-gray-800 rounded-xl p-5 overflow-auto max-h-[50vh]">
                <Markdown text={response} />
                <div ref={bottomRef} />
              </div>
            </div>
          )}

          {/* Error */}
          {status === 'error' && (
            <div className="flex gap-3 bg-red-900/20 border border-red-700/40 rounded-lg p-4">
              <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-400">Request failed</p>
                <p className="text-xs text-red-300 mt-1 font-mono break-all">{errMsg}</p>
                <button
                  onClick={runAnalysis}
                  className="mt-3 text-xs text-indigo-400 hover:text-indigo-300 underline"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Re-run after success */}
          {status === 'done' && (
            <button
              onClick={clearAndRerun}
              className="text-xs text-gray-500 hover:text-gray-300 underline transition-colors"
            >
              Re-run analysis
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
