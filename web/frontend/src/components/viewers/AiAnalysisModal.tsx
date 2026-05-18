import { useState, useRef, useEffect } from 'react'
import { X, Sparkles, Copy, Check, AlertTriangle } from 'lucide-react'
import { useAiStore } from '../../store/aiStore'
import { fetchAiAnalysis, aiStreamUrl } from '../../api/client'
import { useAuthStore } from '../../store/authStore'

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
  onClose,
}: {
  jobId:    string
  onClose:  () => void
}) {
  const ai    = useAiStore()
  const token = useAuthStore((s) => s.token)

  const [status,   setStatus]   = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [response, setResponse] = useState('')
  const [errMsg,   setErrMsg]   = useState('')
  const [cached,   setCached]   = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const accumRef  = useRef('')

  // Load cached result from backend on mount
  useEffect(() => {
    fetchAiAnalysis(jobId).then((saved) => {
      if (saved) { setResponse(saved); setStatus('done'); setCached(true) }
    })
  }, [jobId])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [response])

  function clearAndRerun() { setCached(false); runAnalysis() }

  async function runAnalysis() {
    setStatus('loading')
    setResponse('')
    setErrMsg('')
    setCached(false)
    accumRef.current = ''

    try {
      // Call the server-side proxy — key never leaves the server
      const url = aiStreamUrl(jobId)
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })

      if (!resp.ok) {
        const errBody = await resp.text().catch(() => '')
        let detail = errBody
        try { detail = JSON.parse(errBody).detail ?? errBody } catch { /* ignore */ }
        throw new Error(detail.slice(0, 300))
      }

      // Stream SSE from backend proxy
      const reader  = resp.body?.getReader()
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
            if (chunk.error) throw new Error(chunk.error)
            const delta = chunk.delta ?? ''
            if (delta) {
              accumRef.current += delta
              setResponse((r) => r + delta)
            }
          } catch (parseErr) {
            if ((parseErr as Error).message !== 'Unexpected token') throw parseErr
          }
        }
      }

      setStatus('done')
      // Backend already persisted ai_analysis.txt during streaming
    } catch (e) {
      setErrMsg((e as Error).message ?? 'Unknown error.')
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
          <div className="text-xs text-gray-500 bg-gray-800/40 border border-gray-700/40 rounded-lg p-3">
            Context is collected server-side: logs, dashboards, and CSV data are read from the job output directory
            and sent directly to the LLM. Your API key never passes through the browser.
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
