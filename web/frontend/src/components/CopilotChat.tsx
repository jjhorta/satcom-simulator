import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Bot, User, Loader2, AlertCircle, CheckCircle, Plus, Trash2, MessageSquare, ChevronLeft, ChevronRight, Satellite, HelpCircle } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { listCarlChats, getCarlChat, deleteCarlChat } from '../api/client'
import ResourcesModal from './ResourcesModal'
import HelpModal from './HelpModal'

const API_BASE = `${import.meta.env.BASE_URL?.replace(/\/$/, '')}/api`

interface CarlMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatSummary {
  id: string
  name: string
  preview: string
  message_count: number
  created_at: string
  updated_at: string
}

interface ToolCallStatus {
  id: string
  name: string
  status: 'pending' | 'running' | 'done' | 'error'
}

const TOOL_LABELS: Record<string, string> = {
  submit_simulation: '🔬 Running simulation...',
  get_job_status: '📊 Checking results...',
  read_csv_data: '📈 Analyzing data...',
  submit_batch_sweep: '⚡ Running batch sweep...',
  get_simulation_options: '📋 Listing options...',
  upload_file: '📎 Processing file...',
}

export default function CopilotChat() {
  const token = useAuthStore((s) => s.token)
  const [chats, setChats] = useState<ChatSummary[]>([])
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<CarlMessage[]>([
    { role: 'assistant', content: "Hello! I'm CARL, your constellation AI engineer. How can I help you design or analyze a satellite constellation today?" }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [toolCalls, setToolCalls] = useState<ToolCallStatus[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [showResources, setShowResources] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [chatLoading, setChatLoading] = useState(false)
  const chatEnd = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, toolCalls])

  // Load chats on mount
  useEffect(() => {
    listCarlChats().then(setChats).catch(() => {})
  }, [])

  const loadChat = useCallback(async (chatId: string) => {
    setChatLoading(true)
    setActiveChatId(chatId)
    try {
      const chat = await getCarlChat(chatId)
      setMessages(chat.messages?.length > 0 ? chat.messages : [
        { role: 'assistant', content: "Hello! I'm CARL, your constellation AI engineer. How can I help you?" }
      ])
    } catch {
      setMessages([{ role: 'assistant', content: 'Failed to load chat.' }])
    }
    setChatLoading(false)
  }, [])

  const newChat = async () => {
    setActiveChatId(null)
    setMessages([{ role: 'assistant', content: "Hello! I'm CARL, your constellation AI engineer. How can I help you today?" }])
  }

  const handleDelete = async (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation()
    if (!confirm('Delete this chat?')) return
    await deleteCarlChat(chatId)
    setChats(prev => prev.filter(c => c.id !== chatId))
    if (activeChatId === chatId) newChat()
  }

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)
    setToolCalls([])

    const abort = new AbortController()
    abortRef.current = abort

    try {
      const resp = await fetch(`${API_BASE}/carl/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          chat_id: activeChatId,
          messages: [{ role: 'user', content: userMsg }],
        }),
        signal: abort.signal,
      })

      if (!resp.ok) {
        const err = await resp.json()
        setMessages(prev => [...prev, { role: 'assistant', content: `❌ ${err.detail || 'Failed to connect'}` }])
        setLoading(false)
        return
      }

      const reader = resp.body?.getReader()
      if (!reader) return

      let assistantContent = ''
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        for (const line of text.split('\n').filter(Boolean)) {
          try {
            const event = JSON.parse(line)
            switch (event.type) {
              case 'delta':
                assistantContent += event.content
                setMessages(prev => {
                  const next = [...prev]
                  if (next[next.length - 1]?.role === 'assistant') {
                    next[next.length - 1] = { ...next[next.length - 1], content: assistantContent }
                  } else {
                    next.push({ role: 'assistant', content: assistantContent })
                  }
                  return next
                })
                break
              case 'tool_calls_start':
                setToolCalls(event.tool_calls?.map((tc: ToolCallStatus) => ({ ...tc, status: 'running' })) || [])
                break
              case 'tool_result':
                setToolCalls(prev => prev.map(tc =>
                  tc.id === event.tool_call_id ? { ...tc, status: event.status === 'error' ? 'error' : 'done' } : tc
                ))
                break
              case 'done':
                if (event.chat_id && !activeChatId) {
                  setActiveChatId(event.chat_id)
                  // Refresh chat list
                  listCarlChats().then(setChats).catch(() => {})
                } else {
                  // Refresh chat list to update preview
                  listCarlChats().then(setChats).catch(() => {})
                }
                break
              case 'error':
                setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ ${event.content}` }])
                break
            }
          } catch { /* skip */ }
        }
      }
    } catch (e: unknown) {
      if ((e as Error)?.name !== 'AbortError') {
        setMessages(prev => [...prev, { role: 'assistant', content: '❌ Connection error' }])
      }
    } finally {
      setLoading(false)
      setToolCalls([])
    }
  }

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-72' : 'w-0'} transition-all duration-200 bg-gray-900 border-r border-gray-800 flex flex-col overflow-hidden flex-shrink-0`}>
        {sidebarOpen && (
          <>
            <div className="p-3 border-b border-gray-800 space-y-2">
              <button onClick={newChat}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm
                           border border-dashed border-gray-600 text-gray-400 hover:text-white
                           hover:border-gray-400 transition-colors">
                <Plus className="w-4 h-4" /> New Chat
              </button>
              <button onClick={() => setShowResources(true)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm
                           bg-gray-800 text-gray-300 hover:text-white hover:bg-gray-700
                           transition-colors mt-2">
                <Satellite className="w-4 h-4" /> Resources
              </button>
              <button onClick={() => setShowHelp(true)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm
                           bg-gray-800 text-gray-300 hover:text-white hover:bg-gray-700
                           transition-colors mt-2">
                <HelpCircle className="w-4 h-4" /> Help
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {chats.map(chat => (
                <div key={chat.id}
                  onClick={() => loadChat(chat.id)}
                  className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                    activeChatId === chat.id
                      ? 'bg-indigo-900/40 text-white border border-indigo-800/50'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  }`}>
                  <MessageSquare className="w-4 h-4 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-xs font-medium">{chat.name}</div>
                    {chat.preview && <div className="truncate text-xs text-gray-500">{chat.preview}</div>}
                  </div>
                  <button onClick={(e) => handleDelete(e, chat.id)}
                    className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              {chats.length === 0 && (
                <p className="text-xs text-gray-600 text-center pt-4">No chats yet. Start a new one!</p>
              )}
            </div>
          </>
        )}
      </div>

      {/* Toggle sidebar */}
      <button onClick={() => setSidebarOpen(o => !o)}
        className="absolute left-0 top-20 z-10 bg-gray-900 border border-gray-800 rounded-r-md p-1.5
                   text-gray-500 hover:text-white transition-colors"
        style={{ left: sidebarOpen ? '18rem' : '0' }}>
        {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      {/* Resources modal */}
      {showHelp && (
        <HelpModal onClose={() => setShowHelp(false)} />
      )}
      {showHelp && (
        <HelpModal onClose={() => setShowHelp(false)} />
      )}
      {showResources && (
        <ResourcesModal messages={messages} token={token} onClose={() => setShowResources(false)} />
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {chatLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
          </div>
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 p-4">
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                  )}
                  <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-md'
                      : 'bg-gray-800 text-gray-200 rounded-bl-md'
                  }`}>
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  )}
                </div>
              ))}

              {/* Tool call indicators */}
              {toolCalls.length > 0 && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-gray-800/80 rounded-2xl rounded-bl-md px-4 py-3 space-y-2">
                    {toolCalls.map(tc => (
                      <div key={tc.id} className="flex items-center gap-2 text-xs">
                        {tc.status === 'running' && <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />}
                        {tc.status === 'done' && <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />}
                        {tc.status === 'error' && <AlertCircle className="w-3.5 h-3.5 text-red-400" />}
                        <span className="text-gray-400">{TOOL_LABELS[tc.name] || tc.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {loading && toolCalls.length === 0 && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-gray-800 rounded-2xl rounded-bl-md px-4 py-3">
                    <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                  </div>
                </div>
              )}
              <div ref={chatEnd} />
            </div>

            {/* Input */}
            <div className="border-t border-gray-800 p-4">
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), sendMessage())}
                  placeholder="Ask CARL to design a constellation, analyze coverage, compare configurations..."
                  disabled={loading}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-white
                             focus:outline-none focus:border-indigo-500 placeholder-gray-600 disabled:opacity-50"
                />
                <button onClick={sendMessage} disabled={loading || !input.trim()}
                  className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500
                             text-white rounded-xl px-4 py-3 transition-colors">
                  <Send className="w-4 h-4" />
                </button>
              </div>
              <p className="text-xs text-gray-600 mt-2 ml-1">
                CARL can run real simulations — try "Design a VDES constellation for Panama Canal coverage"
              </p>
            </div>
          </>
        )}
      </div>

    </div>
  )
}
