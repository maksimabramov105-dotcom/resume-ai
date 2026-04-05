import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { startInterview, answerInterview, finishInterview } from '../services/api'
import { useUserStore } from '../stores/userStore'
import { hapticLight, hapticMedium } from '../services/telegram'

type Msg = { role: 'user' | 'ai'; content: string }

export default function InterviewPage() {
  const navigate = useNavigate()
  const { user, decrementCredit } = useUserStore()
  const [stage, setStage] = useState<'setup' | 'chat' | 'done'>('setup')
  const [vacancy, setVacancy] = useState('')
  const [messages, setMessages] = useState<Msg[]>([])
  const [history, setHistory] = useState<{ role: string; content: string }[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [questionCount, setQuestionCount] = useState(0)
  const [result, setResult] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const handleStart = async () => {
    if (!vacancy.trim()) return
    setLoading(true)
    try {
      hapticMedium()
      const { data } = await startInterview({ vacancy_text: vacancy })
      setMessages([{ role: 'ai', content: data.text }])
      setHistory([{ role: 'assistant', content: data.text }])
      setQuestionCount(1)
      decrementCredit('credits_interview')
      setStage('chat')
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка')
    } finally { setLoading(false) }
  }

  const handleAnswer = async () => {
    if (!input.trim() || loading) return
    const answer = input
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: answer }])
    const newHistory = [...history, { role: 'user', content: answer }]
    setLoading(true)
    hapticLight()
    try {
      const { data } = await answerInterview({ answer, vacancy_text: vacancy, conversation_history: newHistory })
      setMessages((m) => [...m, { role: 'ai', content: data.text }])
      const updated = [...newHistory, { role: 'assistant', content: data.text }]
      setHistory(updated)
      setQuestionCount((c) => c + 1)
    } finally { setLoading(false) }
  }

  const handleFinish = async () => {
    setLoading(true)
    hapticMedium()
    try {
      const { data } = await finishInterview({ answer: '', vacancy_text: vacancy, conversation_history: history })
      setResult(data.text)
      setStage('done')
    } finally { setLoading(false) }
  }

  if (!user || user.credits_interview <= 0) {
    return (
      <div className="page">
        <div className="page-header">
          <button className="back-btn" onClick={() => navigate('/')}>←</button>
          <h2>🎯 Собеседование</h2>
        </div>
        <p style={{ color: 'var(--tg-theme-hint-color)', marginBottom: 16 }}>Собеседование — платная функция. Нужны кредиты.</p>
        <button className="btn-primary" onClick={() => navigate('/payment')}>💳 Купить кредиты</button>
      </div>
    )
  }

  if (stage === 'setup') return (
    <div className="page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>←</button>
        <h2>🎯 Симуляция собеседования</h2>
      </div>
      <p style={{ fontSize: 13, color: 'var(--tg-theme-hint-color)', marginBottom: 14 }}>AI сыграет роль HR-менеджера. После 7+ вопросов получишь оценку и советы.</p>
      <div className="form-group">
        <label className="form-label">Текст вакансии</label>
        <textarea className="text-input" rows={6} placeholder="Вставь описание вакансии..." value={vacancy} onChange={(e) => setVacancy(e.target.value)} />
      </div>
      <button className="btn-primary" onClick={handleStart} disabled={loading || !vacancy.trim()}>
        {loading ? '⏳ Начинаю...' : '🎯 Начать собеседование'}
      </button>
    </div>
  )

  if (stage === 'done') return (
    <div className="page">
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>←</button>
        <h2>📊 Итоги собеседования</h2>
      </div>
      <div className="result-box">{result}</div>
      <button className="btn-primary" style={{ marginBottom: 10 }} onClick={() => { setStage('setup'); setMessages([]); setHistory([]); setVacancy(''); setQuestionCount(0) }}>🔄 Ещё раз</button>
      <button className="btn-secondary" onClick={() => navigate('/resume')}>📄 Создать резюме</button>
    </div>
  )

  return (
    <div className="page" style={{ paddingBottom: 130 }}>
      <div className="page-header">
        <button className="back-btn" onClick={() => navigate('/')}>←</button>
        <h2>🎯 Собеседование</h2>
        {questionCount >= 5 && (
          <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: 12 }} onClick={handleFinish} disabled={loading}>
            ⏭ Завершить
          </button>
        )}
      </div>
      <div className="chat-container">
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role === 'user' ? 'user' : 'ai'}`}>{m.content}</div>
        ))}
        {loading && <div className="chat-bubble ai" style={{ opacity: 0.5 }}>✍️ Печатает...</div>}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input-row">
        <input className="chat-input" placeholder="Твой ответ..." value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleAnswer()} disabled={loading} />
        <button className="chat-send-btn" onClick={handleAnswer} disabled={loading || !input.trim()}>→</button>
      </div>
    </div>
  )
}
