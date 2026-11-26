import { useEffect, useState, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import { api, ChatMessage, ChatSession } from '../api/client'
import {
  Sparkles,
  Send,
  Loader2,
  X,
  Bot,
  User,
  ChevronRight,
  ChevronDown,
  History,
  MessageSquare,
  Plus,
} from 'lucide-react'

interface ChatCoachProps {
  evaluationId: string
  isOpen: boolean
  onClose: () => void
  initialPrompt?: string
}

const STARTER_PROMPTS = [
  'Why was my transition flagged between slides?',
  'How can I improve my speaking pace?',
  'Suggest a concise rewrite for my introduction.',
  'What should we prioritize before the next rehearsal?',
]

export default function ChatCoach({ evaluationId, isOpen, onClose, initialPrompt }: ChatCoachProps) {
  const { token } = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(undefined)
  const [showSessionsDrawer, setShowSessionsDrawer] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [sending, setSending] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadHistory = async () => {
    if (!token || !evaluationId) return
    setLoadingHistory(true)
    setErrorMsg('')
    try {
      const res = await api.getChatHistory(token, evaluationId)
      const fetchedSessions = res.sessions || []
      setSessions(fetchedSessions)
      if (fetchedSessions.length > 0) {
        if (!activeSessionId) {
          const latest = fetchedSessions[0]
          setActiveSessionId(latest.id)
          setMessages(latest.messages || [])
        } else {
          const matching = fetchedSessions.find((s) => s.id === activeSessionId)
          if (matching) {
            setMessages(matching.messages || [])
          }
        }
      }
    } catch (err) {
      console.error('Failed to load chat history:', err)
    } finally {
      setLoadingHistory(false)
      setTimeout(scrollToBottom, 100)
    }
  }

  useEffect(() => {
    if (token && evaluationId && isOpen) {
      loadHistory()
    }
  }, [token, evaluationId, isOpen])

  useEffect(() => {
    if (initialPrompt && isOpen) {
      setInputMessage(initialPrompt)
    }
  }, [initialPrompt, isOpen])

  useEffect(() => {
    scrollToBottom()
  }, [messages, sending])

  const handleSelectSession = (s: ChatSession) => {
    setActiveSessionId(s.id)
    setMessages(s.messages || [])
    setShowSessionsDrawer(false)
  }

  const handleStartNewSession = () => {
    setActiveSessionId(undefined)
    setMessages([])
    setShowSessionsDrawer(false)
  }

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim()
    if (!text || !token || !evaluationId || sending) return

    setInputMessage('')
    setErrorMsg('')

    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'USER',
      content: text,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    setSending(true)

    try {
      const res = await api.sendChatMessage(token, evaluationId, text, activeSessionId)
      setActiveSessionId(res.session_id)
      setMessages((prev) => [...prev, res.message])
      setSessions((prev) => {
        const exists = prev.some((s) => s.id === res.session_id)
        if (exists) {
          return prev.map((s) =>
            s.id === res.session_id
              ? { ...s, messages: [...(s.messages || []), tempUserMsg, res.message] }
              : s
          )
        }
        const newSession: ChatSession = {
          id: res.session_id,
          evaluation_id: evaluationId,
          user_id: '',
          title: 'Coaching Session',
          created_at: new Date().toISOString(),
          messages: [tempUserMsg, res.message],
        }
        return [newSession, ...prev]
      })
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to get response from AI Coach')
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id))
      setInputMessage(text)
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-lg bg-white h-full shadow-2xl flex flex-col border-l border-slate-200">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-blue-600 text-white">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-white/15">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-sm leading-tight">AI Coach</h3>
              <p className="text-xs text-blue-100">Grounded in this evaluation</p>
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close chat"
            className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="bg-slate-50 border-b border-slate-200 px-4 py-2 flex items-center justify-between text-xs text-slate-700">
          <button
            onClick={() => setShowSessionsDrawer(!showSessionsDrawer)}
            className="flex items-center gap-1.5 font-medium hover:text-blue-600 transition"
          >
            <History className="w-3.5 h-3.5 text-slate-500" />
            <span>Sessions ({sessions.length})</span>
            <ChevronDown
              className={`w-3.5 h-3.5 text-slate-400 transition-transform ${showSessionsDrawer ? 'rotate-180' : ''}`}
            />
          </button>

          <button
            onClick={handleStartNewSession}
            className="inline-flex items-center gap-1 px-2.5 py-1 font-semibold text-blue-700 bg-white hover:bg-blue-50 border border-slate-200 rounded-lg transition"
          >
            <Plus className="w-3.5 h-3.5" />
            New Chat
          </button>
        </div>

        {showSessionsDrawer && (
          <div className="bg-white border-b border-slate-200 max-h-56 overflow-y-auto divide-y divide-slate-100">
            {sessions.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-400">No prior sessions.</div>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => handleSelectSession(s)}
                  className={`p-3 text-xs cursor-pointer flex items-center justify-between gap-2 hover:bg-blue-50 transition ${
                    activeSessionId === s.id
                      ? 'bg-blue-50/70 border-l-4 border-blue-600 font-semibold text-blue-900'
                      : 'text-slate-700'
                  }`}
                >
                  <div className="space-y-0.5 truncate">
                    <div className="flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span className="truncate">{s.title || 'Coaching Session'}</span>
                    </div>
                    <span className="text-[11px] text-slate-400 block">
                      {new Date(s.created_at).toLocaleString()} · {s.messages?.length || 0} messages
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 bg-slate-50/60">
          {loadingHistory ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
              <p className="text-xs">Loading conversation...</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-4 space-y-4">
              <div className="p-3.5 rounded-2xl bg-blue-50 text-blue-600">
                <Sparkles className="w-7 h-7" />
              </div>
              <div className="space-y-1">
                <h4 className="font-semibold text-slate-800 text-sm">Ask about your report</h4>
                <p className="text-xs text-slate-500 max-w-xs">
                  Request clarification on feedback, phrasing suggestions, or practice tips.
                </p>
              </div>

              <div className="w-full space-y-2 pt-2 text-left">
                {STARTER_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(prompt)}
                    className="w-full p-2.5 rounded-xl bg-white border border-slate-200 text-xs text-slate-700 hover:border-blue-400 hover:text-blue-600 transition flex items-center justify-between group"
                  >
                    <span>{prompt}</span>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-500 transition shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((m, idx) => {
                const isUser = m.role === 'USER'
                return (
                  <div
                    key={m.id || idx}
                    className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                  >
                    <div
                      className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                        isUser ? 'bg-slate-800 text-white' : 'bg-blue-600 text-white'
                      }`}
                    >
                      {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                    </div>

                    <div
                      className={`max-w-[82%] rounded-2xl p-3.5 text-xs leading-relaxed whitespace-pre-wrap shadow-sm ${
                        isUser
                          ? 'bg-slate-900 text-white rounded-tr-none'
                          : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
                      }`}
                    >
                      {m.content}
                    </div>
                  </div>
                )
              })}

              {sending && (
                <div className="flex items-start gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0">
                    <Bot className="w-3.5 h-3.5" />
                  </div>
                  <div className="p-3 rounded-2xl rounded-tl-none bg-white border border-slate-200 text-slate-500 text-xs flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" />
                    <span>Thinking...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {errorMsg && (
          <div className="px-4 py-2 bg-rose-50 border-t border-rose-100 text-rose-700 text-xs flex items-center justify-between">
            <span>{errorMsg}</span>
            <button onClick={() => setErrorMsg('')} className="underline">
              Dismiss
            </button>
          </div>
        )}

        <div className="p-4 border-t border-slate-200 bg-white">
          <div className="relative flex items-center">
            <textarea
              rows={2}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending}
              placeholder="Ask a question..."
              className="w-full resize-none rounded-xl border border-slate-300 p-3 pr-12 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-slate-400 disabled:opacity-60"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputMessage.trim() || sending}
              aria-label="Send message"
              className="absolute right-2.5 p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
