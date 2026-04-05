import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { sendAssistantMessage, clearAssistantHistory } from '../services/api'
import { useUserStore } from '../stores/userStore'
import { hapticLight } from '../services/telegram'

type Msg = { role: 'user' | 'ai'; content: string }

export default function AssistantPage() {
  const navigate = useNavigate()
  const { user, decrementCredit } = useUserStore()
  const [messages, setMessages] = useState<Msg[]>([
    { role: 'ai', content: '👋 Привет! Я AI-ассистент. Задай любой вопрос — карьера, резюме, переводы, обучение и всё что угодно.' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    if (!user || user.credits_assistant <= 0) {
      navigate('/payment')
      return
    }
    const msg = input
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: msg }])
    setLoading(true)
    hapticLight()
    try {
      const { data } = await sendAssistantMessage({ message: msg })
      setMessages((m) => [...m, { role: 'ai', content: data.text }])
      decrementCredit('credits_assistant')
    } catch (e: any) {
      setMessages((m) => [...m, { role: 'ai', content: '⚠️ Ошибка. Попробуй ещё раз.' }])
    } finally { setLoading(false) }
  }

  const handleClear = async () => {
    await clearAssistantHistory()
    setMessages([{ role: 'ai', content: '🗑 История очищена. Начнём заново!' }])
  }

  return (
    <div className="page" style={{ paddingBottom: 130 }}>
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>←</button>
        <h2>💬 AI-ассистент</h2>
        <span style={{ fontSize: 13, color: 'var(--tg-theme-hint-color)', marginLeft: 'auto' }}>
          {user?.credits_assistant ?? 0} сообщ.
        </span>
        <button onClick={handleClear} style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', marginLeft: 8 }} title="Очистить историю">🗑</button>
      </div>

      {user && user.credits_assistant <= 0 && (
        <div style={{ background: '#fff3e0', borderRadius: 12, padding: 14, marginBottom: 14 }}>
          <p style={{ fontSize: 13, marginBottom: 8 }}>Сообщения закончились.</p>
          <button className="btn-primary" onClick={() => navigate('/payment')}>💳 Докупить</button>
        </div>
      )}

      <div className="chat-container">
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role === 'user' ? 'user' : 'ai'}`}>{m.content}</div>
        ))}
        {loading && <div className="chat-bubble ai" style={{ opacity: 0.5 }}>✍️ Думаю...</div>}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <input
          className="chat-input"
          placeholder="Задай вопрос..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={loading || (user?.credits_assistant ?? 0) <= 0}
        />
        <button className="chat-send-btn" onClick={handleSend} disabled={loading || !input.trim() || (user?.credits_assistant ?? 0) <= 0}>→</button>
      </div>
    </div>
  )
}
